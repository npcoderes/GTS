import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Role-based route protection component
 * Redirects to dashboard if user doesn't have required role
 */
const RoleProtectedRoute = ({ children, allowedRoles }) => {
  const { user } = useAuth();
  const roleCode = (user?.role || '').toUpperCase();

  // Check if user's role is in the allowed roles
  const hasAccess = allowedRoles.some(role => {
    const normalizedRole = role.toUpperCase();
    // Handle variations of role names
    if (normalizedRole === 'VENDOR') {
      return roleCode === 'VENDOR' || roleCode === 'SGL_TRANSPORT_VENDOR';
    }
    return roleCode === normalizedRole;
  });

  if (!hasAccess) {
    // Redirect to dashboard with a message
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

export default RoleProtectedRoute;
