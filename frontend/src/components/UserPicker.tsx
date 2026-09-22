import type { DemoUser } from '../types'

type UserPickerProps = {
  users: DemoUser[]
  selectedId: string
  onSelect: (id: string) => void
}

export function UserPicker({ users, selectedId, onSelect }: UserPickerProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h1 className="brand">Mem0 Arch</h1>
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
    </aside>
  )
}
