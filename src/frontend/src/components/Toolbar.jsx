import { useAuth } from '../context/AuthContext';

export default function Toolbar({
  status,
  onLogout,
  onBack,
  documentData,
  syncStatus,
}) {
  const isConnected = status.trim().toLowerCase().includes('connected')

  const { user } = useAuth();

  return (
    <header className="toolbar">
      <div className="toolbar-brand">
        {onBack && (
          <button className="btn btn-ghost" onClick={onBack} title="Back">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
        )}
        <span className="brand-name">
          {documentData ? (documentData.title || 'Untitled Document') : 'AI Project Manager'}
        </span>
      </div>

      <div className="toolbar-controls">
      </div>

      <div className="toolbar-status">
        <span className="user-name" style={{ marginRight: '16px' }}>{user?.name}</span>
        <button className="btn btn-secondary" onClick={onLogout}>Logout</button>
      </div>
    </header>
  )
}
