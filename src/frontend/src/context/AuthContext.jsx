import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  const setAccessToken = (token) => {
    localStorage.setItem('access_token', token);
  };

  const login = async (email, password) => {
    const { data } = await api.post('/api/users/login', { email, password });
    setAccessToken(data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    setIsAuthenticated(true);
    setUser({ 
      id: data.user_id, 
      email, 
      name: data.name, 
      is_profile_complete: data.is_profile_complete 
    }); 
    return data;
  };

  const register = async (name, email, password) => {
    const res = await api.post('/api/users/register', { name, email, password });
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setUser(null);
    setIsAuthenticated(false);
  };

  const checkAuth = async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        const { data } = await api.post('/api/users/refresh', { refresh_token: refreshToken });
        setAccessToken(data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        setIsAuthenticated(true);
        setUser({ 
          id: data.user_id, 
          name: data.name, 
          is_profile_complete: data.is_profile_complete 
        }); 
      } catch {
        logout();
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, loading, login, logout, register, setUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
