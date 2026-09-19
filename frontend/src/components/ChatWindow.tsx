import type { Message } from '../types'

type ChatWindowProps = {
  conversationName: string | null
  messages: Message[]
  loading: boolean
}

export function ChatWindow({
  conversationName,
  messages,
  loading,
}: ChatWindowProps) {
  if (!conversationName) {
    return (
      <div className="chat-window empty">
        <p>Select a conversation or start a new one.</p>
      </div>
    )
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h2>{conversationName}</h2>
      </header>
      <div className="message-list">
        {loading ? (
          <p className="empty-hint">Loading messages…</p>
        ) : messages.length === 0 ? (
          <p className="empty-hint">Send a message to start chatting.</p>
        ) : (
          messages.map((m) => (
            <div key={m.id} className="message-pair">
              <div className="bubble user">
                <span className="role">You</span>
                <p>{m.user_message}</p>
              </div>
              <div className="bubble assistant">
                <span className="role">Assistant</span>
                <p>{m.assistant_message}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
