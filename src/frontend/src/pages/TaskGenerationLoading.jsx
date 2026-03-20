import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getTaskGenerationStatusRequest } from '../api';

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 200; // Allow up to 10 minutes for granular task generation

const STATUS_MESSAGES = {
  not_started: 'Initiating task generation...',
  generating: 'AI is analyzing your Technical Specification and generating tasks...',
  thinking: 'AI is analyzing your Technical Specification and generating tasks...',
  completed: 'Tasks generated successfully! Redirecting...',
  failed: 'Task generation failed. Please try again from the Technical Specification page.',
  failed_missing_docs: 'Requirement or Technical Specification is missing. Please complete them first.',
};

export default function TaskGenerationLoading() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('not_started');
  const [error, setError] = useState(null);
  const pollTimerRef = useRef(null);
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (!projectId) return;

    const pollStatus = async () => {
      try {
        attemptsRef.current += 1;
        const data = await getTaskGenerationStatusRequest(projectId);
        const currentStatus = data.status;
        setStatus(currentStatus);

        if (currentStatus === 'completed') {
          stopPolling();
          // Small delay to show "Completed" message
          setTimeout(() => {
            navigate(`/project/${projectId}`);
          }, 1500);
        } else if (currentStatus === 'failed' || currentStatus === 'failed_missing_docs') {
          stopPolling();
          setError(STATUS_MESSAGES[currentStatus] || 'An unexpected error occurred.');
        } else if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
          stopPolling();
          setError('Task generation is taking longer than expected. Please check the Tasks tab in a few moments.');
        }
      } catch (err) {
        console.error('Polling error:', err);
        // Don't stop immediately on one network error
        if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
          stopPolling();
          setError('Failed to fetch status. Please check your connection.');
        }
      }
    };

    const stopPolling = () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };

    // Initial check
    pollStatus();
    // Start interval
    pollTimerRef.current = setInterval(pollStatus, POLL_INTERVAL_MS);

    return () => stopPolling();
  }, [projectId, navigate]);

  return (
    <div className="dashboard-loading" style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      minHeight: '80vh',
      textAlign: 'center',
      padding: '24px'
    }}>
      {!error ? (
        <>
          <div className="spinner" style={{ 
            width: '48px', 
            height: '48px', 
            border: '4px solid var(--brand-100)', 
            borderTop: '4px solid var(--brand-600)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            marginBottom: '24px'
          }}></div>
          <h2 style={{ color: 'var(--gray-900)', marginBottom: '12px' }}>Generating Project Tasks</h2>
          <p style={{ color: 'var(--gray-600)', maxWidth: '400px', fontSize: '16px', lineHeight: '1.5' }}>
            {STATUS_MESSAGES[status] || 'Processing...'}
          </p>
          <p style={{ color: 'var(--gray-400)', marginTop: '24px', fontSize: '14px' }}>
            This usually takes 30-60 seconds.
          </p>
        </>
      ) : (
        <>
          <div style={{ color: 'var(--error-600)', fontSize: '48px', marginBottom: '16px' }}>⚠️</div>
          <h2 style={{ color: 'var(--gray-900)', marginBottom: '12px' }}>Task Generation Issue</h2>
          <p style={{ color: 'var(--gray-600)', maxWidth: '400px', fontSize: '16px', marginBottom: '24px' }}>
            {error}
          </p>
          <button 
            className="btn btn-primary" 
            onClick={() => navigate(`/project/${projectId}`)}
          >
            Back to Project
          </button>
        </>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}} />
    </div>
  );
}
