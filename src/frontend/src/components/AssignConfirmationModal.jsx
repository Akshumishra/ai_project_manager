import React from 'react';

export default function AssignConfirmationModal({ isOpen, onClose, onConfirm, pendingMembers = [] }) {
  if (!isOpen) return null;

  const pendingNames = pendingMembers.map(m => m.name).join(', ');

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '460px' }}>
        <header className="modal-header" style={{ borderBottom: 'none', paddingBottom: '0' }}>
          <div style={{ textAlign: 'center', width: '100%', paddingTop: '10px' }}>
            <h3 style={{ fontSize: '22px', fontWeight: '800', color: 'var(--gray-900)' }}>Assign Tasks</h3>
            <p className="modal-description" style={{ marginTop: '4px' }}>Confirm the AI-driven task assignment</p>
          </div>
          <button onClick={onClose} className="btn-close">&times;</button>
        </header>

        <div className="modal-body" style={{ paddingTop: '10px' }}>
          <div style={{ 
            background: pendingNames ? '#fffbeb' : '#f0fdf4', 
            border: `1.5px solid ${pendingNames ? '#fde68a' : '#bbf7d0'}`, 
            borderRadius: '20px', 
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '16px',
            boxShadow: `0 4px 12px ${pendingNames ? 'rgba(180, 83, 9, 0.05)' : 'rgba(22, 101, 52, 0.05)'}`
          }}>
            <div style={{ 
              width: '48px', 
              height: '48px', 
              borderRadius: '50%', 
              background: pendingNames ? '#f59e0b' : '#4ade80', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              fontSize: '24px',
              color: 'white'
            }}>
              {pendingNames ? '⚠️' : '✅'}
            </div>
            <p style={{ 
              fontSize: '15.5px', 
              lineHeight: '1.6', 
              color: pendingNames ? '#92400e' : '#166534', 
              fontWeight: '600',
              textAlign: 'center',
              margin: 0
            }}>
              {pendingNames 
                ? `Tasks will not be assigned to ${pendingNames} because they are not currently active.`
                : "All members are active! The AI will intelligently assign tasks based on individual skills and workload."
              }
            </p>
          </div>
        </div>

        <footer className="modal-footer" style={{ 
          display: 'flex', 
          gap: '12px', 
          padding: '24px', 
          borderTop: '1px solid var(--gray-100)',
          background: 'var(--gray-50)'
        }}>
          <button className="btn btn-secondary" onClick={onClose} style={{ flex: 1, height: '48px' }}>
            Cancel
          </button>
          <button 
            className="btn btn-primary" 
            onClick={() => { onConfirm(); onClose(); }} 
            style={{ 
              flex: 1, 
              height: '48px',
              background: 'var(--brand-600)',
              boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
            }}
          >
            Continue
          </button>
        </footer>
      </div>
    </div>
  );
}
