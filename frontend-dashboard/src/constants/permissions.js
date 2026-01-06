/**
 * Permission Constants for GTS Dashboard
 * Organized by platform and category for easy management
 */

// Platform types
export const PLATFORMS = {
    ALL: 'all',
    MOBILE: 'mobile',
    DASHBOARD: 'dashboard',
};

// =============================================
// ACTION PERMISSIONS (shared across platforms)
// =============================================
export const ACTION_PERMISSIONS = {
    SUBMIT_MANUAL_REQUEST: 'can_submit_manual_request',
    APPROVE_REQUEST: 'can_approve_request',
    MANAGE_DRIVERS: 'can_manage_drivers',
    OVERRIDE_TOKENS: 'can_override_tokens',
    MANAGE_CLUSTERS: 'can_manage_clusters',
    TRIGGER_CORRECTION_ACTIONS: 'can_trigger_correction_actions',
    APPROVE_SHIFT: 'can_approve_shift',
    REJECT_SHIFT: 'can_reject_shift',
};

// =============================================
// DASHBOARD SCREEN PERMISSIONS (Web Only)
// =============================================
export const DASHBOARD_SCREEN_PERMISSIONS = {
    // Admin screens
    VIEW_ADMIN_USERS: 'can_view_admin_users',
    VIEW_ADMIN_ROLES: 'can_view_admin_roles',
    VIEW_ADMIN_PERMISSIONS: 'can_view_admin_permissions',
    VIEW_ADMIN_STATIONS: 'can_view_admin_stations',
    
    // EIC screens
    VIEW_EIC_NETWORK_DASHBOARD: 'can_view_eic_network_dashboard',
    VIEW_EIC_DRIVER_APPROVALS: 'can_view_eic_driver_approvals',
    VIEW_EIC_ALERTS: 'can_view_eic_alerts',
    VIEW_EIC_INCOMING_STOCK_REQUESTS: 'can_view_eic_incoming_stock_requests',
    VIEW_EIC_STOCK_TRANSFERS: 'can_view_eic_stock_transfers',
    VIEW_EIC_CLUSTER_MANAGEMENT: 'can_view_eic_cluster_management',
    VIEW_EIC_RECONCILIATION: 'can_view_eic_reconciliation',
    VIEW_EIC_VEHICLE_TRACKING: 'can_view_eic_vehicle_tracking',
    VIEW_EIC_VEHICLE_QUEUE: 'can_view_eic_vehicle_queue',
    VIEW_EIC_MANUAL_TOKEN_ASSIGNMENT: 'can_view_eic_manual_token_assignment',
    
    // Transport screens
    VIEW_TRANSPORT_LOGISTICS: 'can_view_transport_logistics',
    VIEW_TRANSPORT_VEHICLES: 'can_view_transport_vehicles',
    VIEW_TRANSPORT_DRIVERS: 'can_view_transport_drivers',
    VIEW_TRANSPORT_TIMESHEET: 'can_view_transport_timesheet',
    
    // Settings
    VIEW_SETTINGS: 'can_view_settings',
};

// =============================================
// MOBILE SCREEN PERMISSIONS (Mobile App Only)
// =============================================
export const MOBILE_SCREEN_PERMISSIONS = {
    // MS screens
    VIEW_MS_DASHBOARD: 'can_view_ms_dashboard',
    VIEW_MS_OPERATIONS: 'can_view_ms_operations',
    VIEW_MS_STOCK_TRANSFERS: 'can_view_ms_stock_transfers',
    
    // DBS screens
    VIEW_DBS_DASHBOARD: 'can_view_dbs_dashboard',
    VIEW_DBS_DECANTING: 'can_view_dbs_decanting',
    VIEW_DBS_MANUAL_REQUEST: 'can_view_dbs_manual_request',
    VIEW_DBS_REQUEST_STATUS: 'can_view_dbs_request_status',
    VIEW_DBS_STOCK_TRANSFERS: 'can_view_dbs_stock_transfers',
    
    // Customer screens
    VIEW_CUSTOMER_DASHBOARD: 'can_view_customer_dashboard',
    VIEW_CUSTOMER_CURRENT_STOCKS: 'can_view_customer_current_stocks',
    VIEW_CUSTOMER_TRANSPORT_TRACKING: 'can_view_customer_transport_tracking',
    VIEW_CUSTOMER_TRIP_ACCEPTANCE: 'can_view_customer_trip_acceptance',
    VIEW_CUSTOMER_STOCK_TRANSFERS: 'can_view_customer_stock_transfers',
    
    // Driver screens
    VIEW_DRIVER_DASHBOARD: 'can_view_driver_dashboard',
    VIEW_DRIVER_TRIPS: 'can_view_driver_trips',
    VIEW_DRIVER_EMERGENCY: 'can_view_driver_emergency',
    
    // Settings
    VIEW_SETTINGS: 'can_view_settings',
};

