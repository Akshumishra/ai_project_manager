import { useCallback, useEffect, useState } from 'react';
import api, { getProjectTasksRequest, createProjectTaskRequest } from '../api';
import { useAuth } from '../context/AuthContext';
import InviteModal from './InviteModal';
import ProjectMembersModal from './ProjectMembersModal';
import AddTaskModal from './AddTaskModal';

export default function ProjectDetail({ projectId, onSelectDocument, onBack }) {
  const [documents, setDocuments] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('documents');
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [isMembersModalOpen, setIsMembersModalOpen] = useState(false);
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const { user } = useAuth();

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${projectId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    }
  }, [projectId]);

  const fetchTasks = useCallback(async () => {
    try {
      const data = await getProjectTasksRequest(projectId);
      setTasks(data);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
    }
  }, [projectId]);

  const fetchMembers = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${projectId}/members`);
      setMembers(res.data);
    } catch (err) {
      console.error('Failed to fetch members:', err);
    }
  }, [projectId]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      if (projectId) {
        // Double check workflow status for robustness
        try {
          const statusRes = await api.get(`/api/projects/${projectId}/status`);
          const reqStatus = workflows.find(w => w.workflow_name === 'requirement_gathering')?.status;
          const techStatus = workflows.find(w => w.workflow_name === 'tech_doc_gathering')?.status;

          if (reqStatus !== 'completed' || techStatus !== 'completed') {
             // Let App.jsx handle it or force here
             // navigate if needed, but App.jsx is better. 
          }
        } catch (e) {
          console.warn("Status check failed in detail page", e);
        }
        await Promise.all([fetchDocuments(), fetchTasks(), fetchMembers()]);
      }
      setLoading(false);
    };
    load();
  }, [projectId, fetchDocuments, fetchTasks]);

  const handleCreateDocument = async () => {
    const title = prompt('Document Title:', 'Untitled Document');
    if (!title) return;
    try {
      const res = await api.post('/api/documents/', { title, project_id: projectId });
      if (res.data.document_id) {
        onSelectDocument(res.data.document_id);
      } else {
        await fetchDocuments();
      }
    } catch (err) {
      console.error('Create document failed:', err);
    }
  };

  const handleAddMember = () => {
    setIsInviteModalOpen(true);
  };

  const handleDeleteDocument = async (e, docId) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this document?')) return;
    try {
      await api.delete(`/api/documents/${docId}`);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch (err) {
      console.error('Failed to delete document:', err);
      alert('Failed to delete document');
    }
  };

  const handleRenameDocument = async (e, docId, currentTitle) => {
    e.stopPropagation();
    const newTitle = prompt('New Document Title:', currentTitle);
    if (!newTitle || newTitle === currentTitle) return;
    
    try {
      await api.patch(`/api/documents/${docId}`, { title: newTitle });
      setDocuments(prev => prev.map(d => d.id === docId ? { ...d, title: newTitle } : d));
    } catch (err) {
      console.error('Failed to rename document:', err);
      alert('Failed to rename document');
    }
  };

  const handleCreateTask = () => {
    setIsTaskModalOpen(true);
  };

  const onTaskCreated = (newTask) => {
    setTasks(prev => [newTask, ...prev]);
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="project-detail-container" style={{ padding: '40px', background: 'var(--gray-50)', minHeight: '100vh', display: 'flex', justifyContent: 'center' }}>
      <div className="document-container" style={{ width: '100%', maxWidth: '1000px', background: 'white', padding: '40px', borderRadius: '24px', boxShadow: 'var(--shadow-md)' }}>
        <header className="dashboard-header" style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button className="btn btn-ghost" onClick={onBack} title="Back to Dashboard">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>
            <div>
              <h1>Project Dashboard</h1>
              <p className="welcome-text">Manage your workspace for <strong>{user?.name || user?.email}</strong></p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button className="btn btn-secondary" onClick={handleAddMember}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
              </svg>
              Add Member
            </button>
            <button className="btn btn-outline" onClick={() => setIsMembersModalOpen(true)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              View All Members
            </button>
          </div>
        </header>

        <div className="document-inner-scroller" style={{ padding: '0 40px 40px 40px' }}>
          <div className="tabs" style={{ position: 'sticky', top: 0, background: 'white', zIndex: 10, paddingBottom: '16px', paddingTop: '8px' }}>
            <button
              className={`tab ${activeTab === 'documents' ? 'active' : ''}`}
              onClick={() => setActiveTab('documents')}
            >
              Documents
            </button>
            <button
              className={`tab ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => setActiveTab('tasks')}
            >
              Tasks
            </button>
          </div>

          {activeTab === 'documents' && (
            <>
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px' }}>
                <button className="btn btn-primary" onClick={handleCreateDocument}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  New Document
                </button>
              </div>

              <div className="doc-grid">
                {documents.map(doc => (
                  <div key={doc.id} className="doc-card" onClick={() => onSelectDocument(doc.id)}>
                    <div className="doc-card-icon">
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <polyline points="14 2 14 8 20 8"/>
                      </svg>
                    </div>
                    <div className="doc-card-info" style={{ flex: 1 }}>
                      <h3>{doc.title}</h3>
                      <p>Created: {new Date(doc.created_at).toLocaleDateString()}</p>
                    </div>
                    <div className="doc-card-actions" onClick={(e) => e.stopPropagation()}>
                      <button 
                        className="btn-action-doc btn-rename-doc" 
                        onClick={(e) => handleRenameDocument(e, doc.id, doc.title)}
                        title="Rename Document"
                        style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                        </svg>
                      </button>
                      <button 
                        className="btn-action-doc btn-delete-doc" 
                        onClick={(e) => handleDeleteDocument(e, doc.id)}
                        title="Delete Document"
                        style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ff4d4d" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="3 6 5 6 21 6"></polyline>
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                          <line x1="10" y1="11" x2="10" y2="17"></line>
                          <line x1="14" y1="11" x2="14" y2="17"></line>
                        </svg>
                      </button>
                    </div>
                  </div>
                ))}

                {documents.length === 0 && (
                  <div className="no-docs">
                    <p>No documents in this project yet. Click "New Document" to create one!</p>
                  </div>
                )}
              </div>
            </>
          )}

          {activeTab === 'tasks' && (
            <div className="tasks-panel">
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px', gap: '12px' }}>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => alert('Task Assigner AI Agent is coming soon!')}
                  style={{ display: 'flex', alignItems: 'center' }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                  Assign Task (AI)
                </button>
                <button className="btn btn-primary" onClick={handleCreateTask}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
                    <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
                  </svg>
                  Add Task
                </button>
              </div>
              {tasks.length === 0 ? (
                <div className="no-docs">
                  <p>No tasks for this project yet. Use "Add Task" to create one.</p>
                </div>
              ) : (
                <div className="task-list">
                  {tasks.map(task => (
                    <div key={task.id} className="task-card">
                      <div className="task-header">
                        <h3>{task.name}</h3>
                        <span className={`task-status status-${task.status.toLowerCase()}`}>
                          {task.status.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="task-description">{task.description}</p>
                      <div className="task-meta">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                          {task.deadline && (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                              {new Date(task.deadline).toLocaleDateString()}
                            </span>
                          )}
                          {task.complexity && (
                            <span className={`badge-complexity ${task.complexity.toLowerCase()}`} style={{
                              padding: '2px 8px',
                              borderRadius: '12px',
                              fontSize: '10px',
                              fontWeight: '700',
                              textTransform: 'uppercase',
                              backgroundColor: task.complexity.toLowerCase() === 'critical' ? '#fee2e2' : 
                                             task.complexity.toLowerCase() === 'high' ? '#ffedd5' :
                                             task.complexity.toLowerCase() === 'medium' ? '#f0f9ff' : '#f0fdf4',
                              color: task.complexity.toLowerCase() === 'critical' ? '#991b1b' : 
                                     task.complexity.toLowerCase() === 'high' ? '#9a3412' :
                                     task.complexity.toLowerCase() === 'medium' ? '#075985' : '#166534',
                            }}>
                              {task.complexity}
                            </span>
                          )}
                        </div>
                        {task.assignee_name && (
                          <div className="task-assignee" style={{ 
                            marginTop: '12px',
                            paddingTop: '12px',
                            borderTop: '1px solid var(--gray-100)',
                            display: 'flex', 
                            alignItems: 'center',
                            fontSize: '12px',
                            color: 'var(--gray-600)'
                          }}>
                            <div style={{ 
                              width: '24px', 
                              height: '24px', 
                              borderRadius: '50%', 
                              background: 'var(--brand-600)', 
                              color: 'white',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              marginRight: '8px',
                              fontSize: '10px',
                              fontWeight: 'bold'
                            }}>
                              {task.assignee_name.charAt(0).toUpperCase()}
                            </div>
                            <span style={{ fontWeight: '500' }}>{task.assignee_name}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <InviteModal 
          projectId={projectId} 
          isOpen={isInviteModalOpen} 
          onClose={() => setIsInviteModalOpen(false)} 
        />

        <ProjectMembersModal
          projectId={projectId}
          isOpen={isMembersModalOpen}
          onClose={() => setIsMembersModalOpen(false)}
        />

        <AddTaskModal
          isOpen={isTaskModalOpen}
          onClose={() => setIsTaskModalOpen(false)}
          projectId={projectId}
          onSuccess={onTaskCreated}
          members={members}
        />
      </div>
    </div>
  );
}
