import { useMemo, useState } from 'react'
import { sendChat } from './api/client'
import { ChatWindow } from './components/ChatWindow'
import { MessageInput } from './components/MessageInput'
import { UserPicker } from './components/UserPicker'
import type { DemoUser, Message } from './types'
import './App.css'

const USERS: DemoUser[] = [
  { id: 'alex', label: 'Alex' },
  { id: 'maya', label: 'Maya' },
  { id: 'jordan', label: 'Jordan' },
]

function App() {
  const [userId, setUserId] = useState('alex')
  const [messages, setMessages] = useState<Message[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const userLabel = useMemo(
    () => USERS.find((u) => u.id === userId)?.label ?? userId,
    [userId],
  )

  function handleSelectUser(id: string) {
    setUserId(id)
    setMessages([])
    setError(null)
  }

  async function handleSend(userMessage: string) {
    setSending(true)
    setError(null)
    try {
      const reply = await sendChat({
        user_id: userId,
        user_message: userMessage,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          user_message: userMessage,
          assistant_message: reply.response,
        },
      ])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="app">
      <UserPicker
        users={USERS}
        selectedId={userId}
        onSelect={handleSelectUser}
      />
      <main className="main">
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        <ChatWindow userLabel={userLabel} messages={messages} />
        <MessageInput disabled={false} sending={sending} onSend={handleSend} />
      </main>
    </div>
  )
}

export default App
