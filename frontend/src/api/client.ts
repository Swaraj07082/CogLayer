import type {
  ChatRequest,
  Conversation,
  ConversationSummary,
  CreateConversationRequest,
  Message,
} from '../types'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (!response.ok) {
    const detail = await response.text().catch(() => '')
    throw new Error(
      detail || `Request failed: ${response.status} ${response.statusText}`,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function listConversations(
  userId: string,
): Promise<ConversationSummary[]> {
  return request(`/conversations?user_id=${encodeURIComponent(userId)}`)
}

export function createConversation(
  body: CreateConversationRequest,
): Promise<Conversation> {
  return request('/conversations', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getConversation(id: string): Promise<Conversation> {
  return request(`/conversations/${encodeURIComponent(id)}`)
}

export function sendChat(body: ChatRequest): Promise<Message> {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
