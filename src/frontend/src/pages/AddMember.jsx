import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function AddMember() {
  const { projectId } = useParams();
  const navigate = useNavigate();

  return (
    <div className="agent-page completion-page">
      <div className="completion-card">
        <h2>🎉 Project Setup Complete!</h2>
        <p>Your project and technical documentation have been successfully created.</p>
        <div className="completion-actions">
          <button className="btn btn-primary" onClick={() => navigate(`/project/${projectId}`)}>
            Go to Project Dashboard
          </button>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            Back to All Projects
          </button>
        </div>
      </div>
    </div>
  );
}
