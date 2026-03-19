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
    
    const userData = { 
      id: data.user_id, 
      email, 
      name: data.name, 
      is_profile_complete: data.is_profile_complete 
    };
    
    // Cache user to avoid blocking UI on page reload
    localStorage.setItem('cached_user', JSON.stringify(userData));
    
    setIsAuthenticated(true);
    setUser(userData); 
    return data;
  };

  const register = async (name, email, password) => {
    const res = await api.post('/api/users/register', { name, email, password });
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('cached_user');
    setUser(null);
    setIsAuthenticated(false);
  };

  const isCheckingAuth = React.useRef(false);
  const checkAuth = async () => {
    if (isCheckingAuth.current) return;
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      setLoading(false);
      return;
    }

    // 1. Immediately load user from cache state to unblock UI
    let cachedUserStr = localStorage.getItem('cached_user');
    if (cachedUserStr) {
      try {
        const cachedUser = JSON.parse(cachedUserStr);
        setUser(cachedUser);
        setIsAuthenticated(true);
        setLoading(false); // Unblock rendering immediately!
      } catch (e) {
        cachedUserStr = null; // invalid cache
      }
    }

    isCheckingAuth.current = true;
    try {
      // 2. Perform silent background refresh
      const { data } = await api.post(
        '/api/users/refresh', 
        { refresh_token: refreshToken },
        { timeout: 30000 }
      );
      
      setAccessToken(data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      
      const newUserData = { 
        id: data.user_id, 
        name: data.name, 
        is_profile_complete: data.is_profile_complete,
        email: data.email || (cachedUserStr ? JSON.parse(cachedUserStr).email : null)
      };
      
      localStorage.setItem('cached_user', JSON.stringify(newUserData));
      setUser(newUserData); 
      setIsAuthenticated(true);
      
    } catch (err) {
      console.error('Check auth failed in background:', err.message || err);
      // Only perform a hard logout if the token is explicitly rejected (401 Unauthorized)
      // Otherwise (e.g., timeout or network error), keep the cached session alive
      if (err.response && err.response.status === 401) {
        logout();
      }
    } finally {
      isCheckingAuth.current = false;
      // If there was no cached user, we need to unblock UI now whether it succeeded or failed
      if (!cachedUserStr) {
        setLoading(false);
      }
    }
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
