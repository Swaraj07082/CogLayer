from fastapi import FastAPI
import os
from pydantic import BaseModel
from utils.conversations import get_user_conversation
from utils.llm_call import llm_call
from utils.qdrant_memory import client, query_user_memories
from utils.workers import process_message_pair


app = FastAPI()

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
    process_message_pair.delay(
        request.user_id,
        request.user_message,
        response.response,
    )

    return response
