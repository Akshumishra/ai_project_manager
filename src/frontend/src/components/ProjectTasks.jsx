import React from 'react';

export default function ProjectTasks({ tasks, onCreateTask, onEditTask }) {
  return (
    <div className="tasks-panel">
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '24px', gap: '12px' }}>
        <button
          className="btn btn-secondary"
          onClick={() => alert('Task Assigner AI Agent is coming soon!')}
          style={{ display: 'flex', alignItems: 'center' }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          Assign Task (AI)
        </button>
        <button className="btn btn-primary" onClick={onCreateTask}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: '8px' }}>
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Task
        </button>
      </div>
      {tasks.length === 0 ? (
        <div className="no-docs">
          <p>No tasks for this project yet. Use "Add Task" to create one.</p>
        </div>
      ) : (
        <div className="task-list">
          {tasks.map(task => (
            <div key={task.id} className="task-card">
              <div className="task-header" style={{ position: 'relative' }}>
                <div style={{ paddingRight: '40px' }}>
                  <h3>{task.title}</h3>
                </div>
                <div style={{ position: 'absolute', top: 0, right: 0, display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button
                    className="btn-action-doc"
                    onClick={(e) => onEditTask(e, task)}
                    title="Edit Task"
                    style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: '4px' }}
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                    </svg>
                  </button>
                  <span className={`task-status status-${task.status.toLowerCase()}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </div>
              <p className="task-description">{task.description}</p>
              <div className="task-meta">
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                  {task.deadline && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                      {new Date(task.deadline).toLocaleDateString()}
                    </span>
                  )}
                  {task.complexity && (
                    <span className={`badge-complexity ${task.complexity.toLowerCase()}`} style={{
                      padding: '2px 8px',
                      borderRadius: '12px',
                      fontSize: '10px',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      backgroundColor: task.complexity.toLowerCase() === 'critical' ? '#fee2e2' :
                        task.complexity.toLowerCase() === 'high' ? '#ffedd5' :
                          task.complexity.toLowerCase() === 'medium' ? '#f0f9ff' : '#f0fdf4',
                      color: task.complexity.toLowerCase() === 'critical' ? '#991b1b' :
                        task.complexity.toLowerCase() === 'high' ? '#9a3412' :
                          task.complexity.toLowerCase() === 'medium' ? '#075985' : '#166534',
                    }}>
                      {task.complexity}
                    </span>
                  )}
                </div>
                {task.assignee_name && (
                  <div className="task-assignee" style={{
                    marginTop: '12px',
                    paddingTop: '12px',
                    borderTop: '1px solid var(--gray-100)',
                    display: 'flex',
                    alignItems: 'center',
                    fontSize: '12px',
                    color: 'var(--gray-600)'
                  }}>
                    <div style={{
                      width: '24px',
                      height: '24px',
                      borderRadius: '50%',
                      background: 'var(--brand-600)',
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      marginRight: '8px',
                      fontSize: '10px',
                      fontWeight: 'bold'
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
