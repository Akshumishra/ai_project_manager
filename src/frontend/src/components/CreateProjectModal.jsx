import React, { useState } from 'react';
import api from '../api';
import { setProjectContext } from '../utils/agent_storage';
import { useAuth } from '../context/AuthContext';

export default function CreateProjectModal({ isOpen, onClose, onSuccess }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [background, setBackground] = useState('technical');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { user } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    
    setLoading(true);
    setError('');

    try {
      const res = await api.post('/api/projects/', { 
        name: name.trim(), 
        description: description.trim(),
        background: background
      });
      
      const projectId = res.data.id;
      setProjectContext(projectId, { 
        userId: user?.id, 
        background: background 
      });

      setName('');
      setDescription('');
      onSuccess(projectId);
      onClose();
    } catch (err) {
      console.error('Create project failed:', err);
      setError(err.response?.data?.detail || 'Failed to create project. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h2>Create New Project</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="modal-alert error">{error}</div>}

          <div className="form-group">
            <label htmlFor="project-name">Project Name <span className="required-star">*</span></label>
            <input
              id="project-name"
              type="text"
              placeholder="e.g. My Awesome App"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="project-description">Description (Optional)</label>
            <textarea
              id="project-description"
              placeholder="Describe the scope or goals of this project..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Your Background</label>
            <div style={{ display: 'flex', gap: '20px', marginTop: '8px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="background"
                  value="technical"
                  checked={background === 'technical'}
                  onChange={() => setBackground('technical')}
                />
                Technical
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="radio"
                  name="background"
                  value="non_technical"
                  checked={background === 'non_technical'}
                  onChange={() => setBackground('non_technical')}
                />
                Non-Technical
              </label>
            </div>
          </div>
          
          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
