import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Login({ onToggle }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login } = useAuth();
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 401) {
        setError('Invalid email or password. If you were invited to a project, please Register your account first!');
      } else if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg).join(', '));
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Login failed');
      }
    }
  };


  return (
    <div className="auth-container">
      <form className="auth-form" onSubmit={handleSubmit}>
        <h2>Login</h2>
        {error && <div className="error-banner">{error}</div>}
        <input 
          type="email" 
          placeholder="Email" 
          value={email} 
          onChange={(e) => setEmail(e.target.value)} 
          required 
        />
        <input 
          type="password" 
          placeholder="Password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
        />
        <button type="submit">Login</button>
        <p>
          Don't have an account? <button type="button" onClick={onToggle}>Register</button>
        </p>
      </form>
    </div>
  );
}
