import type { DemoUser } from '../types'

type UserPickerProps = {
  users: DemoUser[]
  selectedId: string
  onSelect: (id: string) => void
}

function goLearn() {
  window.history.pushState({}, '', '/learn')
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function UserPicker({ users, selectedId, onSelect }: UserPickerProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="brand">CogLayer</h1>
      </div>
      <p className="sidebar-hint">Demo users (UUID-scoped memories)</p>
      <ul className="conversation-list">
        {users.map((user) => (
          <li key={user.id}>
            <button
              type="button"
              className={
                user.id === selectedId
                  ? 'conversation-item active'
                  : 'conversation-item'
              }
              onClick={() => onSelect(user.id)}
            >
              {user.label}
            </button>
          </li>
        ))}
      </ul>
      <div className="sidebar-footer">
        <button type="button" className="learn-entry" onClick={goLearn}>
          Learn architecture →
        </button>
      </div>
    </aside>
  )
}
