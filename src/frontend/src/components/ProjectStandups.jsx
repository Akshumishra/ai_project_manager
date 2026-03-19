import React, { useState, useEffect } from 'react';
import api from '../api';

export default function ProjectStandups({ projectId }) {
  const [standups, setStandups] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStandups();
  }, [projectId]);

  const fetchStandups = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/api/projects/${projectId}/standups`);
      setStandups(data);
    } catch (err) {
      console.error('Failed to fetch standups:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div style={{ display: 'flex', justifyContent: 'center', padding: '40px' }}><div className="spinner"></div></div>;

  return (
    <div className="standups-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', color: 'var(--gray-900)' }}>Daily Standups</h2>
        <button className="btn btn-secondary" onClick={fetchStandups}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
          </svg>
          Refresh
        </button>
      </div>

      {standups.length === 0 ? (
        <div className="no-docs">
          <p>No standups recorded for this project yet.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {standups.map(standup => (
            <div key={standup.id} className="document-card" style={{ padding: '24px', cursor: 'default' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div>
                  <span style={{ fontSize: '12px', color: 'var(--brand-600)', fontWeight: 'bold', textTransform: 'uppercase' }}>
                    {new Date(standup.created_at).toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                  </span>
                  <h3 style={{ margin: '4px 0 0 0', fontSize: '18px' }}>Daily Summary</h3>
                </div>
                <span style={{ fontSize: '12px', color: 'var(--gray-400)' }}>
                  {new Date(standup.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              
              <div className="standup-content">
                <div style={{ marginBottom: '16px', padding: '16px', background: 'var(--gray-50)', borderRadius: '12px' }}>
                  <h4 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>AI Summary</h4>
                  <p style={{ margin: 0, fontSize: '15px', color: 'var(--gray-800)', lineHeight: '1.6' }}>
                    {standup.summary || 'No summary generated yet.'}
                  </p>
                </div>
                
                {standup.prompt && (
                  <div>
                    <h4 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>Prompt</h4>
                    <p style={{ margin: 0, fontSize: '14px', color: 'var(--gray-600)', fontStyle: 'italic' }}>
                      {standup.prompt}
                    </p>
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
