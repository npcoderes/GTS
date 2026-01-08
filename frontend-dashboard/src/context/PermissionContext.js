import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import { permissionsAPI } from '../services/api';
import { useAuth } from './AuthContext';

const PermissionContext = createContext(null);

/**
 * Permission Provider - Central store for user permissions
 * 
 * Fetches permissions from backend on login and provides:
 * - hasPermission(code) - Check single permission
 * - hasAnyPermission([codes]) - Check if user has ANY of the permissions
 * - hasAllPermissions([codes]) - Check if user has ALL permissions
 * - refreshPermissions() - Re-fetch permissions from backend
 */
export const PermissionProvider = ({ children }) => {
    const { user, isAuthenticated } = useAuth();
    const [permissions, setPermissions] = useState({});
    const [permissionList, setPermissionList] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch permissions when user logs in
    const fetchPermissions = useCallback(async () => {
        if (!isAuthenticated || !user) {
            setPermissions({});
            setPermissionList([]);
            setLoading(false);
            return;
        }

        try {
            setLoading(true);
            const response = await permissionsAPI.getUserPermissions();

            // Backend returns { permissions: { can_view_admin_users: true, ... }, details: [...] }
            // or just { can_view_admin_users: true, ... }
            const data = response.data;

            if (data.permissions) {
                setPermissions(data.permissions);
                setPermissionList(data.details || []);
            } else {
                // Flat format
                setPermissions(data);
                setPermissionList([]);
            }

            setError(null);
        } catch (err) {
            console.error('Failed to fetch permissions:', err);
            setError(err);
            setPermissions({});
            setPermissionList([]);
        } finally {
            setLoading(false);
        }
    }, [isAuthenticated, user]);

    useEffect(() => {
        fetchPermissions();
    }, [fetchPermissions]);

    // Check if user has specific permission
    const hasPermission = useCallback((permissionCode) => {
        if (!permissionCode) return true; // No permission required = allow
        return permissions[permissionCode] === true;
    }, [permissions]);

    // Check if user has ANY of the permissions
    const hasAnyPermission = useCallback((permissionCodes) => {
        if (!permissionCodes || permissionCodes.length === 0) return true;
        return permissionCodes.some(code => permissions[code] === true);
    }, [permissions]);

    // Check if user has ALL of the permissions
    const hasAllPermissions = useCallback((permissionCodes) => {
        if (!permissionCodes || permissionCodes.length === 0) return true;
        return permissionCodes.every(code => permissions[code] === true);
    }, [permissions]);

    // Get all granted permission codes
    const getGrantedPermissions = useCallback(() => {
        return Object.entries(permissions)
            .filter(([, granted]) => granted === true)
            .map(([code]) => code);
    }, [permissions]);

    const value = {
        permissions,
        permissionList,
        loading,
        error,
        hasPermission,
        hasAnyPermission,
        hasAllPermissions,
        getGrantedPermissions,
        refreshPermissions: fetchPermissions,
    };

    return (
        <PermissionContext.Provider value={value}>
            {children}
        </PermissionContext.Provider>
    );
};

/**
 * Hook to use permission context
 */
export const usePermissions = () => {
    const context = useContext(PermissionContext);
    if (!context) {
        throw new Error('usePermissions must be used within a PermissionProvider');
    }
    return context;
};

/**
 * Convenience hook to check single permission
 */
export const useHasPermission = (permissionCode) => {
    const { hasPermission } = usePermissions();
    return hasPermission(permissionCode);
};

export default PermissionContext;
