from backend.utils.qdrant_memory import COLLECTION_NAME, client, query_user_memories
from celery import Celery
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from backend.utils.summary import generate_summary
from backend.utils.top_k_messages import get_top_k_messages
from typing import Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import os
from langchain_groq import ChatGroq
from fastembed import TextEmbedding
from qdrant_client.models import PointIdsList, PointStruct

class Memories(BaseModel):
    memories : list[dict]


class MemoryToolCall(BaseModel):
    """One memory operation chosen by the DECIDE LLM step."""

    name: Literal["ADD", "UPDATE", "DELETE", "NOOP"]
    candidate_fact: str = Field(description="The extracted candidate fact being decided on")
    memory_id: Optional[str] = Field(
        default=None,
        description="Existing memory id from similar matches; required for UPDATE and DELETE",
    )
    text: Optional[str] = Field(
        default=None,
        description="New or refined memory text; used for ADD and UPDATE",
    )
    reason: str = Field(description="Short explanation for why this operation was chosen")


class ToolPickResponse(BaseModel):
    tool_calls: list[MemoryToolCall]
    notes: Optional[str] = Field(
        default=None,
        description="Optional extra context about the overall decision batch",
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
MEMORY_STORE_PATH = REPO_ROOT / "data" / "memory_store.json"
USER_IDS_PATH = REPO_ROOT / "data" / "user_ids.json"
CONVERSATIONS_PATH = REPO_ROOT / "conversations_store.json"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_embedder: Optional[TextEmbedding] = None

app_celery = Celery("tasks", broker="pyamqp://guest@localhost//")
app_celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(model_name=EMBED_MODEL_NAME)
    return _embedder


def embed_text(text: str) -> list[float]:
    vector = next(_get_embedder().embed([text]))
    return [float(x) for x in vector]


def load_memory_store() -> dict:
    with MEMORY_STORE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_memory_store(data: dict) -> None:
    with MEMORY_STORE_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)
        file.write("\n")


def load_user_ids() -> dict[str, str]:
    with USER_IDS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_user_key(user_id: str) -> str:
    """Map a Qdrant UUID back to the memory_store friendly key (e.g. alex)."""
    user_ids = load_user_ids()
    for key, value in user_ids.items():
        if value == user_id or key == user_id:
            return key
    raise ValueError(f"Unknown user_id: {user_id}")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_qdrant_user_id(user_key: str) -> str:
    """Friendly key (alex) → UUID stored in Qdrant payload user_id."""
    user_ids = load_user_ids()
    qdrant_user_id = user_ids.get(user_key)
    if not qdrant_user_id:
        raise ValueError(f"No Qdrant user_id mapping for key: {user_key}")
    return qdrant_user_id


def upsert_qdrant_memory(entry: dict, user_key: str, qdrant_user_id: str) -> None:
    """Upsert one memory point so the read path sees ADD/UPDATE immediately."""
    memory_id = entry["id"]
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=memory_id,
                vector=entry["embedding_vector"],
                payload={
                    "id": memory_id,
                    "user_id": qdrant_user_id,
                    "source_user_key": user_key,
                    "text": entry["text"],
                    "metadata": entry.get("metadata", {}),
                    "created_at": entry.get("created_at"),
                    "updated_at": entry.get("updated_at"),
                },
            )
        ],
        wait=True,
    )


def delete_qdrant_memory(memory_id: str) -> None:
    """Remove a memory point so the read path reflects DELETE immediately."""
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=PointIdsList(points=[memory_id]),
        wait=True,
    )


