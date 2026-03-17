import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api';
import { useAuth } from '../context/AuthContext';

export default function TaskDetailPage() {
  const { projectId, taskId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [members, setMembers] = useState([]);
  const [logs, setLogs] = useState([]);
  const [editForm, setEditForm] = useState({
    title: '',
    description: '',
    status: '',
    complexity: '',
    deadline: '',
    project_member_id: ''
  });

  useEffect(() => {
    fetchTask();
    fetchMembers();
    fetchLogs();
  }, [projectId, taskId]);

  const fetchMembers = async () => {
    try {
      const { data } = await api.get(`/api/projects/${projectId}/members`);
      setMembers(data);
    } catch (err) {
      console.error('Failed to fetch members:', err);
    }
  };

  const fetchTask = async () => {
    try {
      setLoading(true);
      const { data } = await api.get(`/api/projects/${projectId}/tasks/${taskId}`);
      setTask(data);
      setEditForm({
        title: data.title,
        description: data.description || '',
        status: data.status,
        complexity: data.complexity,
        deadline: data.deadline ? data.deadline.split('T')[0] : '',
        project_member_id: data.project_member_id || ''
      });
    } catch (err) {
      setError('Failed to fetch task details');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLogs = async () => {
    try {
      const { data } = await api.get(`/api/projects/${projectId}/tasks/${taskId}/logs`);
      setLogs(data);
    } catch (err) {
      console.error('Failed to fetch logs:', err);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      const { data } = await api.patch(`/api/projects/${projectId}/tasks/${taskId}`, editForm);
      setTask(data);
      setIsEditing(false);
      fetchLogs(); // Refresh logs after update
    } catch (err) {
      setError('Failed to update task');
    }
  };

  if (loading) return <div className="dashboard-loading"><div className="spinner"></div></div>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!task) return <div>Task not found</div>;

  return (
    <div className="project-detail-container" style={{ padding: '40px', background: 'var(--gray-50)', minHeight: '100vh', display: 'flex', justifyContent: 'center' }}>
      <div className="document-container" style={{ width: '100%', maxWidth: '800px', background: 'white', padding: '40px', borderRadius: '24px', boxShadow: 'var(--shadow-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '32px' }}>
          <button 
            onClick={() => navigate(`/project/${projectId}`)} 
            className="btn-link" 
            style={{ display: 'flex', alignItems: 'center', gap: '8px', textDecoration: 'none', color: 'var(--gray-500)', fontSize: '14px' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            Back to Project
          </button>
        </div>

        {isEditing ? (
          <form onSubmit={handleUpdate} className="auth-form" style={{ maxWidth: 'none', padding: 0, boxShadow: 'none' }}>
            <div className="form-group">
              <label>Title <span className="required-star">*</span></label>
              <input 
                type="text" 
                value={editForm.title} 
                onChange={(e) => setEditForm({...editForm, title: e.target.value})} 
                required 
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea 
                value={editForm.description} 
                onChange={(e) => setEditForm({...editForm, description: e.target.value})} 
                rows="4"
                style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid var(--gray-200)' }}
              />
            </div>
            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
              <div className="form-group">
                <label>Status</label>
                <select 
                  value={editForm.status} 
                  onChange={(e) => setEditForm({...editForm, status: e.target.value})}
                  style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid var(--gray-200)' }}
                >
                  <option value="todo">Todo</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="blocked">Blocked</option>
                </select>
              </div>
              <div className="form-group">
                <label>Complexity</label>
                <select 
                  value={editForm.complexity} 
                  onChange={(e) => setEditForm({...editForm, complexity: e.target.value})}
                  style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid var(--gray-200)' }}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
            <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginTop: '20px' }}>
              <div className="form-group">
                <label>Deadline</label>
                <input 
                  type="date" 
                  value={editForm.deadline} 
                  onChange={(e) => setEditForm({...editForm, deadline: e.target.value})}
                  style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid var(--gray-200)' }}
                />
              </div>
              <div className="form-group">
                <label>Assigned To</label>
                <select 
                  value={editForm.project_member_id} 
                  onChange={(e) => setEditForm({...editForm, project_member_id: e.target.value})}
                  style={{ width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid var(--gray-200)' }}
                >
                  <option value="">Unassigned</option>
                  {members.map(member => (
                    <option key={member.id} value={member.id}>{member.name}</option>
                  ))}
                </select>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px', marginTop: '24px' }}>
              <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Save Changes</button>
              <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => setIsEditing(false)}>Cancel</button>
            </div>
          </form>
        ) : (
          <div className="task-detail-view">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
              <div>
                <span style={{ color: 'var(--brand-600)', fontWeight: 'bold', fontSize: '18px' }}>#{task.label}</span>
                <h1 style={{ marginTop: '8px', fontSize: '32px', color: 'var(--gray-900)' }}>{task.title}</h1>
              </div>
              <button className="btn btn-secondary" onClick={() => setIsEditing(true)}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
                Edit Task
              </button>
            </div>

            <div style={{ marginBottom: '32px' }}>
              <h3 style={{ fontSize: '14px', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>Description</h3>
              <p style={{ color: 'var(--gray-700)', lineHeight: '1.6', fontSize: '16px' }}>{task.description || 'No description provided.'}</p>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px', padding: '24px', background: 'var(--gray-50)', borderRadius: '16px' }}>
              <div>
                <h3 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>Status</h3>
                <span className={`task-status status-${task.status.toLowerCase()}`} style={{ fontSize: '14px', padding: '4px 12px' }}>
                  {task.status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <div>
                <h3 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>Complexity</h3>
                <span className={`badge-complexity ${task.complexity.toLowerCase()}`} style={{ 
                  fontSize: '14px', 
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontWeight: 'bold',
                  backgroundColor: task.complexity.toLowerCase() === 'high' ? '#fee2e2' : task.complexity.toLowerCase() === 'medium' ? '#f0f9ff' : '#f0fdf4',
                  color: task.complexity.toLowerCase() === 'high' ? '#991b1b' : task.complexity.toLowerCase() === 'medium' ? '#075985' : '#166534'
                }}>
                  {task.complexity.toUpperCase()}
                </span>
              </div>
              <div>
                <h3 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>Assignee</h3>
                {task.assignee_name ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'var(--brand-600)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold' }}>
                      {task.assignee_name.charAt(0).toUpperCase()}
                    </div>
                    <span>{task.assignee_name}</span>
                  </div>
                ) : <span style={{ color: 'var(--gray-400)', fontStyle: 'italic' }}>Unassigned</span>}
              </div>
              <div>
                <h3 style={{ fontSize: '12px', color: 'var(--gray-500)', textTransform: 'uppercase', marginBottom: '8px' }}>Deadline</h3>
                {task.deadline ? (
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--gray-900)' }}>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                    {new Date(task.deadline).toLocaleDateString()}
                  </span>
                ) : <span style={{ color: 'var(--gray-400)', fontStyle: 'italic' }}>No deadline set</span>}
              </div>
            </div>

            <div style={{ marginTop: '40px' }}>
              <h3 style={{ fontSize: '14px', color: 'var(--gray-500)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20v-6M6 20V10M18 20V4"/></svg>
                Activity Log
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {logs.length === 0 ? (
                  <p style={{ color: 'var(--gray-400)', fontSize: '14px', fontStyle: 'italic' }}>No activity logged yet.</p>
                ) : (
                  logs.map(log => (
                    <div key={log.id} style={{ padding: '12px 16px', background: 'var(--gray-50)', borderRadius: '12px', borderLeft: '4px solid var(--brand-500)' }}>
                      <p style={{ margin: 0, fontSize: '14px', color: 'var(--gray-800)' }}>{log.log}</p>
                      <span style={{ fontSize: '11px', color: 'var(--gray-400)' }}>{new Date(log.created_at).toLocaleString()}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
