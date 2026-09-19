# Chat Frontend

Simple Vite + React chat UI. Conversations are loaded/stored via your backend; message IDs are UUIDs.

## Run

```bash
cd frontend
cp .env.example .env   # optional; defaults to http://localhost:8000
npm install
npm run dev
```

App runs at `http://localhost:5173`. Demo `user_id` is hardcoded as `"1"` in `src/App.tsx`.

## Backend API contract

Base URL: `VITE_API_BASE_URL` (default `http://localhost:8000`). Enable CORS for the Vite origin.

### `GET /conversations?user_id=`

List conversations for a user.

**Response**
```json
[
  {
    "id": "<uuid>",
    "user_id": "1",
    "conversation_name": "Conversation 1"
  }
]
```

### `POST /conversations`

Create a conversation.

**Request**
```json
{
  "user_id": "1",
  "conversation_name": "Conversation 1"
}
```

**Response**
```json
{
  "id": "<uuid>",
  "user_id": "1",
  "conversation_name": "Conversation 1",
  "conversation_messages": []
}
```

### `GET /conversations/:id`

Get one conversation with messages.

**Response**
```json
{
  "id": "<uuid>",
  "user_id": "1",
  "conversation_name": "Conversation 1",
  "conversation_messages": [
    {
      "id": "<uuid>",
      "user_message": "Hello",
      "assistant_message": "Hi there"
    }
  ]
}
```

### `POST /chat`

Send a user message. Backend runs the LLM, stores the pair, returns the stored message (UUID `id`).

**Request**
```json
{
  "conversation_id": "<uuid>",
  "user_id": "1",
  "user_message": "Hello"
}
```

**Response**
```json
{
  "id": "<uuid>",
  "user_message": "Hello",
  "assistant_message": "Hi there"
}
```

## Storage shape

Matches the project `conversations.json` shape, with UUID string IDs for conversations and messages:

```json
{
  "conversations": [
    {
      "id": "<uuid>",
      "user_id": "1",
      "conversation_name": "Conversation 1",
      "conversation_messages": [
        {
          "id": "<uuid>",
          "user_message": "...",
          "assistant_message": "..."
        }
      ]
    }
  ]
}
```
