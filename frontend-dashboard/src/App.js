import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme as antdTheme } from 'antd';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import ErrorBoundary from './components/ErrorBoundary';
import PrivateRoute from './components/PrivateRoute';
import RoleProtectedRoute from './components/RoleProtectedRoute';
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
import PermissionManagement from './pages/PermissionManagement';
import Profile from './pages/Profile';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import SetupMPIN from './pages/SetupMPIN';
import NotFound from './pages/NotFound';
import './App.css';

// Role definitions for route access
const ADMIN_ROLES = ['SUPER_ADMIN', 'EIC'];
const TRANSPORT_ROLES = ['TRANSPORT_ADMIN', 'VENDOR', 'SGL_TRANSPORT_VENDOR'];
const ALL_ROLES = [...ADMIN_ROLES, ...TRANSPORT_ROLES];

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
            boxShadowTertiary: theme.card.boxShadow, // Mapping our shadow to Card's tertiary shadow token
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

            {/* Admin only routes */}
            <Route
              path="users"
              element={
                <RoleProtectedRoute allowedRoles={ADMIN_ROLES}>
                  <UserManagement />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="roles"
              element={
                <RoleProtectedRoute allowedRoles={ADMIN_ROLES}>
                  <RoleManagement />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="stations"
              element={
                <RoleProtectedRoute allowedRoles={ADMIN_ROLES}>
                  <StationManagement />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="logistics"
              element={
                <RoleProtectedRoute allowedRoles={ADMIN_ROLES}>
                  <LogisticsOverview />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="permissions"
              element={
                <RoleProtectedRoute allowedRoles={ADMIN_ROLES}>
                  <PermissionManagement />
                </RoleProtectedRoute>
              }
            />

            {/* Transport roles routes */}
            <Route
              path="transport-logistics"
              element={
                <RoleProtectedRoute allowedRoles={TRANSPORT_ROLES}>
                  <TransportAdminLogistics />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="vehicles"
              element={
                <RoleProtectedRoute allowedRoles={TRANSPORT_ROLES}>
                  <VehicleManagement />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="drivers"
              element={
                <RoleProtectedRoute allowedRoles={TRANSPORT_ROLES}>
                  <DriverManagement />
                </RoleProtectedRoute>
              }
            />
            <Route
              path="shifts"
              element={
                <RoleProtectedRoute allowedRoles={TRANSPORT_ROLES}>
                  <ShiftManagement />
                </RoleProtectedRoute>
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
          <ThemedApp />
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
