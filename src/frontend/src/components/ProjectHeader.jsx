import React, { useState } from 'react';

export default function ProjectHeader({ user, project, onBack, onUpdateStatus, onAddMember, onViewMembers }) {
  const [isUpdating, setIsUpdating] = useState(false);
  const isCreator = user && project && user.id === project.created_by;

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    if (newStatus === project.status) return;

    setIsUpdating(true);
    const success = await onUpdateStatus(newStatus);
    if (!success) {
      alert('Failed to update project status');
    }
    setIsUpdating(false);
  };
  return (
    <header className="dashboard-header" style={{ marginBottom: '32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <button className="btn btn-ghost" onClick={onBack} title="Back to Dashboard">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <div>
          <h1>Project Dashboard</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <p className="welcome-text" style={{ margin: 0 }}>Manage your workspace for <strong>{user?.name || user?.email}</strong></p>
            {project && (
              <div className="project-status-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {isCreator ? (
                  <select
                    className="status-select"
                    value={project.status}
                    onChange={handleStatusChange}
                    disabled={isUpdating}
                    style={{
                      padding: '2px 8px',
                      borderRadius: '6px',
                      border: '1px solid var(--gray-200)',
                      fontSize: '12px',
                      fontWeight: '600',
                      textTransform: 'uppercase',
                      cursor: 'pointer',
                      backgroundColor: project.status === 'active' ? '#f0fdf4' : project.status === 'completed' ? '#f0f9ff' : '#fff7ed',
                      color: project.status === 'active' ? '#166534' : project.status === 'completed' ? '#075985' : '#9a3412',
                    }}
                  >
                    <option value="active">Active</option>
                    <option value="completed">Completed</option>
                    <option value="hold">Hold</option>
                  </select>
                ) : (
                  <span
                    className="status-badge"
                    style={{
                      padding: '2px 10px',
                      borderRadius: '12px',
                      fontSize: '11px',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      backgroundColor: project.status === 'active' ? '#f0fdf4' : project.status === 'completed' ? '#f0f9ff' : '#fff7ed',
                      color: project.status === 'active' ? '#166534' : project.status === 'completed' ? '#075985' : '#9a3412',
                    }}
                  >
                    {project.status}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '10px' }}>
        {isCreator && (
          <button className="btn btn-secondary" onClick={onAddMember}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="8.5" cy="7" r="4" /><line x1="20" y1="8" x2="20" y2="14" /><line x1="23" y1="11" x2="17" y2="11" />
            </svg>
            Add Member
          </button>
        )}
        <button className="btn btn-outline" onClick={onViewMembers}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
          </svg>
          View All Members
        </button>
      </div>
    </header>
  );
}
