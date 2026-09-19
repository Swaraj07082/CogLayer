import type { ConversationSummary } from '../types'

type ConversationListProps = {
  conversations: ConversationSummary[]
  selectedId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  creating: boolean
}

export function ConversationList({
  conversations,
  selectedId,
  onSelect,
  onNew,
  creating,
}: ConversationListProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="brand">Chat</h1>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onNew}
          disabled={creating}
        >
          {creating ? 'Creating…' : 'New chat'}
        </button>
      </div>
      <ul className="conversation-list">
        {conversations.length === 0 ? (
          <li className="empty-hint">No conversations yet</li>
        ) : (
          conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`conversation-item${selectedId === c.id ? ' active' : ''}`}
                onClick={() => onSelect(c.id)}
              >
                {c.conversation_name}
              </button>
            </li>
          ))
        )}
      </ul>
    </aside>
  )
}
