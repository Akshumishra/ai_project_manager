import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import api, { setAccessToken } from '../../../shared/api/api';
import { API } from '../../../shared/config/config';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setAccessToken(null);
    localStorage.removeItem('refresh_token');
    setUser(null);
    setIsAuthenticated(false);
  }, []);

  const login = async (email, password) => {
    const { data } = await api.post('/api/users/login', { email, password });
    setAccessToken(data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setIsAuthenticated(true);
    setUser({ email, name: data.name, is_profile_complete: data.is_profile_complete }); 
    return data;
  };

  const register = async (name, email, password) => {
    await api.post('/api/users/register', { name, email, password });
    return login(email, password);
  };

  useEffect(() => {
    const initAuth = async () => {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API}/api/users/refresh`, { refresh_token: refreshToken });
          setAccessToken(data.access_token);
          localStorage.setItem('refresh_token', data.refresh_token);
          setIsAuthenticated(true);
          setUser({ name: data.name, is_profile_complete: data.is_profile_complete }); 
        } catch {
          logout();
        }
      }
      setLoading(false);
    };

    initAuth();
  }, [logout]);

  return (
    <AuthContext.Provider value={{ user, setUser, isAuthenticated, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
