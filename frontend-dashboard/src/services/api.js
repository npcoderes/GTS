import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://commorant-dixie-sinuously.ngrok-free.dev/api';
const BASE_URL = process.env.REACT_APP_API_URL ? process.env.REACT_APP_API_URL.replace('/api', '') : 'https://commorant-dixie-sinuously.ngrok-free.dev';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {  
    'Content-Type': 'application/json',
    "ngrok-skip-browser-warning": "true",
    
  },  
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    // Don't add token for login request
    if (token && !config.url.includes('/auth/login/')) {
      config.headers.Authorization = `Token ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    if (!response || !response.data) {
      console.warn('Empty response received');
      return { data: [] };
    }
    return response;
  },
  (error) => {
    console.error('API Error:', {
      url: error?.config?.url,
      method: error?.config?.method,
      status: error?.response?.status,
      message: error?.message
    });

    if (error?.response?.status === 401 && error?.response?.data?.detail?.code === 'TOKEN_EXPIRED') {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        alert('Your session has expired. Please login again.');
        window.location.href = '/login';
      }
    }
    else if (error?.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    else if (!error?.response) {
      console.error('Network error - server may be down');
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (credentials) => api.post('/auth/login/', credentials),
  logout: () => api.post('/auth/logout/'),
  getCurrentUser: () => api.get('/auth/me/'),
  changePassword: (data) => api.post('/auth/change-password/', data),
  setMPIN: (data) => api.post('/auth/set-mpin/', data),
};

// Users API
export const usersAPI = {
  getAll: (params) => api.get('/users/', { params }),
  getById: (id) => api.get(`/users/${id}/`),
  create: (data) => api.post('/users/', data),
  update: (id, data) => api.put(`/users/${id}/`, data),
  partialUpdate: (id, data) => api.patch(`/users/${id}/`, data),
  delete: (id) => api.delete(`/users/${id}/`),
};

// Roles API
export const rolesAPI = {
  getAll: (params) => api.get('/roles/', { params }),
  getById: (id) => api.get(`/roles/${id}/`),
  create: (data) => api.post('/roles/', data),
  update: (id, data) => api.put(`/roles/${id}/`, data),
  delete: (id) => api.delete(`/roles/${id}/`),
};

// User Roles API
export const userRolesAPI = {
  getAll: (params) => api.get('/user-roles/', { params }),
  getByUser: (userId, params) => api.get(`/user-roles/`, { params: { user: userId, ...params } }),
  assign: (data) => api.post('/user-roles/', data),
  update: (id, data) => api.put(`/user-roles/${id}/`, data),
  delete: (id) => api.delete(`/user-roles/${id}/`),
};

// Stations API
export const stationsAPI = {
  getAll: (params) => api.get('/stations/', { params }),
  getById: (id) => api.get(`/stations/${id}/`),
};

// Permissions API
export const permissionsAPI = {
  // Get all permission definitions
  getAll: () => api.get('/permissions/'),

  // Get current user's computed permissions
  getUserPermissions: () => api.get('/auth/permissions/'),

  // Get all roles with their permissions
  getRolesWithPermissions: () => api.get('/roles-with-permissions/'),

  // Role permissions
  getRolePermissions: (roleId) => api.get('/role-permissions/', roleId ? { params: { role: roleId } } : {}),
  updateRolePermission: (id, data) => api.patch(`/role-permissions/${id}/`, data),
  createRolePermission: (data) => api.post('/role-permissions/', data),
  bulkUpdateRolePermissions: (data) => api.post('/role-permissions/bulk-update/', data),

  // User permission overrides
  getUserOverrides: (userId) => api.get('/user-permissions/', userId ? { params: { user: userId } } : {}),
  updateUserPermission: (id, data) => api.patch(`/user-permissions/${id}/`, data),
  createUserPermission: (data) => api.post('/user-permissions/', data),
  deleteUserPermission: (id) => api.delete(`/user-permissions/${id}/`),
  bulkUpdateUserPermissions: (data) => api.post('/user-permissions/bulk-update/', data),
};

// Helper function to get full image URL
export const getImageUrl = (path) => {
  if (!path) return null;
  if (typeof path !== 'string') return null;
  if (path.startsWith('http')) return path;
  return `${BASE_URL}${path.startsWith('/') ? path : '/' + path}`;
};

export default api;
