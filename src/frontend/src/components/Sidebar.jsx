const Sidebar = ({
  projects = [],
  activeProjectId,
  onSelectProject,
  onNewProject,
  loading = false,
}) => {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>My Projects</h2>
      </div>
      <div className="sidebar-nav">
        {loading ? (
          <div className="v-stack gap-2" style={{ padding: '12px' }}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                style={{
                  height: '32px',
                  background: '#f1f5f9',
                  borderRadius: '8px',
                  opacity: 0.5,
                }}
              ></div>
            ))}
          </div>
        ) : (
          Array.isArray(projects) &&
          projects.map((project) => (
            <button
              key={project.id}
              className={`sidebar-item ${activeProjectId === project.id ? 'active' : ''}`}
              onClick={() => onSelectProject && onSelectProject(project.id)}
            >
              <span style={{ marginRight: '10px' }}>📁</span>
              {project.name}
            </button>
          ))
        )}
        <button
          className="sidebar-item"
          onClick={onNewProject}
          style={{ marginTop: '12px', color: 'var(--brand-600)' }}
        >
          <span style={{ marginRight: '10px' }}>+</span>
          New Project
        </button>
      </div>
    </aside>
  )
}

const ProjectDetail = ({ project, documents, onSelectDocument, onNewDocument, onStartRequirement, onStartTechDoc, loading }) => {
  if (loading) {
    return (
      <div className="dashboard-container">
        <div className="dashboard-loading">
          <div className="spinner"></div>
        </div>
      </div>
    )
  }

  if (!project) return null

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="v-stack gap-1">
          <h1>{project.name}</h1>
          <p className="welcome-text">Manage your project documents and AI agents</p>
        </div>
        <div className="h-stack gap-2">
          <button className="btn btn-secondary" onClick={onStartRequirement}>
             Requirement Agent
          </button>
          <button className="btn btn-secondary" onClick={onStartTechDoc}>
             Tech Doc Agent
          </button>
          <button className="btn btn-primary" onClick={onNewDocument}>
             New Document
          </button>
        </div>
      </header>

      <div className="doc-grid">
        {documents.length === 0 ? (
          <div className="no-docs">
            <p>No documents yet. Get started by creating one or starting an agent.</p>
          </div>
        ) : (
          documents.map(doc => (
            <div key={doc.id} className="doc-card" onClick={() => onSelectDocument(doc.id)}>
              <div className="h-stack gap-4">
                <div className="doc-card-icon">📄</div>
                <div className="doc-card-info">
                  <h3>{doc.title || 'Untitled Document'}</h3>
                  <p>Last edited {new Date().toLocaleDateString()}</p>
                </div>
              </div>
              <div className="doc-card-actions">
                <button className="btn btn-ghost">Open</button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Sidebar; // Assuming Sidebar is the default export for this file. If ProjectDetail is also needed, it would be a named export.
