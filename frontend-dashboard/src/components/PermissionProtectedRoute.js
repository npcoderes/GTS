import React from 'react';
import { Navigate } from 'react-router-dom';
import { Spin, Result, Button } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { usePermissions } from '../context/PermissionContext';

/**
 * Permission-based route protection component
 * 
 * Usage:
 * <PermissionProtectedRoute requiredPermission="can_view_admin_users">
 *   <UserManagement />
 * </PermissionProtectedRoute>
 * 
 * Or with multiple permissions (ANY):
 * <PermissionProtectedRoute requiredPermissions={["can_view_users", "can_manage_users"]}>
 *   <UserManagement />
 * </PermissionProtectedRoute>
 * 
 * Or require ALL permissions:
 * <PermissionProtectedRoute requiredPermissions={["can_view", "can_edit"]} requireAll={true}>
 *   <Component />
 * </PermissionProtectedRoute>
 */
const PermissionProtectedRoute = ({
    children,
    requiredPermission,     // Single permission code (string)
    requiredPermissions,    // Array of permission codes
    requireAll = false,     // If true with requiredPermissions, user needs ALL
    fallback = null,        // Custom fallback component, or null for redirect
    showAccessDenied = true, // Show access denied page instead of redirect
}) => {
    const { hasPermission, hasAnyPermission, hasAllPermissions, loading } = usePermissions();

    // Show loading spinner while fetching permissions
    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%',
                minHeight: '400px'
            }}>
                <Spin size="large" tip="Loading permissions..." />
            </div>
        );
    }

    // Determine access
    let hasAccess = true;

    if (requiredPermission) {
        hasAccess = hasPermission(requiredPermission);
    } else if (requiredPermissions && requiredPermissions.length > 0) {
        hasAccess = requireAll
            ? hasAllPermissions(requiredPermissions)
            : hasAnyPermission(requiredPermissions);
    }

    // Handle no access
    if (!hasAccess) {
        // Custom fallback provided
        if (fallback) {
            return fallback;
        }

        // Show access denied page
        if (showAccessDenied) {
            return (
                <Result
                    status="403"
                    icon={<LockOutlined style={{ color: '#ff4d4f' }} />}
                    title="Access Denied"
                    subTitle="You don't have permission to access this page. Please contact your administrator if you believe this is an error."
                    extra={
                        <Button type="primary" onClick={() => window.history.back()}>
                            Go Back
                        </Button>
                    }
                    style={{ marginTop: '50px' }}
                />
            );
        }

        // Redirect to dashboard
        return <Navigate to="/dashboard" replace />;
    }

    return children;
};

/**
 * Higher-order component version for wrapping components
 */
export const withPermission = (Component, requiredPermission, options = {}) => {
    return function PermissionWrapped(props) {
        return (
            <PermissionProtectedRoute
                requiredPermission={requiredPermission}
                {...options}
            >
                <Component {...props} />
            </PermissionProtectedRoute>
        );
    };
};

export default PermissionProtectedRoute;
