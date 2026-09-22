from fastapi import FastAPI
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils.conversations import get_user_conversation
from utils.llm_call import llm_call
from utils.qdrant_memory import client, query_user_memories
from utils.workers import process_message_pair


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: str
    user_message: str


@app.post("/chat")
def chat(request : ChatRequest):

    memories = query_user_memories(
        client=client,
        user_id=request.user_id,
        user_message=request.user_message,
        limit=int(os.getenv("TOP_K", "10")),
    )

    conversations = get_user_conversation(request.user_id)

    response = llm_call(memories , conversations , request.user_message)

    # WRITE PATH (async): extract → similar search → decide → apply
    try:
        process_message_pair.delay(
            request.user_id,
            request.user_message,
            response.response,
        )
    except Exception as exc:
        # Do not fail the read-path reply if the broker/worker is unavailable.
        print(f"Failed to enqueue process_message_pair: {exc}")

    return response
