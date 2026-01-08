import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Typography,
  Badge,
  Button,
  Grid,
  Breadcrumb,
  Space,
  Switch,
  Tooltip,
  Drawer,
  Spin,
} from 'antd';
import {
  UserOutlined,
  DashboardOutlined,
  TeamOutlined,
  SafetyOutlined,
  SettingOutlined,
  LogoutOutlined,
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  CarOutlined,
  IdcardOutlined,
  ScheduleOutlined,
  HomeOutlined,
  AppstoreOutlined,
  ToolOutlined,
  LockOutlined,
  SunOutlined,
  MoonOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { usePermissions } from '../context/PermissionContext';
import './DashboardLayout.css';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

/**
 * Menu items with permission requirements
 * Each item can have:
 * - permission: single permission code required
 * - permissions: array of permission codes (user needs ANY of them)
 * - requireAll: if true with permissions array, user needs ALL
 */
const ALL_MENU_ITEMS = [
  {
    key: '/dashboard',
    icon: <HomeOutlined />,
    label: 'Dashboard',
    permission: null, // Always visible
  },
  // Admin Section
  {
    key: '/dashboard/users',
    icon: <TeamOutlined />,
    label: 'Users',
    permission: 'can_view_admin_users',
  },
  {
    key: '/dashboard/roles',
    icon: <SafetyOutlined />,
    label: 'Roles',
    permission: 'can_view_admin_roles',
  },
  {
    key: '/dashboard/permissions',
    icon: <LockOutlined />,
    label: 'Permissions',
    permission: 'can_view_admin_permissions',
  },
  {
    key: '/dashboard/stations',
    icon: <AppstoreOutlined />,
    label: 'Stations',
    permission: 'can_view_admin_stations',
  },
  // EIC Section
  {
    key: '/dashboard/logistics',
    icon: <DashboardOutlined />,
    label: 'Logistics',
    permission: 'can_view_eic_network_dashboard',
  },
  {
    key: '/dashboard/eic-approvals',
    icon: <SafetyOutlined />,
    label: 'Shift Approvals',
    permission: 'can_view_eic_driver_approvals',
  },
  // Transport Section
  {
    key: '/dashboard/transport-logistics',
    icon: <DashboardOutlined />,
    label: 'Trips',
    permission: 'can_view_transport_logistics',
  },
  {
    key: '/dashboard/vehicles',
    icon: <CarOutlined />,
    label: 'Vehicles',
    permission: 'can_view_transport_vehicles',
  },
  {
    key: '/dashboard/drivers',
    icon: <IdcardOutlined />,
    label: 'Drivers',
    permission: 'can_view_transport_drivers',
  },
  //   key: '/dashboard/shifts',
  //   icon: <ScheduleOutlined />,
  //   label: 'Shifts',
  //   permission: 'can_view_transport_timesheet',
  // },
  {
    key: '/dashboard/timesheet',
    icon: <ScheduleOutlined />,
    label: 'Shift Timeline',
    permission: 'can_view_transport_timesheet',
  },
];

const DashboardLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerVisible, setMobileDrawerVisible] = useState(false);
  const { user, logout } = useAuth();
  const { theme, isDark, toggleTheme } = useTheme();
  const { hasPermission, loading: permissionsLoading } = usePermissions();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = useBreakpoint();

  // Determine if we're on mobile/tablet
  const isMobile = !screens.lg;

  // Close mobile drawer when navigating
  useEffect(() => {
    if (isMobile) {
      setMobileDrawerVisible(false);
    }
  }, [location.pathname, isMobile]);

  // Auto collapse on mobile
  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
    }
  }, [isMobile]);

  // Get dynamic page title based on permissions
  const getPageTitle = useCallback(() => {
    if (hasPermission('can_view_admin_permissions')) {
      return 'Admin Dashboard | GTS';
    }
    if (hasPermission('can_view_eic_network_dashboard')) {
      return 'EIC Dashboard | GTS';
    }
    if (hasPermission('can_view_transport_logistics')) {
      return 'Transport Dashboard | GTS';
    }
    if (hasPermission('can_view_ms_dashboard')) {
      return 'MS Operator | GTS';
    }
    if (hasPermission('can_view_dbs_dashboard')) {
      return 'DBS Operator | GTS';
    }
    if (hasPermission('can_view_customer_dashboard')) {
      return 'Customer Portal | GTS';
    }
    if (hasPermission('can_view_driver_dashboard')) {
      return 'Driver Portal | GTS';
    }
    return 'GTS Dashboard';
  }, [hasPermission]);

  // Update browser tab title dynamically based on permissions
  useEffect(() => {
    if (!permissionsLoading) {
      document.title = getPageTitle();
    }
  }, [permissionsLoading, getPageTitle]);

  const roleCode = (user?.role || '').toUpperCase();

  // Get sidebar title based on user's permissions (not hardcoded role)
  const getSidebarTitle = useCallback(() => {
    if (collapsed) return 'GTS';

    // Priority-based title from permissions
    if (hasPermission('can_view_admin_permissions')) {
      return 'Admin Dashboard';
    }
    if (hasPermission('can_view_eic_network_dashboard')) {
      return 'EIC Dashboard';
    }
    if (hasPermission('can_view_transport_logistics')) {
      return 'Transport Dashboard';
    }
    if (hasPermission('can_view_ms_dashboard')) {
      return 'MS Operator';
    }
    if (hasPermission('can_view_dbs_dashboard')) {
      return 'DBS Operator';
    }
    if (hasPermission('can_view_customer_dashboard')) {
      return 'Customer Portal';
    }
    if (hasPermission('can_view_driver_dashboard')) {
      return 'Driver Portal';
    }
    return 'GTS Dashboard';
  }, [collapsed, hasPermission]);

  // Filter menu items based on user permissions
  const menuItems = useMemo(() => {
    return ALL_MENU_ITEMS.filter((item) => {
      // No permission required - always visible
      if (!item.permission) return true;

      // Check if user has the required permission
      return hasPermission(item.permission);
    });
  }, [hasPermission]);

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Profile',
      onClick: () => navigate('/dashboard/profile'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Logout',
      danger: true,
      onClick: logout,
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
    // Close mobile drawer when menu item is clicked
    if (isMobile) {
      setMobileDrawerVisible(false);
    }
  };

  // Toggle sidebar/drawer based on device
  const toggleSidebar = useCallback(() => {
    if (isMobile) {
      setMobileDrawerVisible(!mobileDrawerVisible);
    } else {
      setCollapsed(!collapsed);
    }
  }, [isMobile, mobileDrawerVisible, collapsed]);

  // Breadcrumb generator - memoized to prevent unnecessary recalculations
  const getBreadcrumbs = useMemo(() => {
    const pathSnippets = location.pathname.split('/').filter(i => i);
    const breadcrumbItems = [
      {
        title: <><HomeOutlined /> <span>Home</span></>,
        href: '/dashboard',
      }
    ];

    const routeMap = {
      'users': 'User Management',
      'roles': 'Role Management',
      'permissions': 'Permission Management',
      'stations': 'Station Management',
      'logistics': 'Logistics Overview',
      'eic-approvals': 'Shift Approvals',
      'timesheet': 'Timesheet Management',
      'transport-logistics': 'My Trips',
      'vehicles': 'Vehicle Management',
      'drivers': 'Driver Management',
      'shifts': 'Shift Management',
      'profile': 'Profile',
      'dashboard': 'Dashboard',
    };

    pathSnippets.forEach((snippet, index) => {
      if (snippet !== 'dashboard' && routeMap[snippet]) {
        breadcrumbItems.push({
          title: routeMap[snippet],
        });
      }
    });

    return breadcrumbItems;
  }, [location.pathname]);

  // Sidebar content component (reused in both Sider and Drawer)
  const SidebarContent = () => (
    <>
      <div className="logo" style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: theme.sider.background,
        borderBottom: theme.sider.borderRight
      }}>
        <Typography.Title level={4} style={{ color: theme.sider.textColor, margin: 0, fontWeight: 700, letterSpacing: '-0.5px' }}>
          {getSidebarTitle()}
        </Typography.Title>
      </div>

      {permissionsLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
          <Spin size="small" />
        </div>
      ) : (
        <Menu
          theme={isDark ? 'dark' : 'light'}
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{
            background: theme.sider.background,
            borderRight: 'none',
            padding: '16px 8px',
          }}
        />
      )}
    </>
  );

  return (
    <Layout style={{ minHeight: '100vh', background: theme.token.colorBgLayout }}>
      {/* Desktop Sidebar */}
      {!isMobile && (
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          theme={isDark ? 'dark' : 'light'}
          width={260}
          collapsedWidth={80}
          style={{
            overflowY: 'auto',
            overflowX: 'hidden',
            height: '100vh',
            position: 'fixed',
            left: 0,
            top: 0,
            bottom: 0,
            zIndex: 1000,
            background: theme.sider.background,
            borderRight: theme.sider.borderRight,
          }}
          className="custom-sider"
        >
          <SidebarContent />
        </Sider>
      )}

      {/* Mobile Drawer */}
      {isMobile && (
        <Drawer
          placement="left"
          closable={false}
          onClose={() => setMobileDrawerVisible(false)}
          open={mobileDrawerVisible}
          width={280}
          bodyStyle={{
            padding: 0,
            background: theme.sider.background
          }}
          headerStyle={{ display: 'none' }}
          className="mobile-sidebar-drawer"
        >
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '12px 16px',
            borderBottom: theme.sider.borderRight
          }}>
            <Typography.Title level={4} style={{ color: theme.sider.textColor, margin: 0, fontWeight: 700 }}>
              {getSidebarTitle()}
            </Typography.Title>
            <Button
              type="text"
              icon={<CloseOutlined />}
              onClick={() => setMobileDrawerVisible(false)}
              style={{ color: theme.sider.textColor }}
            />
          </div>
          {permissionsLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 0' }}>
              <Spin size="small" />
            </div>
          ) : (
            <Menu
              theme={isDark ? 'dark' : 'light'}
              mode="inline"
              selectedKeys={[location.pathname]}
              items={menuItems}
              onClick={handleMenuClick}
              style={{
                background: theme.sider.background,
                borderRight: 'none',
                padding: '8px',
              }}
            />
          )}
        </Drawer>
      )}

      <Layout style={{
        marginLeft: isMobile ? 0 : (collapsed ? 80 : 260),
        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
        background: theme.token.colorBgLayout,
        minHeight: '100vh'
      }}>
        <Header
          className="dashboard-header"
          style={{
            background: theme.header.background,
            backdropFilter: theme.header.backdropFilter,
            WebkitBackdropFilter: theme.header.backdropFilter,
            boxShadow: theme.header.boxShadow,
            borderBottom: 'none',
            position: 'sticky',
            top: 0,
            zIndex: 999,
          }}
        >
          <div className="header-left">
            <Button
              type="text"
              icon={isMobile ? <MenuUnfoldOutlined /> : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)}
              onClick={toggleSidebar}
              style={{
                fontSize: '18px',
                width: 48,
                height: 48,
                color: theme.header.textColor,
              }}
            />
          </div>

          <div className="header-right">
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow={{ pointAtCenter: true }}>
              <div className="user-profile" role="button" style={{
                padding: '4px 8px',
                borderRadius: user ? 50 : 8,
                background: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)',
                border: `1px solid ${isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'}`,
                transition: 'all 0.2s',
              }}>
                <Avatar
                  style={{
                    backgroundColor: theme.token.colorPrimary,
                    verticalAlign: 'middle'
                  }}
                  icon={<UserOutlined />}
                />
                {!collapsed && (
                  <div className="user-info" style={{ marginLeft: 12 }}>
                    <span className="user-name" style={{
                      color: theme.header.textColor,
                      fontWeight: 600,
                      fontSize: '14px'
                    }}>
                      {user?.full_name || user?.name || 'User'}
                    </span>
                    <span className="user-email" style={{
                      color: theme.token.colorTextSecondary,
                      fontSize: '12px'
                    }}>
                      {user?.email || roleCode || 'user@example.com'}
                    </span>
                  </div>
                )}
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content className="dashboard-content" style={{
          background: theme.token.colorBgLayout,
          padding: '24px',
          overflow: 'initial'
        }}>
          {/* Breadcrumb Section */}
          {location.pathname !== '/dashboard' && (
            <div style={{
              background: 'transparent',
              padding: '0 0 16px 4px',
              marginBottom: 0,
            }}>
              <Breadcrumb items={getBreadcrumbs} />
            </div>
          )}

          <div className="content-wrapper" style={{
            maxWidth: 1600,
            margin: '0 auto',
          }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default DashboardLayout;
