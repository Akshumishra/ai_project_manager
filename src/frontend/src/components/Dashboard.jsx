import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import CreateProjectModal from './CreateProjectModal';

export default function Dashboard({ onSelectProject }) {
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const { user } = useAuth();

  const fetchProjects = async () => {
    try {
      const res = await api.get('/api/projects/');
      setProjects(res.data);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleCreateProject = () => {
    navigate('/create-project');
  };

  const handleDeleteProject = async (e, projectId, projectName) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete project "${projectName}"?`)) return;

    try {
      await api.delete(`/api/projects/${projectId}`);
      setProjects(projects.filter(p => p.id !== projectId));
    } catch (err) {
      console.error('Failed to delete project:', err);
      alert('Failed to delete project. Please try again.');
    }
  };

  if (loading) return <div className="dashboard-loading">Loading your projects...</div>;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div>
          <h1>My Projects</h1>
          <p className="welcome-text">Logged in as: <strong>{user?.name || user?.email || 'User'}</strong></p>
        </div>
        <button className="btn btn-primary" onClick={handleCreateProject}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Project
        </button>
      </header>

      <div className="doc-grid">
        {projects.map(project => (
          <div key={project.id} className="doc-card" onClick={() => onSelectProject(project.id)}>
            <div className="doc-card-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
            </div>
            <div className="doc-card-info">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <h3 style={{ margin: 0 }}>{project.name}</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className={`task-status status-${(project.status || 'active').toLowerCase()}`} style={{ fontSize: '10px', padding: '2px 8px' }}>
                    {(project.status || 'active').replace('_', ' ')}
                  </span>
                  {user?.id === project.created_by && (
                    <button 
                      className="btn-delete-project"
                      onClick={(e) => handleDeleteProject(e, project.id, project.name)}
                      title="Delete Project"
                      style={{ padding: '4px' }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
              <p style={{ margin: 0 }}>{project.description || 'No description'}</p>
            </div>
          </div>
        ))}

        {projects.length === 0 && (
          <div className="no-docs">
            <p>No projects yet. Create your first project to get started!</p>
          </div>
        )}
      </div>

      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={fetchProjects}
      />
    </div>
  );
}
