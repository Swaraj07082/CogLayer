from dotenv import load_dotenv
import os

load_dotenv()

def get_top_k_messages(conversation_messages, k=int(os.getenv("TOP_K", "3"))):
    return conversation_messages[-k:]