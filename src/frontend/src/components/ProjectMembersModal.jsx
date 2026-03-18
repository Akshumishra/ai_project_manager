import React, { useState, useEffect } from 'react';
import api from '../api';

export default function ProjectMembersModal({ projectId, isOpen, onClose }) {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && projectId) {
      fetchMembers();
    }
  }, [isOpen, projectId]);

  const fetchMembers = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/api/projects/${projectId}/members`);
      setMembers(res.data);
    } catch (err) {
      console.error('Failed to fetch members:', err);
      setError('Failed to load members. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
        <header className="modal-header">
          <div>
            <h3>Project Members</h3>
            <p className="modal-description" style={{ margin: '4px 0 0 0' }}>View all contributors to this workspace</p>
          </div>
          <button onClick={onClose} className="btn-close">&times;</button>
        </header>

        <div className="modal-body">
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
              <div className="spinner"></div>
            </div>
          ) : error ? (
            <div className="error-banner">{error}</div>
          ) : (
            <div className="member-list" style={{ maxHeight: '400px', overflowY: 'auto' }}>
              {members.length === 0 ? (
                <p className="no-docs" style={{ padding: '20px' }}>No members found.</p>
              ) : (
                members.map(member => (
                  <div key={member.id} className="member-item" style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '16px',
                    borderRadius: '16px',
                    background: 'var(--gray-50)',
                    marginBottom: '12px',
                    transition: 'all 0.2s'
                  }}>
                    <div className="member-avatar" style={{
                      width: '40px',
                      height: '40px',
                      borderRadius: '12px',
                      background: 'var(--brand-100)',
                      color: 'var(--brand-700)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: '700',
                      marginRight: '16px'
                    }}>
                      {member.name.charAt(0).toUpperCase()}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '600', fontSize: '15px', color: 'var(--gray-900)' }}>{member.name}</div>
                      <div style={{ fontSize: '13px', color: 'var(--gray-500)' }}>{member.email}</div>
                    </div>
                    <div className={`status-badge status-${member.status.toLowerCase()}`} style={{
                      padding: '4px 12px',
                      borderRadius: '20px',
                      fontSize: '11px',
                      fontWeight: '700',
                      background: member.status.toLowerCase() === 'active' ? '#dcfce7' : '#fefae8',
                      color: member.status.toLowerCase() === 'active' ? '#166534' : '#a16207',
                      textTransform: 'uppercase'
                    }}>
                      {member.status}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <footer className="modal-footer" style={{ padding: '20px 24px', borderTop: '1px solid var(--gray-100)' }}>
          <button className="btn btn-primary" onClick={onClose}>Close</button>
        </footer>
      </div>
    </div>
  );
}
