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
import './DashboardLayout.css';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

const DashboardLayout = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileDrawerVisible, setMobileDrawerVisible] = useState(false);
  const { user, logout } = useAuth();
  const { theme, isDark, toggleTheme } = useTheme();
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

  const roleCode = (user?.role || '').toUpperCase();

  // Get sidebar title based on role
  const getSidebarTitle = () => {
    if (roleCode === 'SUPER_ADMIN' || roleCode === 'EIC') {
      return collapsed ? 'GTS' : 'GTS Admin';
    }
    if (roleCode === 'TRANSPORT_ADMIN') {
      return collapsed ? 'GTS' : 'Transport Admin';
    }
    if (roleCode === 'VENDOR' || roleCode === 'SGL_TRANSPORT_VENDOR') {
      return collapsed ? 'GTS' : 'Transport Vendor';
    }
    return collapsed ? 'GTS' : 'GTS Dashboard';
  };

  // Role-based navigation: Transport Vendors see a trimmed menu focused on fleet/driver ops
  const baseMenu = [
    { key: '/dashboard', icon: <HomeOutlined />, label: 'Dashboard' },
    { key: '/dashboard/users', icon: <TeamOutlined />, label: 'Users' },
    { key: '/dashboard/roles', icon: <SafetyOutlined />, label: 'Roles' },
    { key: '/dashboard/permissions', icon: <LockOutlined />, label: 'Permissions' },
    { key: '/dashboard/stations', icon: <AppstoreOutlined />, label: 'Stations' },
    { key: '/dashboard/logistics', icon: <DashboardOutlined />, label: 'Logistics' },
    { key: '/dashboard/transport-logistics', icon: <DashboardOutlined />, label: 'Trips' },
    { key: '/dashboard/vehicles', icon: <CarOutlined />, label: 'Vehicles' },
    { key: '/dashboard/drivers', icon: <IdcardOutlined />, label: 'Drivers' },
    { key: '/dashboard/shifts', icon: <ScheduleOutlined />, label: 'Shifts' },
  ];

  // Define menu access for different roles
  const superAdminAllowed = new Set([
    '/dashboard',
    '/dashboard/users',
    '/dashboard/roles',
    '/dashboard/permissions',
    '/dashboard/stations',
    '/dashboard/logistics',
  ]);

  const transportAdminAllowed = new Set([
    '/dashboard',
    '/dashboard/transport-logistics',
    '/dashboard/vehicles',
    '/dashboard/drivers',
    '/dashboard/shifts',
  ]);

  const vendorAllowed = new Set([
    '/dashboard',
    '/dashboard/transport-logistics',
    '/dashboard/vehicles',
    '/dashboard/drivers',
    '/dashboard/shifts',
  ]);

  const menuItems = useMemo(() => {
    return baseMenu.filter((item) => {
      // SUPER_ADMIN role - admin menu items
      if (roleCode === 'SUPER_ADMIN') {
        return superAdminAllowed.has(item.key);
      }
      // TRANSPORT_ADMIN role - transport menu items
      if (roleCode === 'TRANSPORT_ADMIN') {
        return transportAdminAllowed.has(item.key);
      }
      // VENDOR role - limited menu items
      if (roleCode === 'VENDOR' || roleCode === 'SGL_TRANSPORT_VENDOR') {
        return vendorAllowed.has(item.key);
      }
      return true; // other roles see everything else
    });
  }, [roleCode]);

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
            WebkitBackdropFilter: theme.header.backdropFilter, // Safari support
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
            {/* Theme Toggle */}
            {/* <Tooltip title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}>
              <Button
                type="text"
                icon={isDark ? <SunOutlined /> : <MoonOutlined />}
                onClick={toggleTheme}
                style={{
                  fontSize: 18,
                  width: 40,
                  height: 40,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: isDark ? '#FCD34D' : '#64748B',
                  marginRight: 8,
                }}
              />
            </Tooltip> */}

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
