import json
import os
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    Document,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    VectorParams,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "memories")
USER_IDS_PATH = Path(__file__).resolve().parents[2] / "data" / "user_ids.json"


def load_user_ids() -> dict[str, str]:
    with USER_IDS_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def create_client() -> QdrantClient:
    return QdrantClient(
        url=os.getenv("QDRANT_ENDPOINT"),
        api_key=os.getenv("QDRANT_API_KEY"),
        cloud_inference=True,
    )


def ensure_collection(client: QdrantClient) -> None:
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    client.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name="user_id",
        field_schema=PayloadSchemaType.KEYWORD,
    )


client = create_client()
ensure_collection(client)


def query_user_memories(
    client: QdrantClient,
    user_id: str,
    user_message: str,
    limit: int,
):
    qdrant_user_id = load_user_ids().get(user_id, user_id)
    return client.query_points(
        collection_name=COLLECTION_NAME,
        query=Document(text=user_message, model=MODEL_NAME),
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=qdrant_user_id),
                )
            ]
        ),
        with_payload=True,
        limit=limit,
    )
