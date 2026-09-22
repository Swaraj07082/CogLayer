import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PayloadSchemaType, PointStruct, VectorParams


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "memories")


def load_memories() -> dict[str, list[dict]]:
    store_path = Path(__file__).resolve().parent.parent / "data" / "memory_store.json"
    with store_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    memory_store = data.get("memory_store")
    if not isinstance(memory_store, dict):
        raise ValueError("memory_store.json must contain a user-keyed memory_store object")
    return memory_store


def load_user_ids() -> dict[str, str]:
    ids_path = Path(__file__).resolve().parent.parent / "data" / "user_ids.json"
    if not ids_path.exists():
        return {}

    with ids_path.open("r", encoding="utf-8") as file:
        user_ids = json.load(file)
    if not isinstance(user_ids, dict):
        raise ValueError("user_ids.json must contain a user-keyed object")
    return user_ids


def save_user_ids(user_ids: dict[str, str]) -> None:
    ids_path = Path(__file__).resolve().parent.parent / "data" / "user_ids.json"
    with ids_path.open("w", encoding="utf-8") as file:
        json.dump(user_ids, file, indent=2)
        file.write("\n")


def get_client() -> QdrantClient:
    endpoint = os.getenv("QDRANT_ENDPOINT")
    api_key = os.getenv("QDRANT_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError("QDRANT_ENDPOINT and QDRANT_API_KEY must be set")

    return QdrantClient(url=endpoint, api_key=api_key, cloud_inference=True)


def recreate_collection(client: QdrantClient) -> None:
    """Drop and recreate so old uuid5 point IDs cannot linger beside memory_store IDs."""
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )
    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )


def build_points(
    memory_store: dict[str, list[dict]], user_ids: dict[str, str]
) -> tuple[list[PointStruct], dict[str, str]]:
    for user_key in memory_store:
        user_ids.setdefault(user_key, str(uuid.uuid4()))
    points = []

    for user_key, memories in memory_store.items():
        qdrant_user_id = user_ids[user_key]
        for memory in memories:
            memory_id = memory.get("id")
            text = memory.get("text")
            embedding_vector = memory.get("embedding_vector")
            if not isinstance(memory_id, str) or not memory_id.strip():
                raise ValueError(f"User {user_key} has a memory without an id")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"User {user_key} has a memory without text")
            if not isinstance(embedding_vector, list) or len(embedding_vector) != 384:
                raise ValueError(
                    f"Memory {memory_id} must have a 384-dimensional embedding_vector"
                )

            points.append(
                PointStruct(
                    id=memory_id,
                    vector=embedding_vector,
                    payload={
                        "id": memory_id,
                        "user_id": qdrant_user_id,
                        "source_user_key": user_key,
                        "text": text,
                        "metadata": memory.get("metadata", {}),
                        "created_at": memory.get("created_at"),
                        "updated_at": memory.get("updated_at"),
                    },
                )
            )

    return points, user_ids


def main() -> None:
    memory_store = load_memories()
    user_ids = load_user_ids()
    client = get_client()
    recreate_collection(client)
    points, user_ids = build_points(memory_store, user_ids)
    save_user_ids(user_ids)

    if not points:
        print("No memories found; nothing was uploaded.")
        return

    client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    print(f"Recreated '{COLLECTION_NAME}' and uploaded {len(points)} memories for {len(user_ids)} users.")
    for user_key, user_id in user_ids.items():
        print(f"{user_key}: {user_id}")


if __name__ == "__main__":
    main()
