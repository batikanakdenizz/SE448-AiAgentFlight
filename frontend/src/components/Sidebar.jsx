import './Sidebar.css'

const actions = [
  { id: 'query', icon: '🔍', label: 'Query Flight' },
  { id: 'book',  icon: '✈️', label: 'Book Flight' },
  { id: 'checkin', icon: '✅', label: 'Check In' }
]

export default function Sidebar({ onQuickAction, onNewChat }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">✈</div>
        <div>
          <h1 className="sidebar-title">AI Flight Agent</h1>
          <p className="sidebar-subtitle">Flight Actions</p>
        </div>
      </div>

      <nav className="sidebar-nav">
        <p className="sidebar-nav-label">Quick Actions</p>
        {actions.map(action => (
          <button
            key={action.id}
            className="sidebar-action-btn"
            onClick={() => onQuickAction(action.id)}
          >
            <span className="action-icon">{action.icon}</span>
            {action.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button className="new-chat-btn" onClick={onNewChat}>
          + New Chat
        </button>
      </div>
    </aside>
  )
}
