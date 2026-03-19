import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createProjectRequest } from "../api";
import { setActiveProject, setUserBackground } from "../utils/storage";
import { useAuth } from "../context/AuthContext";

export default function CreateProjectPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [projectTitle, setProjectTitle] = useState("");
  const [projectDescription, setProjectDescription] = useState("");
  const [background, setBackground] = useState("technical");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!projectTitle.trim() || !projectDescription.trim()) {
      setError("Project title and description are both required.");
      return;
    }

    if (!user?.id) {
      setError("You must be logged in to create a project.");
      return;
    }

    setLoading(true);
    setError("");

    // Store background for agent context
    setUserBackground(user.id, background);

    try {
      const data = await createProjectRequest({
        name: projectTitle.trim(),
        description: projectDescription.trim(),
        background: background,
      });

      setActiveProject(data);
      navigate(`/requirement-agent?project_id=${encodeURIComponent(data.id)}`);
    } catch (err) {
      console.error("Create project failed:", err);
      setError(err.response?.data?.detail || err.message || "Failed to create project. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-form" style={{ maxWidth: '480px' }}>
        <h2>Initialize Project</h2>
        <p style={{ textAlign: 'center', marginBottom: '32px', color: 'var(--gray-500)', fontSize: '15px' }}>
          Define your project goals to start the AI-guided workflow.
        </p>

      <form onSubmit={handleSubmit}>
        <div className="v-stack gap-6">
          {error && <div className="error-banner">{error}</div>}

          <div className="v-stack gap-2">
            <label className="text-sm font-bold" style={{ marginBottom: '4px', display: 'block' }}>Project Name <span className="required-star">*</span></label>
            <input
              type="text"
              className="input"
              value={projectTitle}
              onChange={(e) => setProjectTitle(e.target.value)}
              placeholder="e.g. AI Learning Platform"
              required
              autoFocus
            />
          </div>

          <div className="v-stack gap-2">
            <label className="text-sm font-bold" style={{ marginBottom: '4px', display: 'block' }}>Description <span className="required-star">*</span></label>
            <textarea
              className="input"
              style={{ minHeight: '100px' }}
              value={projectDescription}
              onChange={(e) => setProjectDescription(e.target.value)}
              placeholder="What does this project solve?"
              required
            />
          </div>

          <div className="v-stack gap-2">
            <label className="text-sm font-bold" style={{ marginBottom: '4px', display: 'block' }}>Project Context</label>
            <div className="radio-group" style={{ display: 'flex', gap: '12px' }}>
              <div 
                className={`radio-label ${background === "technical" ? "active" : ""}`}
                onClick={() => setBackground("technical")}
                style={{ flex: 1, padding: '12px', border: '1px solid var(--gray-200)', borderRadius: '12px', cursor: 'pointer', textAlign: 'center' }}
              >
                Technical
              </div>
              <div 
                className={`radio-label ${background === "non_technical" ? "active" : ""}`}
                onClick={() => setBackground("non_technical")}
                style={{ flex: 1, padding: '12px', border: '1px solid var(--gray-200)', borderRadius: '12px', cursor: 'pointer', textAlign: 'center' }}
              >
                Non technical
              </div>
            </div>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', padding: '16px', marginTop: '12px' }}
            disabled={loading}
          >
            {loading ? 'Creating Project...' : 'Create Project'}
          </button>
          <button 
            type="button" 
            className="btn btn-ghost" 
            style={{ width: '100%' }}
            onClick={() => navigate('/')}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  </div>
  );
}
