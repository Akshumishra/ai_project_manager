import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getTaskGenerationStatusRequest, autoAssignTasksRequest } from '../api';
import { useAuth } from '../context/AuthContext';
import AssignConfirmationModal from './AssignConfirmationModal';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 20;

const STATUS_LABELS = {
  not_started: null,
  generating: 'AI is generating tasks from your documents...',
  completed: 'Tasks generated successfully!',
  failed: 'Task generation failed. Please try again.',
  failed_missing_docs: 'Missing required documents. Please complete Requirement and Technical Specifications first.',
};

export default function ProjectTasks({ project, tasks, members = [], onCreateTask, refreshTasks }) {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const { user } = useAuth();
  const [genStatus, setGenStatus] = useState(null);
  const [assignStatus, setAssignStatus] = useState(null); // null | 'assigning' | 'done' | 'error'
  const [assignMessage, setAssignMessage] = useState('');
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const pollRef = useRef(null);
  const pollAttemptsRef = useRef(0);

  // On mount: check if generation is already running
  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    const checkInitialStatus = async () => {
      try {
        const statusData = await getTaskGenerationStatusRequest(projectId);
        if (cancelled) return;
        if (statusData.status === 'generating') {
          setGenStatus('generating');
          startPolling();
        } else if (statusData.status === 'completed' && tasks.length === 0) {
          setGenStatus('completed');
          await refreshTasks();
        }
      } catch (err) {
        // Status endpoint not available yet — silently ignore
      }
    };
    checkInitialStatus();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  // Auto-dismiss banners after 8 seconds
  useEffect(() => {
    if (genStatus === 'completed') {
      const t = setTimeout(() => setGenStatus(null), 600000);
      return () => clearTimeout(t);
    }
  }, [genStatus]);

  useEffect(() => {
    if (assignStatus === 'done' || assignStatus === 'error') {
      const t = setTimeout(() => { setAssignStatus(null); setAssignMessage(''); }, 80000);
      return () => clearTimeout(t);
    }
  }, [assignStatus]);

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  };

  const startPolling = () => {
    pollAttemptsRef.current = 0;
    pollRef.current = setInterval(async () => {
      pollAttemptsRef.current += 1;
      try {
        const statusData = await getTaskGenerationStatusRequest(projectId);
        const s = statusData.status;
        setGenStatus(s);

        if (s === 'completed') {
          stopPolling();
          await refreshTasks();
        } else if (s === 'failed' || s === 'failed_missing_docs') {
          stopPolling();
        } else if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
          stopPolling();
          setGenStatus('failed');
        }
      } catch (err) {
        console.error('Status poll error:', err);
        if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
          stopPolling();
          setGenStatus('failed');
        }
      }
    }, POLL_INTERVAL_MS);
  };


  const handleAssignTasks = () => {
    if (assignStatus === 'assigning') return;
    if (!user?.id) {
      setAssignStatus('error');
      setAssignMessage('User not authenticated. Please log in again.');
      return;
    }
    if (tasks.length === 0) {
      setAssignStatus('error');
      setAssignMessage('No tasks to assign. Generate tasks first.');
      return;
    }
    setIsAssignModalOpen(true);
  };

  const runAutoAssignment = async () => {
    setAssignStatus('assigning');
    setAssignMessage('');

    try {
      const result = await autoAssignTasksRequest(projectId, user.id);
      setAssignStatus('done');
      setAssignMessage(result.content || 'Tasks have been assigned successfully!');
      await refreshTasks(); // Refresh to show new assignees
    } catch (err) {
      console.error('Auto-assign failed:', err);
      const detail = err.response?.data?.detail || 'Auto-assignment failed. Please try again.';
      setAssignStatus('error');
      setAssignMessage(detail);
    }
  };

  const isBusy = genStatus === 'generating';
  const isGenError = genStatus === 'failed' || genStatus === 'failed_missing_docs';
  const isGenSuccess = genStatus === 'completed';

  const isAssigning = assignStatus === 'assigning';
  const isAssignError = assignStatus === 'error';
  const isAssignDone = assignStatus === 'done';
  const isCreator = user && project && user.id === project.created_by;

  const bannerBg = isGenError ? '#fef2f2' : isGenSuccess ? '#f0fdf4' : 'var(--brand-50)';
  const bannerBorder = isGenError ? '#fca5a5' : isGenSuccess ? '#86efac' : 'var(--brand-300)';
  const bannerText = isGenError ? '#b91c1c' : isGenSuccess ? '#166534' : 'var(--brand-700)';

  const assignBannerBg = isAssignError ? '#fef2f2' : isAssignDone ? '#f0fdf4' : 'var(--brand-50)';
  const assignBannerBorder = isAssignError ? '#fca5a5' : isAssignDone ? '#86efac' : 'var(--brand-300)';
  const assignBannerText = isAssignError ? '#b91c1c' : isAssignDone ? '#166534' : 'var(--brand-700)';

  return (
    <div className="tasks-panel">
      {/* Action Buttons */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: (genStatus || assignStatus) ? '16px' : '24px', gap: '12px' }}>

        {isCreator && (
          <button
            className="btn btn-secondary"
            onClick={handleAssignTasks}
            disabled={isAssigning}
            title="Automatically assign tasks to team members based on their skills"
            style={{ display: 'flex', alignItems: 'center', opacity: isAssigning ? 0.7 : 1 }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            {isAssigning ? 'Assigning...' : 'Assign Task (AI)'}
          </button>
        )}

        <button className="btn btn-primary" onClick={onCreateTask}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Task
        </button>
      </div>

      {/* Task Generation Status Banner */}
      {genStatus && (
        <div style={{
          padding: '14px 18px',
          background: bannerBg,
          border: `1.5px solid ${bannerBorder}`,
          borderRadius: '14px',
          marginBottom: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}>
          {isBusy && (
            <div style={{
              width: '20px', height: '20px',
              border: '3px solid var(--brand-200)',
              borderTop: '3px solid var(--brand-600)',
              borderRadius: '50%',
              flexShrink: 0,
              animation: 'spin 1s linear infinite',
            }} />
          )}
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, color: bannerText, fontWeight: '600', fontSize: '14px' }}>
              {STATUS_LABELS[genStatus] || genStatus}
            </p>
            {isBusy && (
              <p style={{ margin: '4px 0 0', color: 'var(--brand-600)', fontSize: '12px' }}>
                This can take up to a minute. The task list will refresh automatically.
              </p>
            )}
          </div>
          {!isBusy && (
            <button
              onClick={() => setGenStatus(null)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: bannerText, fontSize: '18px', padding: '4px', flexShrink: 0 }}
            >
              &times;
            </button>
          )}
        </div>
      )}

      {/* Task Assignment Status Banner */}
      {assignStatus && (
        <div style={{
          padding: '14px 18px',
          background: assignBannerBg,
          border: `1.5px solid ${assignBannerBorder}`,
          borderRadius: '14px',
          marginBottom: '20px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '14px',
        }}>
          {isAssigning && (
            <div style={{
              width: '20px', height: '20px',
              border: '3px solid var(--brand-200)',
              borderTop: '3px solid var(--brand-600)',
              borderRadius: '50%',
              flexShrink: 0,
              marginTop: '2px',
              animation: 'spin 1s linear infinite',
            }} />
          )}
          <div style={{ flex: 1 }}>
            <p style={{ margin: 0, color: assignBannerText, fontWeight: '600', fontSize: '14px' }}>
              {isAssigning ? 'AI is analyzing and assigning tasks to team members...' :
               isAssignDone ? 'Task assignment complete!' :
               `${assignMessage}`}
            </p>
            {isAssigning && (
              <p style={{ margin: '4px 0 0', color: 'var(--brand-600)', fontSize: '12px' }}>
                The AI will balance workload and match tasks to member skills.
              </p>
            )}
            {isAssignDone && assignMessage && (
              <p style={{ margin: '6px 0 0', color: assignBannerText, fontSize: '12px', whiteSpace: 'pre-wrap' }}>
                {assignMessage}
              </p>
            )}
          </div>
          {!isAssigning && (
            <button
              onClick={() => { setAssignStatus(null); setAssignMessage(''); }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: assignBannerText, fontSize: '18px', padding: '4px', flexShrink: 0 }}
            >
              &times;
            </button>
          )}
        </div>
      )}

      {/* Task List */}
      {tasks.length === 0 ? (
        <div className="no-docs">
          <p>No tasks for this project yet. Use &quot;Add Task&quot; to create one, or complete your Technical Specification to generate tasks automatically.</p>
        </div>
      ) : (
        <div className="task-list">
          {tasks.map(task => (
            <div key={task.id} className="task-card">
              <div className="task-header" style={{ position: 'relative' }}>
                <div style={{ paddingRight: '40px' }}>
                  <h3
                    onClick={() => navigate(`/project/${projectId}/task/${task.id}`)}
                    style={{ cursor: 'pointer', color: 'var(--brand-600)' }}
                  >
                    <span style={{ marginRight: '8px', color: 'var(--gray-400)' }}>#{task.label}</span>
                    {task.title}
                  </h3>
                </div>
                <div style={{ position: 'absolute', top: 0, right: 0, display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <span className={`task-status status-${(task.status || 'todo').toLowerCase().replace('_', '-')}`}>
                    {(task.status || 'todo').replace('_', ' ')}
                  </span>
                </div>
              </div>
              <p className="task-description">{task.description}</p>
              <div className="task-meta">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  {task.deadline && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '13px', color: 'var(--gray-600)' }}>
                      📅 {new Date(task.deadline).toLocaleDateString()}
                    </span>
                  )}
                  {task.complexity && (
                    <span style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '10px',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      backgroundColor:
                        task.complexity.toLowerCase() === 'critical' ? '#fee2e2' :
                        task.complexity.toLowerCase() === 'high' ? '#ffedd5' :
                        task.complexity.toLowerCase() === 'medium' ? '#f0f9ff' : '#f0fdf4',
                      color:
                        task.complexity.toLowerCase() === 'critical' ? '#991b1b' :
                        task.complexity.toLowerCase() === 'high' ? '#9a3412' :
                        task.complexity.toLowerCase() === 'medium' ? '#075985' : '#166534',
                    }}>
                      {task.complexity}
                    </span>
                  )}
                  {task.category && (
                    <span style={{ fontSize: '12px', color: 'var(--gray-500)', fontStyle: 'italic' }}>
                      {task.category.replace('_', '/')}
                    </span>
                  )}
                </div>
                {task.assignee_name && (
                  <div style={{
                    marginTop: '12px', paddingTop: '12px',
                    borderTop: '1px solid var(--gray-100)',
                    display: 'flex', alignItems: 'center',
                    fontSize: '12px', color: 'var(--gray-600)'
                  }}>
                    <div style={{
                      width: '24px', height: '24px', borderRadius: '50%',
                      background: 'var(--brand-600)', color: 'white',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      marginRight: '8px', fontSize: '10px', fontWeight: 'bold'
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

      <AssignConfirmationModal
        isOpen={isAssignModalOpen}
        onClose={() => setIsAssignModalOpen(false)}
        onConfirm={runAutoAssignment}
        pendingMembers={members.filter(m => m.status?.toLowerCase() !== 'active')}
      />
    </div>
  );
}
