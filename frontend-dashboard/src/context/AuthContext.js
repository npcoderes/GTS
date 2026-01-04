import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/api';
import { message } from 'antd';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check if user is logged in on mount
    const token = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      const { token, user: userData, reset_required } = response.data;
      
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(userData));
      
      setUser(userData);
      setIsAuthenticated(true);
      
      // Check if password reset or MPIN setup is required
      if (reset_required || !userData.mpin_set) {
        return { success: true, reset_required, mpin_required: !userData.mpin_set };
      }
      
      message.success('Login successful!');
      return { success: true };
    } catch (error) {
      console.error('Login error:', error);
      message.error(error.response?.data?.message || 'Login failed. Please check your credentials.');
      return { success: false };
    }
  };

  const logout = () => {
    try {
      authAPI.logout().catch(() => {}); // Fire and forget
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setUser(null);
      setIsAuthenticated(false);
      message.info('Logged out successfully');
    }
  };

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
