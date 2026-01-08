import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import { AuthProvider } from './context/AuthContext';
import { PermissionProvider } from './context/PermissionContext';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import ErrorBoundary from './components/ErrorBoundary';
import PrivateRoute from './components/PrivateRoute';
import PermissionProtectedRoute from './components/PermissionProtectedRoute';
import DashboardLayout from './components/DashboardLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import UserManagement from './pages/UserManagement';
import RoleManagement from './pages/RoleManagement';
import StationManagement from './pages/StationManagement';
import LogisticsOverview from './pages/LogisticsOverview';
import TransportAdminLogistics from './pages/TransportAdminLogistics';
import VehicleManagement from './pages/VehicleManagement';
import DriverManagement from './pages/DriverManagement';
import ShiftManagement from './pages/ShiftManagement';
import EICShiftApprovals from './pages/EICShiftApprovals';
import TimesheetManagement from './pages/TimesheetManagement';
import PermissionManagement from './pages/PermissionManagement';
import Profile from './pages/Profile';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import SetupMPIN from './pages/SetupMPIN';
import NotFound from './pages/NotFound';
import './App.css';

// Themed App wrapper
const ThemedApp = () => {
  const { theme, isDark } = useTheme();

  return (
    <ConfigProvider
      theme={{
        algorithm: isDark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm,
        token: {
          colorPrimary: theme.token.colorPrimary,
          colorBgContainer: theme.token.colorBgContainer,
          colorBgLayout: theme.token.colorBgLayout,
          colorText: theme.token.colorText,
          colorTextSecondary: theme.token.colorTextSecondary,
          colorBorder: theme.token.colorBorder,
          borderRadius: theme.token.borderRadius,
          fontFamily: theme.token.fontFamily,
        },
        components: {
          Layout: {
            bodyBg: theme.token.colorBgLayout,
            headerBg: theme.header.background,
            siderBg: theme.sider.background,
          },
          Card: {
            colorBgContainer: theme.card.background,
            boxShadowTertiary: theme.card.boxShadow,
            colorBorderSecondary: theme.card.border,
          },
          Table: {
            colorBgContainer: theme.card.background,
            headerBg: isDark ? 'rgba(255,255,255,0.04)' : '#F8FAFC',
            headerColor: theme.token.colorTextSecondary,
            rowHoverBg: isDark ? 'rgba(255,255,255,0.04)' : '#F1F5F9',
          },
          Menu: {
            itemSelectedColor: theme.sider.selectedColor,
            itemSelectedBg: theme.sider.selectedBg,
            itemColor: theme.sider.textColor,
            darkItemColor: theme.sider.textColor,
            darkItemSelectedBg: theme.sider.selectedBg,
            darkItemSelectedColor: theme.sider.selectedColor,
            darkSubMenuItemBg: 'transparent',
          },
          Typography: {
            colorTextHeading: theme.token.colorText,
            colorText: theme.token.colorText,
            colorTextSecondary: theme.token.colorTextSecondary,
          }
        }
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/setup-mpin" element={<SetupMPIN />} />

          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <DashboardLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="profile" element={<Profile />} />

            {/* Admin routes - Protected by permission */}
            <Route
              path="users"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_admin_users">
                  <UserManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="roles"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_admin_roles">
                  <RoleManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="stations"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_admin_stations">
                  <StationManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="permissions"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_admin_permissions">
                  <PermissionManagement />
                </PermissionProtectedRoute>
              }
            />

            {/* EIC routes */}
            <Route
              path="logistics"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_eic_network_dashboard">
                  <LogisticsOverview />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="eic-approvals"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_eic_driver_approvals">
                  <EICShiftApprovals />
                </PermissionProtectedRoute>
              }
            />

            {/* Transport routes */}
            <Route
              path="transport-logistics"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_transport_logistics">
                  <TransportAdminLogistics />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="vehicles"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_transport_vehicles">
                  <VehicleManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="drivers"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_transport_drivers">
                  <DriverManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="shifts"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_transport_timesheet">
                  <ShiftManagement />
                </PermissionProtectedRoute>
              }
            />
            <Route
              path="timesheet"
              element={
                <PermissionProtectedRoute requiredPermission="can_view_transport_timesheet">
                  <TimesheetManagement />
                </PermissionProtectedRoute>
              }
            />
          </Route>

          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <PermissionProvider>
            <ThemedApp />
          </PermissionProvider>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
