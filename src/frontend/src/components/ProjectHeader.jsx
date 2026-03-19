import React, { useState, useEffect, useRef } from 'react';


import { joinSlackChannelRequest, triggerSlackSetup, getProjectRequest } from '../api';

export default function ProjectHeader({ user, project, onBack, onUpdateStatus, onAddMember, onViewMembers, onProjectUpdated }) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [isJoiningSlack, setIsJoiningSlack] = useState(false);
  const [isInitializingSlack, setIsInitializingSlack] = useState(false);
  const pollingRef = useRef(null);
  const isCreator = user && project && user.id === project.created_by;

  // Clean up polling on unmount
  useEffect(() => {
    return () => { if (pollingRef.current) clearInterval(pollingRef.current); };
  }, []);

  const handleStatusChange = async (e) => {
    const newStatus = e.target.value;
    if (newStatus === project.status) return;
    setIsUpdating(true);
    const success = await onUpdateStatus(newStatus);
    if (!success) alert('Failed to update project status');
    setIsUpdating(false);
  };

  const handleJoinSlack = async () => {
    setIsJoiningSlack(true);
    try {
      const result = await joinSlackChannelRequest(project.id);
      if (result.invite_sent) {
        alert('You are being redirected to Slack.');
      }
      window.open(result.redirect_url, '_blank', 'noopener,noreferrer');
    } catch {
      alert('Failed to join Slack channel. Make sure the project has a channel set up.');
    } finally {
      setIsJoiningSlack(false);
    }
  };

  const handleInitializeSlack = async () => {
    setIsInitializingSlack(true);
    try {
      await triggerSlackSetup(project.id);

      // Poll every 3s for up to 30s until slack_channel_id appears on the project
      let attempts = 0;
      pollingRef.current = setInterval(async () => {
        attempts++;
        try {
          const updated = await getProjectRequest(project.id);
          if (updated.slack_channel_id) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
            setIsInitializingSlack(false);
            if (onProjectUpdated) onProjectUpdated(updated);
          } else if (attempts >= 10) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
            setIsInitializingSlack(false);
            alert('Slack channel setup is taking longer than expected. It will appear automatically once ready — please refresh in a moment.');
          }
        } catch {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
          setIsInitializingSlack(false);
        }
      }, 3000);
    } catch {
      setIsInitializingSlack(false);
      alert('Failed to start Slack channel setup. Make sure SLACK_BOT_TOKEN is configured.');
    }
  };

  return (
    <>
      <header className="dashboard-header" style={{
        marginBottom: '32px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '20px',
        flexWrap: 'nowrap'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', minWidth: 0 }}>
          <button className="btn btn-ghost" onClick={onBack} title="Back to Dashboard">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
          <div style={{ minWidth: 0 }}>
            <h1 style={{ margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Project Dashboard</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <p className="welcome-text" style={{ margin: 0, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '13px' }}>
                Account: <strong>{user?.name || user?.email}</strong>
              </p>
              {project && (
                <div className="project-status-wrapper" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {isCreator ? (
                    <select
                      className="status-select"
                      value={project.status}
                      onChange={handleStatusChange}
                      disabled={isUpdating}
                      style={{
                        padding: '2px 8px', borderRadius: '6px', border: '1px solid var(--gray-200)',
                        fontSize: '12px', fontWeight: '600', textTransform: 'uppercase', cursor: 'pointer',
                        backgroundColor: project.status === 'active' ? '#f0fdf4' : project.status === 'completed' ? '#f0f9ff' : '#fff7ed',
                        color: project.status === 'active' ? '#166534' : project.status === 'completed' ? '#075985' : '#9a3412',
                      }}
                    >
                      <option value="active">Active</option>
                      <option value="completed">Completed</option>
                      <option value="hold">Hold</option>
                    </select>
                  ) : (
                    <span className="status-badge" style={{
                      padding: '2px 10px', borderRadius: '12px', fontSize: '11px',
                      fontWeight: '700', textTransform: 'uppercase',
                      backgroundColor: project.status === 'active' ? '#f0fdf4' : project.status === 'completed' ? '#f0f9ff' : '#fff7ed',
                      color: project.status === 'active' ? '#166534' : project.status === 'completed' ? '#075985' : '#9a3412',
                    }}>
                      {project.status}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'nowrap', flexShrink: 0 }}>

          {/* ── Join Slack (channel exists) ── */}
          {project?.slack_channel_id && (
            <button
              className="btn"
              onClick={handleJoinSlack}
              disabled={isJoiningSlack}
              title="Open this project's Slack channel"
              style={{
                background: '#4A154B', color: '#fff', border: 'none',
                padding: '8px 16px', borderRadius: '8px',
                fontWeight: '600', fontSize: '13px', cursor: 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
                opacity: isJoiningSlack ? 0.7 : 1,
              }}
            >
              <svg width="16" height="16" viewBox="0 0 122.8 122.8" fill="white">
                <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zm6.5 0c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z"/>
                <path d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2zm0 6.5c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9h32.3z"/>
                <path d="M97 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.2zm-6.5 0c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.7 5.8 70.5 0 77.6 0s12.9 5.8 12.9 12.9v32.3z"/>
                <path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9zm0-6.5c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z"/>
              </svg>
              {isJoiningSlack ? 'Opening…' : 'Join Slack'}
            </button>
          )}

          {/* ── Initialize Slack (creator only, no channel yet) ── */}
          {isCreator && !project?.slack_channel_id && (
            <button
              className="btn"
              onClick={handleInitializeSlack}
              disabled={isInitializingSlack}
              title="Auto-create a Slack channel for this project"
              style={{
                background: isInitializingSlack ? '#7b5c7c' : '#4A154B',
                color: '#fff', border: 'none',
                padding: '8px 16px', borderRadius: '8px',
                fontWeight: '600', fontSize: '13px', cursor: isInitializingSlack ? 'default' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '6px',
              }}
            >
              {isInitializingSlack ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"
                    style={{ animation: 'spin 1s linear infinite' }}>
                    <path d="M21 12a9 9 0 11-6.219-8.56"/>
                  </svg>
                  Initializing…
                </>
              ) : (
                <>
                  <svg width="16" height="16" viewBox="0 0 122.8 122.8" fill="white">
                    <path d="M25.8 77.6c0 7.1-5.8 12.9-12.9 12.9S0 84.7 0 77.6s5.8-12.9 12.9-12.9h12.9v12.9zm6.5 0c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9v32.3c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V77.6z"/>
                    <path d="M45.2 25.8c-7.1 0-12.9-5.8-12.9-12.9S38.1 0 45.2 0s12.9 5.8 12.9 12.9v12.9H45.2zm0 6.5c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H12.9C5.8 58.1 0 52.3 0 45.2s5.8-12.9 12.9-12.9h32.3z"/>
                    <path d="M97 45.2c0-7.1 5.8-12.9 12.9-12.9s12.9 5.8 12.9 12.9-5.8 12.9-12.9 12.9H97V45.2zm-6.5 0c0 7.1-5.8 12.9-12.9 12.9s-12.9-5.8-12.9-12.9V12.9C64.7 5.8 70.5 0 77.6 0s12.9 5.8 12.9 12.9v32.3z"/>
                    <path d="M77.6 97c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9-12.9-5.8-12.9-12.9V97h12.9zm0-6.5c-7.1 0-12.9-5.8-12.9-12.9s5.8-12.9 12.9-12.9h32.3c7.1 0 12.9 5.8 12.9 12.9s-5.8 12.9-12.9 12.9H77.6z"/>
                  </svg>
                  Initialize Slack
                </>
              )}
            </button>
          )}

          {/* ── Add Member (creator only) ── */}
          {isCreator && (
            <button className="btn btn-secondary" onClick={onAddMember}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="8.5" cy="7" r="4" />
                <line x1="20" y1="8" x2="20" y2="14" />
                <line x1="23" y1="11" x2="17" y2="11" />
              </svg>
              Add Member
            </button>
          )}

          {/* ── View All Members ── */}
          <button className="btn btn-outline" onClick={onViewMembers}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            View All Members
          </button>
        </div>
      </header>

      {/* Spin keyframe */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