def apply_tool_calls(user_id: str, tool_calls: list[dict]) -> dict:
    """
    Apply DECIDE operations to memory_store.json and sync ADD/UPDATE/DELETE to Qdrant.
    Returns a summary of what changed.
    """
    user_key = resolve_user_key(user_id)
    qdrant_user_id = resolve_qdrant_user_id(user_key)
    data = load_memory_store()
    memories = data.setdefault("memory_store", {}).setdefault(user_key, [])

    by_id = {memory.get("id"): memory for memory in memories if memory.get("id")}
    applied = []

    for call in tool_calls:
        op = call.get("name")
        memory_id = call.get("memory_id")
        text = call.get("text")
        reason = call.get("reason")

        if op == "NOOP":
            applied.append({"op": op, "memory_id": memory_id, "reason": reason})
            continue

        if op == "ADD":
            if not text or not str(text).strip():
                applied.append({"op": op, "status": "skipped", "reason": "missing text"})
                continue
            new_id = str(uuid4())
            now = utc_now()
            entry = {
                "text": text.strip(),
                "embedding_vector": embed_text(text.strip()),
                "created_at": now,
                "updated_at": now,
                "metadata": {
                    "tags": [],
                    "source": "tool_pick",
                    "user_id": user_key,
                },
                "id": new_id,
            }
            memories.append(entry)
            by_id[new_id] = entry
            upsert_qdrant_memory(entry, user_key, qdrant_user_id)
            applied.append({"op": op, "memory_id": new_id, "text": entry["text"], "reason": reason})
            continue

        if op == "UPDATE":
            if not memory_id or memory_id not in by_id:
                applied.append({"op": op, "status": "skipped", "reason": f"unknown memory_id {memory_id}"})
                continue
            if not text or not str(text).strip():
                applied.append({"op": op, "status": "skipped", "reason": "missing text"})
                continue
            entry = by_id[memory_id]
            entry["text"] = text.strip()
            entry["embedding_vector"] = embed_text(text.strip())
            entry["updated_at"] = utc_now()
            upsert_qdrant_memory(entry, user_key, qdrant_user_id)
            applied.append({"op": op, "memory_id": memory_id, "text": entry["text"], "reason": reason})
            continue

        if op == "DELETE":
            if not memory_id or memory_id not in by_id:
                applied.append({"op": op, "status": "skipped", "reason": f"unknown memory_id {memory_id}"})
                continue
            memories[:] = [m for m in memories if m.get("id") != memory_id]
            by_id.pop(memory_id, None)
            delete_qdrant_memory(memory_id)
            applied.append({"op": op, "memory_id": memory_id, "reason": reason})
            continue

        applied.append({"op": op, "status": "skipped", "reason": f"unknown operation {op}"})

    save_memory_store(data)
    return {
        "user_key": user_key,
        "applied": applied,
        "memory_count": len(memories),
    }


def handle_message_pair(user_id, user_message, response):
    if CONVERSATIONS_PATH.exists():
        with CONVERSATIONS_PATH.open("r", encoding="utf-8") as file:
            conversations = json.load(file)
    else:
        conversations = {"conversations": []}

    conversations.setdefault("conversations", [])
    pair = {
        "id": str(uuid4()),
        "user_message": user_message,
        "assistant_message": response,
    }

    for con in conversations["conversations"]:
        if con.get("user_id") == user_id:
            con.setdefault("conversation_messages", []).append(pair)
            break
    else:
        conversations["conversations"].append(
            {"user_id": user_id, "conversation_messages": [pair]}
        )

    with CONVERSATIONS_PATH.open("w", encoding="utf-8") as file:
        json.dump(conversations, file, indent=2)


