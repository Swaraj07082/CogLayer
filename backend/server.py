from fastapi import FastAPI
import json
from pathlib import Path
from pydantic import BaseModel
from utils.summary import generate_summary
from utils.top_k_messages import get_top_k_messages
from utils.llm_call import llm_call
from utils.memory_update import update_memories

app = FastAPI()

class ChatRequest(BaseModel):
    user_id: int
    user_message: str

@app.post("/chat")
def chat(request : ChatRequest):
    conversations_path = Path(__file__).resolve().parent.parent / "conversations.json"
    with open(conversations_path, "r") as f:
        conversations = json.load(f)
    
    conversation_messages = []

    for conversation in conversations["conversations"]:
        if conversation["user_id"] == request.user_id:
            conversation_messages = conversation["conversation_messages"]
            break

    if conversation_messages:
        summary = generate_summary(conversation_messages)
        top_k_messages = get_top_k_messages(conversation_messages)

        response = llm_call(summary , top_k_messages , request.user_message)

        
        update_memories(request.user_id, response.memories)
        return {"response": response}
    else:
        response = llm_call(user_message=request.user_message)
        update_memories(request.user_id, response.memories)
        return {"response": response}

    

    