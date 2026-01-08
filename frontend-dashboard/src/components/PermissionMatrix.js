import React, { useMemo } from 'react';
import { Switch, Tag, Tooltip, Typography, Spin } from 'antd';
import {
    DesktopOutlined,
    MobileOutlined,
    GlobalOutlined,
} from '@ant-design/icons';
import './PermissionMatrix.css';

const { Text } = Typography;

/**
 * Platform icons and labels
 */
const PLATFORM_CONFIG = {
    all: { icon: <GlobalOutlined />, label: 'All' },
    mobile: { icon: <MobileOutlined />, label: 'Mobile' },
    dashboard: { icon: <DesktopOutlined />, label: 'Dashboard' },
};

/**
 * Permission Matrix - Visual grid for managing role permissions
 */
const PermissionMatrix = ({
    roles = [],
    permissions = [],
    rolePermissions = [],
    onUpdate,
    loading = false
}) => {
    // Create a lookup map for quick permission checking
    const permissionMap = useMemo(() => {
        const map = {};
        rolePermissions.forEach(rp => {
            const key = `${rp.role}-${rp.permission}`;
            map[key] = rp.granted;
        });
        return map;
    }, [rolePermissions]);

    // Check if a permission is granted to a role
    const isGranted = (roleId, permissionId) => {
        const key = `${roleId}-${permissionId}`;
        return permissionMap[key] === true;
    };

    // Handle toggle
    const handleToggle = (roleId, permissionId, checked) => {
        if (onUpdate) {
            onUpdate(roleId, permissionId, checked);
        }
    };

    if (loading) {
        return (
            <div className="permission-matrix-loading">
                <Spin size="large" />
            </div>
        );
    }

    if (roles.length === 0 || permissions.length === 0) {
        return (
            <div className="permission-matrix-empty">
                <Text type="secondary">No data available</Text>
            </div>
        );
    }

    return (
        <div className="permission-matrix">
            <div className="matrix-scroll-container">
                <table className="matrix-table">
                    <thead>
                        <tr>
                            <th className="permission-header sticky-col">Permission</th>
                            {roles.map(role => (
                                <th key={role.id} className="role-header">
                                    <Tooltip title={role.description || role.name}>
                                        <span className="role-name">{role.name}</span>
                                    </Tooltip>
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {permissions.map(permission => (
                            <tr key={permission.id} className="permission-row">
                                <td className="permission-cell sticky-col">
                                    <div className="permission-info">
                                        <div className="permission-name">{permission.name}</div>
                                        <div className="permission-meta">
                                            <code className="permission-code">{permission.code}</code>
                                            <Tooltip title={PLATFORM_CONFIG[permission.platform]?.label || 'All'}>
                                                <span className="platform-badge">
                                                    {PLATFORM_CONFIG[permission.platform]?.icon || PLATFORM_CONFIG.all.icon}
                                                </span>
                                            </Tooltip>
                                        </div>
                                    </div>
                                </td>
                                {roles.map(role => {
                                    const granted = isGranted(role.id, permission.id);
                                    return (
                                        <td key={role.id} className="toggle-cell">
                                            <Switch
                                                checked={granted}
                                                size="small"
                                                onChange={(checked) => handleToggle(role.id, permission.id, checked)}
                                            />
                                        </td>
                                    );
                                })}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default PermissionMatrix;
