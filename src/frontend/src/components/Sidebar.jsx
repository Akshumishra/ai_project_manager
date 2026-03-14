import { useEffect, useState } from 'react';
import api from '../api';

export default function Sidebar({ onSelectProject, activeProjectId }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await api.get('/api/projects/');
        setProjects(res.data);
      } catch (err) {
        console.error('Failed to fetch projects for sidebar:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchProjects();
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2>Projects</h2>
      </div>
      <nav className="sidebar-nav">
        {loading ? (
          <div className="sidebar-loading">Loading...</div>
        ) : (
          projects.map(p => (
            <button 
              key={p.id} 
              className={`sidebar-item ${p.id === activeProjectId ? 'active' : ''}`}
              onClick={() => onSelectProject(p.id)}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
              </svg>
              {p.name}
            </button>
          ))
        )}
      </nav>
    </aside>
  );
}
