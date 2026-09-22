import type { Message } from '../types'

type ChatWindowProps = {
  userLabel: string
  messages: Message[]
}

export function ChatWindow({ userLabel, messages }: ChatWindowProps) {
  return (
    <div className="chat-window">
      <header className="chat-header">
        <h2>Chat as {userLabel}</h2>
      </header>
      <div className="message-list">
        {messages.length === 0 ? (
          <p className="empty-hint">
            Ask about preferences, work, or learning — answers use that user&apos;s
            Qdrant memories. Each send also fires the async write path.
          </p>
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
