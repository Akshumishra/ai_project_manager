import React, { useState, useEffect } from 'react';
import api, { createProjectTaskRequest, updateProjectTaskRequest } from '../api';

export default function AddTaskModal({ isOpen, onClose, projectId, onSuccess, members, task = null }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [complexity, setComplexity] = useState('medium');
  const [deadline, setDeadline] = useState('');
  const [assigneeId, setAssigneeId] = useState('');
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isEditMode = !!task;

  useEffect(() => {
    if (isOpen) {
      if (isEditMode) {
        setTitle(task.title || '');
        
        // Parse description and acceptance criteria
        const desc = task.description || '';
        if (desc.includes('### Acceptance Criteria')) {
          const parts = desc.split('### Acceptance Criteria');
          setDescription(parts[0].trim());
          setAcceptanceCriteria(parts[1].trim());
        } else {
          setDescription(desc);
          setAcceptanceCriteria('');
        }

        setComplexity((task.complexity || 'medium').toLowerCase());
        setDeadline(task.deadline ? task.deadline.split('T')[0] : '');
        setAssigneeId(task.project_member_id || '');
      } else {
        setTitle('');
        setDescription('');
        setAcceptanceCriteria('');
        setComplexity('medium');
        setDeadline('');
        setAssigneeId('');
      }
      setError('');
    }
  }, [isOpen, task, isEditMode]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    setLoading(true);
    setError('');

    // Merge description and acceptance criteria
    let finalDescription = description.trim();
    if (acceptanceCriteria.trim()) {
      finalDescription += `\n\n### Acceptance Criteria\n${acceptanceCriteria.trim()}`;
    }

    const payload = {
      title: title.trim(),
      description: finalDescription,
      complexity: complexity,
      deadline: deadline ? new Date(deadline).toISOString() : null,
      project_member_id: assigneeId || null
    };

    try {
      let result;
      if (isEditMode) {
        result = await updateProjectTaskRequest(projectId, task.id, payload);
      } else {
        result = await createProjectTaskRequest(projectId, payload);
      }
      onSuccess(result);
      onClose();
    } catch (err) {
      console.error(isEditMode ? 'Failed to update task:' : 'Failed to create task:', err);
      setError(err.response?.data?.detail || `Failed to ${isEditMode ? 'update' : 'create'} task. Please try again.`);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '600px' }}>
        <div className="modal-header">
          <h2>{isEditMode ? 'Edit Task' : 'Add New Task'}</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-body">
          {error && <div className="modal-alert error">{error}</div>}

          <div className="form-group">
            <label htmlFor="task-title">Task Title</label>
            <input
              id="task-title"
              type="text"
              className="input"
              placeholder="e.g. Implement User Authentication"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="task-description">Requirement / Description</label>
            <textarea
              id="task-description"
              className="input"
              placeholder="What are the specific requirements for this task?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className="form-group">
            <label htmlFor="task-acceptance">Acceptance Criteria</label>
            <textarea
              id="task-acceptance"
              className="input"
              placeholder="How do we know this task is complete?"
              value={acceptanceCriteria}
              onChange={(e) => setAcceptanceCriteria(e.target.value)}
              rows={3}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            <div className="form-group">
              <label htmlFor="task-complexity">Complexity</label>
              <select
                id="task-complexity"
                className="input"
                value={complexity}
                onChange={(e) => setComplexity(e.target.value)}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="task-deadline">Deadline</label>
              <input
                id="task-deadline"
                type="date"
                className="input"
                value={deadline}
                onChange={(e) => setDeadline(e.target.value)}
              />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="task-assignee">Assignee</label>
            <select
              id="task-assignee"
              className="input"
              value={assigneeId}
              onChange={(e) => setAssigneeId(e.target.value)}
            >
              <option value="">Unassigned</option>
              {members && members.map(member => (
                <option key={member.id} value={member.id}>
                  {member.name || member.email}
                </option>
              ))}
            </select>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading || !title.trim()}>
              {loading ? (isEditMode ? 'Updating...' : 'Creating...') : (isEditMode ? 'Update Task' : 'Add Task')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
