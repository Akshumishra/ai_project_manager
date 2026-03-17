import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { generateTasksRequest, getTaskGenerationStatusRequest } from '../api';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 20; // ~60s

const STATUS_LABELS = {
  not_started: null,
  generating: 'AI is generating tasks from your documents...',
  completed: '✅ Tasks generated successfully!',
  failed: '❌ Task generation failed. Please try again.',
  failed_missing_docs: '⚠️ Missing required documents. Please complete Requirement and Technical Specifications first.',
};

export default function ProjectTasks({ tasks, onCreateTask, refreshTasks }) {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [genStatus, setGenStatus] = useState(null); // null | 'generating' | 'completed' | 'failed' | 'failed_missing_docs'
  const pollRef = useRef(null);
  const pollAttemptsRef = useRef(0);

  // On mount: check if generation is already running (e.g. user was redirected here after tech doc save)
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
          // Generation just finished but tasks haven't loaded yet → refresh
          setGenStatus('completed');
          await refreshTasks();
        }
      } catch (err) {
        // Status endpoint not available yet or no job started — silently ignore
      }
    };
    checkInitialStatus();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);


  // Auto-dismiss success banner after 8 seconds
  useEffect(() => {
    if (genStatus === 'completed') {
      const t = setTimeout(() => setGenStatus(null), 8000);
      return () => clearTimeout(t);
    }
  }, [genStatus]);

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
          await refreshTasks(); // Load the newly created tasks
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

  const handleGenerateTasks = async () => {
    if (genStatus === 'generating') return;
    stopPolling();
    setGenStatus('generating');

    try {
      await generateTasksRequest(projectId);
      startPolling();
    } catch (err) {
      console.error('Failed to generate tasks:', err);
      const detail = err.response?.data?.detail || 'Failed to start task generation.';
      setGenStatus('failed');
    }
  };

  const isBusy = genStatus === 'generating';
  const isError = genStatus === 'failed' || genStatus === 'failed_missing_docs';
  const isSuccess = genStatus === 'completed';

  const bannerBg = isError ? '#fef2f2' : isSuccess ? '#f0fdf4' : 'var(--brand-50)';
  const bannerBorder = isError ? '#fca5a5' : isSuccess ? '#86efac' : 'var(--brand-300)';
  const bannerText = isError ? '#b91c1c' : isSuccess ? '#166534' : 'var(--brand-700)';

  return (
    <div className="tasks-panel">
      {/* Action Buttons */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: genStatus ? '16px' : '24px', gap: '12px' }}>
        <button
          className="btn btn-secondary"
          onClick={handleGenerateTasks}
          disabled={isBusy}
          style={{ display: 'flex', alignItems: 'center', opacity: isBusy ? 0.7 : 1 }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          {isBusy ? 'Generating...' : 'Assign Task (AI)'}
        </button>
        <button className="btn btn-primary" onClick={onCreateTask}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Task
        </button>
      </div>

      {/* Live Status Banner */}
      {genStatus && (
        <div style={{
          padding: '14px 18px',
          background: bannerBg,
          border: `1.5px solid ${bannerBorder}`,
          borderRadius: '14px',
          marginBottom: '20px',
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

      {/* Task List */}
      {tasks.length === 0 ? (
        <div className="no-docs">
          <p>No tasks for this project yet. Use "Add Task" to create one, or "Assign Task (AI)" to generate from your documents.</p>
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
    </div>
  );
}
