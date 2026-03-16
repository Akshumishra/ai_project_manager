import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../api';

export default function Register({ onToggle }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('email') || '';
  });
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const { register } = useAuth();
  const [error, setError] = useState('');
  const [step, setStep] = useState(0); // 0: details, 1: otp, 2: password
  const [loading, setLoading] = useState(false);

  const [showPassword, setShowPassword] = useState(false);

  // Removed useEffect email pre-fill to avoid cascading renders

  const handleSendOTP = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/api/users/send-otp', { email });
      setStep(1);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/api/users/verify-otp', { email, otp });
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(name, email, password);
      alert('Registration successful! Please login.');
      onToggle();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg).join(', '));
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Registration failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <form className="auth-form" onSubmit={step === 0 ? handleSendOTP : step === 1 ? handleVerifyOTP : handleSubmit}>
        <h2>Register</h2>
        {error && <div className="error-banner">{error}</div>}
        
        {step === 0 && (
          <>
            <div className="form-group">
              <label>Name <span className="required-star">*</span></label>
              <input 
                type="text" 
                placeholder="Name" 
                value={name} 
                onChange={(e) => setName(e.target.value)} 
                required 
              />
            </div>
            <div className="form-group">
              <label>Email <span className="required-star">*</span></label>
              <input 
                type="email" 
                placeholder="Email" 
                value={email} 
                onChange={(e) => setEmail(e.target.value)} 
                required 
              />
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Sending...' : 'Send OTP'}
            </button>
          </>
        )}

        {step === 1 && (
          <>
            <div className="form-group">
              <label>OTP <span className="required-star">*</span></label>
              <input 
                type="text" 
                placeholder="Enter 6-digit OTP" 
                value={otp} 
                onChange={(e) => setOtp(e.target.value)} 
                required 
                maxLength={6}
              />
              <p className="hint-text">Check your email for the verification code.</p>
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Verifying...' : 'Verify OTP'}
            </button>
            <button type="button" className="btn-link" onClick={() => setStep(0)}>Change Email</button>
          </>
        )}

        {step === 2 && (
          <>
            <div className="form-group">
              <label>Set Password <span className="required-star">*</span></label>
              <div className="password-input-wrapper">
                <input 
                  type={showPassword ? "text" : "password"} 
                  placeholder="Password" 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)} 
                  required 
                />
                <button 
                  type="button" 
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>
                  ) : (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading}>
              {loading ? 'Registering...' : 'Register'}
            </button>
          </>
        )}
        <p>
          Already have an account? <button type="button" onClick={onToggle}>Login</button>
        </p>
      </form>
    </div>
  );
}
