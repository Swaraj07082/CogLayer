import json
from pathlib import Path


CONVERSATIONS_PATH = Path(__file__).resolve().parents[2] / "conversations_store.json"
USER_IDS_PATH = Path(__file__).resolve().parents[2] / "data" / "user_ids.json"


def get_user_conversation(user_id: str) -> list[dict]:
    with USER_IDS_PATH.open("r", encoding="utf-8") as file:
        user_ids = json.load(file)
    resolved_user_id = user_ids.get(user_id, user_id)

    with CONVERSATIONS_PATH.open("r", encoding="utf-8") as file:
        conversations = json.load(file)

    for conversation in conversations.get("conversations", []):
        if conversation.get("user_id") == resolved_user_id:
            return conversation.get("conversation_messages", [])

    return []


if __name__ == "__main__":
    # Example usage
    user_id = "1668d210-c809-4cce-8f10-d73f68361852"
    conversation = get_user_conversation(user_id)
    print(f"Conversation for {user_id}: {conversation}")