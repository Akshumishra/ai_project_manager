import { useCallback, useEffect, useState } from 'react';
import api from '../../../shared/api/api';
import { useAuth } from '../../auth/context/AuthContext';
import InviteModal from './InviteModal';

export default function ProjectDetail({ projectId, onSelectDocument, onBack }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const { user } = useAuth();

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get(`/api/projects/${projectId}/documents`);
      setDocuments(res.data);
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) fetchDocuments();
  }, [projectId, fetchDocuments]);

  const handleCreateDocument = async () => {
    const title = prompt('Document Title:', 'Untitled Document');
    if (!title) return;
    try {
      const res = await api.post('/api/documents/', { title, project_id: projectId });
      if (res.data.document_id) {
        onSelectDocument(res.data.document_id);
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

  if (loading) return <div className="dashboard-loading">Loading documents...</div>;

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button className="btn btn-ghost" onClick={onBack}>
             <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
          <div>
            <h1>Documents</h1>
            <p className="welcome-text">Team: <strong>{user?.name || user?.email}</strong></p>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={handleAddMember}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/>
            </svg>
            Add Member
          </button>
          <button className="btn btn-primary" onClick={handleCreateDocument}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            New Document
          </button>
        </div>
      </header>


      <div className="doc-grid">
        {documents.map(doc => (
          <div key={doc.id} className="doc-card" onClick={() => onSelectDocument(doc.id)}>
            <div className="doc-card-icon">
               <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
            </div>
            <div className="doc-card-info">
              <h3>{doc.title}</h3>
              <p>Created: {new Date(doc.created_at).toLocaleDateString()}</p>
            </div>
            <div className="doc-card-actions">
              <button 
                className="btn-action-doc btn-rename-doc" 
                onClick={(e) => handleRenameDocument(e, doc.id, doc.title)}
                title="Rename Document"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121(0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
              </button>
              <button 
                className="btn-action-doc btn-delete-doc" 
                onClick={(e) => handleDeleteDocument(e, doc.id)}
                title="Delete Document"
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
      <InviteModal 
        projectId={projectId} 
        isOpen={isInviteModalOpen} 
        onClose={() => setIsInviteModalOpen(false)} 
      />
    </div>
  );
}
