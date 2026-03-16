import { useState } from 'react';
import api from '../../../shared/api/api';
import { useAuth } from '../../auth/context/AuthContext';

export default function ResumeUpload({ onComplete }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [parsedData, setParsedData] = useState(null); 
  const { setUser } = useAuth();

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setError('');
    }
  };

  const handleParse = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post('/api/users/parse-resume', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      setParsedData({
        skills: res.data.skills || [],
        experience_years: res.data.experience_years || '',
        designation: res.data.designation || '',
      });
    } catch (err) {
      console.error('Parsing failed:', err);
      setError(err.response?.data?.detail || 'Failed to parse resume. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');

    try {
      await api.post('/api/users/update-profile', parsedData);
      setUser(prev => ({ ...prev, is_profile_complete: true }));
      if (onComplete) onComplete();
    } catch (err) {
      console.error('Update failed:', err);
      setError(err.response?.data?.detail || 'Failed to update profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const updateParsedField = (field, value) => {
    setParsedData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (parsedData) {
    return (
      <div className="auth-container">
        <div className="auth-form resume-review-form">
          <h2>Review Extracted Data</h2>
          <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
            We've extracted the following details. Please review and edit if necessary.
          </p>

          {error && <div className="error-banner">{error}</div>}

          <form onSubmit={handleSaveProfile}>
            <div className="form-group">
              <label>Designation</label>
              <input 
                type="text" 
                value={parsedData.designation} 
                onChange={(e) => updateParsedField('designation', e.target.value)}
                required 
              />
            </div>

            <div className="form-group">
              <label>Experience (Years)</label>
              <input 
                type="text" 
                value={parsedData.experience_years} 
                onChange={(e) => updateParsedField('experience_years', e.target.value)}
                required 
              />
            </div>

            <div className="form-group">
              <label>Skills (comma separated)</label>
              <textarea 
                value={parsedData.skills.join(', ')} 
                onChange={(e) => updateParsedField('skills', e.target.value.split(',').map(s => s.trim()))}
                rows={4}
                required 
              />
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={() => setParsedData(null)}
                style={{ flex: 1 }}
              >
                Back
              </button>
              <button 
                type="submit" 
                className="btn btn-primary" 
                disabled={saving}
                style={{ flex: 2 }}
              >
                {saving ? 'Saving...' : 'Confirm & Save'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <div className="auth-form resume-upload-form">
        <h2>Complete Your Profile</h2>
        <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
          Please upload your resume (PDF, DOCX, or TXT) to get started with projects.
        </p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleParse}>
          <div className="file-input-wrapper" style={{ marginBottom: '1.5rem' }}>
            <input 
              type="file" 
              accept=".pdf,.docx,.txt" 
              onChange={handleFileChange}
              id="resume-file"
              style={{ display: 'none' }}
            />
            <label 
              htmlFor="resume-file" 
              className="btn btn-secondary" 
              style={{ width: '100%', cursor: 'pointer', padding: '1rem', border: '2px dashed var(--border-color)' }}
            >
              {file ? `Selected: ${file.name}` : 'Click to select Resume'}
            </label>
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%' }}
            disabled={uploading || !file}
          >
            {uploading ? 'Parsing Resume...' : 'Upload & Continue'}
          </button>
        </form>
      </div>
    </div>
  );
}