// =============================================
// MENU PERMISSIONS - Maps menu items to required permissions
// =============================================
export const MENU_PERMISSIONS = {
    // Admin menu items
    '/users': DASHBOARD_SCREEN_PERMISSIONS.VIEW_ADMIN_USERS,
    '/roles': DASHBOARD_SCREEN_PERMISSIONS.VIEW_ADMIN_ROLES,
    '/permissions': DASHBOARD_SCREEN_PERMISSIONS.VIEW_ADMIN_PERMISSIONS,
    '/stations': DASHBOARD_SCREEN_PERMISSIONS.VIEW_ADMIN_STATIONS,
    
    // EIC menu items
    '/eic/overview': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_NETWORK_DASHBOARD,
    '/eic/driver-approvals': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_DRIVER_APPROVALS,
    '/eic/alerts': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_ALERTS,
    '/eic/stock-requests': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_INCOMING_STOCK_REQUESTS,
    '/eic/stock-transfers': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_STOCK_TRANSFERS,
    '/eic/clusters': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_CLUSTER_MANAGEMENT,
    '/eic/reconciliation': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_RECONCILIATION,
    '/eic/vehicle-tracking': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_VEHICLE_TRACKING,
    '/eic/vehicle-queue': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_VEHICLE_QUEUE,
    '/eic/manual-tokens': DASHBOARD_SCREEN_PERMISSIONS.VIEW_EIC_MANUAL_TOKEN_ASSIGNMENT,
    
    // Transport menu items
    '/transport/logistics': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_LOGISTICS,
    '/transport/vehicles': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_VEHICLES,
    '/transport/drivers': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_DRIVERS,
    '/transport/timesheet': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_TIMESHEET,
    '/shifts': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_TIMESHEET,
    '/vehicles': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_VEHICLES,
    '/drivers': DASHBOARD_SCREEN_PERMISSIONS.VIEW_TRANSPORT_DRIVERS,
    
    // Settings
    '/settings': DASHBOARD_SCREEN_PERMISSIONS.VIEW_SETTINGS,
};

// =============================================
// ALL PERMISSIONS - Combined for easy reference
// =============================================
export const ALL_PERMISSIONS = {
    ...ACTION_PERMISSIONS,
    ...DASHBOARD_SCREEN_PERMISSIONS,
    ...MOBILE_SCREEN_PERMISSIONS,
};

/**
 * Check if user has a specific permission
 * @param {Object} permissions - User's permissions object
 * @param {string} permissionCode - Permission code to check
 * @returns {boolean}
 */
export const hasPermission = (permissions, permissionCode) => {
    if (!permissions || !permissionCode) return false;
    return permissions[permissionCode] === true;
};

/**
 * Check if user has any of the specified permissions
 * @param {Object} permissions - User's permissions object
 * @param {string[]} permissionCodes - Array of permission codes
 * @returns {boolean}
 */
export const hasAnyPermission = (permissions, permissionCodes) => {
    if (!permissions || !permissionCodes || !permissionCodes.length) return false;
    return permissionCodes.some(code => permissions[code] === true);
};

/**
 * Check if user has all of the specified permissions
 * @param {Object} permissions - User's permissions object
 * @param {string[]} permissionCodes - Array of permission codes
 * @returns {boolean}
 */
export const hasAllPermissions = (permissions, permissionCodes) => {
    if (!permissions || !permissionCodes || !permissionCodes.length) return false;
    return permissionCodes.every(code => permissions[code] === true);
};

export default {
    PLATFORMS,
    ACTION_PERMISSIONS,
    DASHBOARD_SCREEN_PERMISSIONS,
    MOBILE_SCREEN_PERMISSIONS,
    MENU_PERMISSIONS,
    ALL_PERMISSIONS,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
};