def extract_memories(user_id, user_message, response):
    """LLM call #1 — EXTRACT candidate facts from the new message pair + history."""
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL"),
    )
    with CONVERSATIONS_PATH.open("r", encoding="utf-8") as file:
        conversations = json.load(file)

    user_conversation = []
    for con in conversations.get("conversations", []):
        if con.get("user_id") == user_id:
            user_conversation = con.get("conversation_messages") or []
            break

    summary = generate_summary(user_conversation)
    top_k_messages = get_top_k_messages(user_conversation, k=10)
    parser = PydanticOutputParser(pydantic_object=Memories)

    prompt = PromptTemplate(
        template="""
Extract durable memory facts from the following conversation context.
Use the summary, recent messages, and the new message pair.

summary: {summary}
recent_messages: {top_k_messages}
user_message: {user_message}
assistant_response: {response}

Return memories as a list of objects that include a "text" field with a clear factual sentence.

{format_instructions}
""",
        input_variables=["summary", "top_k_messages", "user_message", "response"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    result = chain.invoke(
        {
            "summary": summary,
            "top_k_messages": top_k_messages,
            "user_message": user_message,
            "response": response,
        }
    )
    return result.memories


def get_similar_memories(user_id, extracted_memories, limit: int = 5):
    """For each candidate fact: similarity search → top-s matches."""
    similar_memories = []

    for memory in extracted_memories:
        query_memory = memory.get("text") if isinstance(memory, dict) else None
        if not query_memory:
            query_memory = str(memory)

        response = query_user_memories(
            client=client,
            user_id=user_id,
            user_message=query_memory,
            limit=limit,
        )

        similar_memories.append(
            {
                "candidate_fact": query_memory,
                "similar_matches": [
                    {
                        "id": point.payload.get("id") or str(point.id),
                        "text": point.payload.get("text"),
                    }
                    for point in response.points
                ],
            }
        )

    return similar_memories


def tool_pick(user_id, user_message, response):
    """
    LLM call #2 (DECIDE): for each candidate fact + its top similar matches,
    pick exactly one operation: ADD | UPDATE | DELETE | NOOP.
    Does not mutate the store — the Celery task applies tool_calls.
    """
    extracted_memories = extract_memories(user_id, user_message, response)
    similar_memories = get_similar_memories(user_id, extracted_memories)

    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL"),
    )
    parser = PydanticOutputParser(pydantic_object=ToolPickResponse)

    prompt = PromptTemplate(
        template="""
You are the memory DECIDE step. For each candidate fact and its top similar
existing memories, pick exactly ONE tool operation.

Operations:
- ADD: candidate is a new fact not covered by similar memories → set text to the new fact; memory_id must be null
- UPDATE: candidate merges with / refines an existing memory → set memory_id to that memory's id and text to the refined fact
- DELETE: candidate contradicts an existing memory → set memory_id to the contradicted memory; text may be null
- NOOP: candidate is already known / fully covered → memory_id may reference the matching memory; text may be null

Rules:
- Emit one tool_call per candidate fact.
- For UPDATE and DELETE, memory_id MUST be one of the ids in that candidate's similar matches.
- Prefer NOOP over ADD when an existing memory already covers the same fact (even with slightly different wording).
- Keep reason short and specific.

Candidate facts with similar matches (JSON):
{similar_memories}

{format_instructions}
""",
        input_variables=["similar_memories"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | llm | parser
    result = chain.invoke({"similar_memories": json.dumps(similar_memories, indent=2)})

    return {
        "extracted_memories": extracted_memories,
        "tool_calls": [call.model_dump() for call in result.tool_calls],
        "notes": result.notes,
        "similar_memories": similar_memories,
    }


@app_celery.task(name="workers.process_message_pair")
def process_message_pair(user_id: str, user_message: str, response: str) -> dict:
    """
    WRITE PATH (async):
    new message pair → save conversation → EXTRACT → similar search →
    DECIDE (ADD/UPDATE/DELETE/NOOP) → apply ops to memory_store.json
    """
    handle_message_pair(user_id, user_message, response)
    decide_result = tool_pick(user_id, user_message, response)
    store_update = apply_tool_calls(user_id, decide_result["tool_calls"])
    return {
        "user_id": user_id,
        "user_message": user_message,
        **decide_result,
        "store_update": store_update,
    }


if __name__ == "__main__":
    result = process_message_pair(
        "1668d210-c809-4cce-8f10-d73f68361852",
        "What does alex like?",
        "Alex prefers dark roast coffee and is studying computer science.",
    )
    print(
        json.dumps(
            {
                "tool_calls": result["tool_calls"],
                "notes": result["notes"],
                "store_update": result["store_update"],
            },
            indent=2,
        )
    )