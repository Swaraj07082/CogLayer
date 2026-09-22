import type { ChatRequest, ChatResponse } from '../types'

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

  return response.json() as Promise<T>
}

export function sendChat(body: ChatRequest): Promise<ChatResponse> {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}
