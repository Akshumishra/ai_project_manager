import { useState } from 'react';
import api from '../../../shared/api/api';

export default function CreateProjectModal({ isOpen, onClose, onSuccess }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/api/projects/', { 
        name: name.trim(), 
        description: description.trim() 
      });
      
      setName('');
      setDescription('');
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Create project failed:', err);
      setError(err.response?.data?.detail || 'Failed to create project. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create New Project</h3>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        
        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="modal-alert error">{error}</div>}

          <div className="form-group">
            <label htmlFor="project-name">Project Name</label>
            <input
              id="project-name"
              type="text"
              placeholder="e.g., Marketing Campaign 2024"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="modal-input"
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
              className="modal-input"
              rows={3}
            />
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
