from backend.utils.qdrant_memory import client, query_user_memories
from celery import Celery
import json
from uuid import uuid4
from backend.utils.summary import generate_summary
from backend.utils.top_k_messages import get_top_k_messages
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
import os
from langchain_groq import ChatGroq

class Memories(BaseModel):
    memories : list[dict]


app_celery = Celery('tasks', broker='pyamqp://guest@localhost//')

def handle_message_pair(user_id , user_message , response ):
    with open("conversations_store.json", "r", encoding="utf-8") as file:
        conversations = json.load(file)

        for con in conversations.get("conversations" , []):
            if con.get("user_id") == user_id:
                con.get("conversation_messages").append({"id": str(uuid4()),
                    "user_message": user_message,
                    "assistant_message": response})
                break

        if conversations.get("conversations") is None:
            conversations["conversations"].append({"user_id": user_id, "conversation_messages": [{"id": str(uuid4()),
                "user_message": user_message,
                "assistant_message": response}]})

    with open("conversations_store.json", "w", encoding="utf-8") as file:
        json.dump(conversations, file, indent=2)


def extract_memories(user_id , user_message , response):

    llm = ChatGroq(
        api_key = os.getenv("GROQ_API_KEY"),
        model = os.getenv("GROQ_MODEL"),
    )   
    with open("conversations_store.json", "r", encoding="utf-8") as file:
        conversations = json.load(file)

        user_conversation = []

        for con in conversations.get("conversations" , []):
            if con.get("user_id") == user_id:
                user_conversation = con.get("conversation_messages")
                break

        summary = generate_summary(user_conversation)

        top_k_messages = get_top_k_messages(user_conversation, k=10)

        parser = PydanticOutputParser(pydantic_object=Memories)

        prompt = PromptTemplate(
            template="""
Extract memories from the following conversation -{top_k_messages} , summary - {summary} and user message - {user_message} and response - {response}.

{format_instructions}
""",
            input_variables=["summary", "top_k_messages", "user_message" , "response"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )


        chain = prompt | llm | parser
        result = chain.invoke({"summary": summary, "top_k_messages": top_k_messages, "user_message": user_message , "response": response})

        return result.memories


def get_similar_memories(user_id , user_message):
     
    response = query_user_memories(
            client=client,
            user_id=user_id,
            user_message=user_message,
            limit=int(os.getenv("TOP_K", "10")),
    )

    memories = []

    for point in response.points:
        memories.append(point.payload) 

    return memories



if __name__ == "__main__":

    memories = get_similar_memories("1668d210-c809-4cce-8f10-d73f68361852" , "What does alex like?")

    print(f"Memories for user 1668d210-c809-4cce-8f10-d73f68361852: {memories}")