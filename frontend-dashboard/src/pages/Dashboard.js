import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Spin, Table, Tag, Progress, Divider, Button, Alert, Empty } from 'antd';
import {
  UserOutlined,
  TeamOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  BankOutlined,
  CarOutlined,
  NodeIndexOutlined,
  EnvironmentOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  PlusOutlined,
  ReloadOutlined,
  TrophyOutlined,
  CalendarOutlined,
  RocketOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import { usersAPI, rolesAPI, stationsAPI } from '../services/api';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';

const { Title, Text } = Typography;

const Dashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const roleCode = (user?.role || '').toUpperCase();

  // Check if user is admin (SUPER_ADMIN or EIC)
  const isAdmin = roleCode === 'SUPER_ADMIN' || roleCode === 'EIC';
  // Check if user is transport role
  const isTransport = roleCode === 'TRANSPORT_ADMIN' || roleCode === 'VENDOR' || roleCode === 'SGL_TRANSPORT_VENDOR';

  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    totalRoles: 0,
    assignedRoles: 0,
    totalStations: 0,
    msStations: 0,
    dbsStations: 0,
    totalDrivers: 0,
    totalVehicles: 0,
    inactiveUsers: 0,
    activeShifts: 0,
    pendingShifts: 0,
  });
  const [msWithDbs, setMsWithDbs] = useState([]);

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const [usersRes, rolesRes, stationsRes] = await Promise.all([
        usersAPI.getAll(),
        rolesAPI.getAll(),
        stationsAPI.getAll(),
      ]);

      const users = Array.isArray(usersRes?.data?.results) ? usersRes.data.results :
        Array.isArray(usersRes?.data) ? usersRes.data : [];
      const roles = Array.isArray(rolesRes?.data?.results) ? rolesRes.data.results :
        Array.isArray(rolesRes?.data) ? rolesRes.data : [];
      const stations = Array.isArray(stationsRes?.data?.results) ? stationsRes.data.results :
        Array.isArray(stationsRes?.data) ? stationsRes.data : [];

      const activeUsers = users.filter(user => user?.is_active === true).length;
      const msStations = stations.filter(s => s?.type === 'MS');
      const dbsStations = stations.filter(s => s?.type === 'DBS');

      const msDbsMap = msStations.map(ms => {
        const linkedDbs = dbsStations.filter(dbs => dbs?.parent_station === ms?.id);
        return {
          id: ms?.id || 0,
          msName: ms?.name || 'Unknown',
          msCode: ms?.code || 'N/A',
          city: ms?.city || 'N/A',
          dbsCount: linkedDbs.length,
          dbsList: linkedDbs
        };
      });

      setMsWithDbs(msDbsMap);

      let driverCount = 0;
      let vehicleCount = 0;

      try {
        const driversRes = await apiClient.get('/drivers/');
        const drivers = Array.isArray(driversRes?.data?.results) ? driversRes.data.results :
          Array.isArray(driversRes?.data) ? driversRes.data : [];
        driverCount = drivers.length;
      } catch (e) {
        // Drivers API not available
      }

      try {
        const vehiclesRes = await apiClient.get('/vehicles/');
        const vehicles = Array.isArray(vehiclesRes?.data?.results) ? vehiclesRes.data.results :
          Array.isArray(vehiclesRes?.data) ? vehiclesRes.data : [];
        vehicleCount = vehicles.length;
      } catch (e) {
        // Vehicles API not available
      }

      setStats({
        totalUsers: users.length,
        activeUsers: activeUsers,
        inactiveUsers: users.length - activeUsers,
        totalRoles: roles.length,
        assignedRoles: 0,
        totalStations: stations.length,
        msStations: msStations.length,
        dbsStations: dbsStations.length,
        totalDrivers: driverCount,
        totalVehicles: vehicleCount,
        activeShifts: 0,
        pendingShifts: 0,
      });

      try {
        const shiftsRes = await apiClient.get('/shifts/');
        const shifts = Array.isArray(shiftsRes?.data?.results) ? shiftsRes.data.results :
          Array.isArray(shiftsRes?.data) ? shiftsRes.data : [];
        const activeShifts = shifts.filter(s => s?.status === 'APPROVED' || s?.status === 'ACTIVE').length;
        const pendingShifts = shifts.filter(s => s?.status === 'PENDING').length;
        setStats(prev => ({
          ...prev,
          activeShifts,
          pendingShifts,
        }));
      } catch (e) {
        // Shifts API not available
      }
    } catch (error) {
      console.error('Failed to fetch dashboard stats:', error);
      setStats({
        totalUsers: 0,
        activeUsers: 0,
        inactiveUsers: 0,
        totalRoles: 0,
        assignedRoles: 0,
        totalStations: 0,
        msStations: 0,
        dbsStations: 0,
        totalDrivers: 0,
        totalVehicles: 0,
        activeShifts: 0,
        pendingShifts: 0,
      });
      setMsWithDbs([]);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon, color, subtitle, onClick }) => (
    <Card
      bordered={false}
      hoverable
      onClick={onClick}
      style={{
        borderRadius: 12,
        boxShadow: theme.card.boxShadow,
        background: theme.card.background,
        height: '100%',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.3s ease',
      }}
      bodyStyle={{ padding: '20px' }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
        <div style={{ flex: 1 }}>
          <Text type="secondary" style={{ fontSize: 13, fontWeight: 500 }}>{title}</Text>
          <div style={{
            fontSize: 32,
            fontWeight: 700,
            color: color,
            marginTop: 8,
            marginBottom: 8
          }}>
            {value}
          </div>
          {subtitle && <Text type="secondary" style={{ fontSize: 12 }}>{subtitle}</Text>}
        </div>
        <div style={{
          width: 56,
          height: 56,
          borderRadius: 12,
          background: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          {React.cloneElement(icon, { style: { fontSize: 28, color: color } })}
        </div>
      </div>
    </Card>
  );

  const stationColumns = [
    {
      title: 'Mother Station',
      dataIndex: 'msName',
      key: 'msName',
      render: (text, record) => (
        <Space>
          <BankOutlined style={{ color: '#2563EB' }} />
          <div>
            <Text strong>{text}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>{record.msCode}</Text>
          </div>
        </Space>
      )
    },
    {
      title: 'Location',
      dataIndex: 'city',
      key: 'city',
      render: (text) => (
        <Space>
          <EnvironmentOutlined style={{ color: '#52c41a' }} />
          <Text>{text || 'N/A'}</Text>
        </Space>
      )
    },
    {
      title: 'Linked DBS',
      dataIndex: 'dbsCount',
      key: 'dbsCount',
      render: (count) => (
        <Tag
          color={count > 0 ? 'blue' : 'default'}
          style={{
            borderRadius: 12,
            padding: '4px 12px',
            fontSize: 14,
            fontWeight: 600
          }}
        >
          {count} DBS
        </Tag>
      )
    },
    {
      title: 'Status',
      key: 'status',
      render: () => (
        <Tag color="green" style={{ borderRadius: 12 }}>Active</Tag>
      )
    }
  ];

  const expandedRowRender = (record) => {
    if (!record.dbsList || record.dbsList.length === 0) {
      return <Text type="secondary">No DBS stations linked</Text>;
    }

    return (
      <div style={{ padding: '8px 0' }}>
        <Space wrap>
          {record.dbsList.map(dbs => (
            <Tag
              key={dbs.id}
              color="cyan"
              style={{
                padding: '4px 12px',
                borderRadius: 8,
                marginBottom: 4
              }}
            >
              <NodeIndexOutlined /> {dbs.name} ({dbs.code})
            </Tag>
          ))}
        </Space>
      </div>
    );
  };

  return (
    <div style={{ padding: 24, background: theme.token.colorBgLayout, minHeight: '100vh' }}>
      {/* Header Section */}
      <div style={{
        marginBottom: 24,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 16
      }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            {isAdmin ? 'Admin Dashboard' : 'Transport Dashboard'}
          </Title>
          <Text type="secondary" style={{ fontSize: 14 }}>
            Welcome back, {user?.name || user?.full_name || 'User'}! Here's your overview.
          </Text>
        </div>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={fetchDashboardStats}
            loading={loading}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: 100 }}>
          <Spin size="large" />
        </div>
      ) : (
        <>
          {/* Key Metrics Section */}
          <Card
            bordered={false}
            style={{
              borderRadius: 12,
              boxShadow: theme.card.boxShadow,
              background: theme.card.background,
              marginBottom: 24
            }}
          >
            <Title level={4} style={{ marginBottom: 20 }}>
              {isAdmin ? 'System Overview' : 'Fleet Overview'}
            </Title>
            <Row gutter={[20, 20]}>
              {isAdmin ? (
                <>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="Total Users"
                      value={stats.totalUsers}
                      icon={<UserOutlined />}
                      color="#2563EB"
                      subtitle={`${stats.activeUsers} active`}
                      onClick={() => navigate('/dashboard/users')}
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="MS Stations"
                      value={stats.msStations}
                      icon={<BankOutlined />}
                      color="#722ed1"
                      subtitle="Mother Stations"
                      onClick={() => navigate('/dashboard/stations')}
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="DBS Stations"
                      value={stats.dbsStations}
                      icon={<NodeIndexOutlined />}
                      color="#13c2c2"
                      subtitle="Daughter Stations"
                      onClick={() => navigate('/dashboard/stations')}
                    />
                  </Col>
                </>
              ) : (
                <>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="Total Drivers"
                      value={stats.totalDrivers}
                      icon={<TeamOutlined />}
                      color="#52c41a"
                      subtitle="Registered drivers"
                      onClick={() => navigate('/dashboard/drivers')}
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="Vehicles"
                      value={stats.totalVehicles}
                      icon={<CarOutlined />}
                      color="#eb2f96"
                      subtitle="Fleet size"
                      onClick={() => navigate('/dashboard/vehicles')}
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="Active Shifts"
                      value={stats.activeShifts || 0}
                      icon={<CalendarOutlined />}
                      color="#2563EB"
                      subtitle="Today's shifts"
                      onClick={() => navigate('/dashboard/shifts')}
                    />
                  </Col>
                  <Col xs={24} sm={12} lg={6}>
                    <StatCard
                      title="Pending Approval"
                      value={stats.pendingShifts || 0}
                      icon={<CheckCircleOutlined />}
                      color="#fa8c16"
                      subtitle="Awaiting EIC"
                      onClick={() => navigate('/dashboard/shifts')}
                    />
                  </Col>
                </>
              )}
            </Row>
          </Card>

          {/* Station Overview - Admin Only */}
          {isAdmin && msWithDbs.length > 0 && (
            <Row gutter={[20, 20]} style={{ marginTop: 24 }}>
              <Col xs={24}>
                <Card
                  title={
                    <Space>
                      <BankOutlined style={{ color: '#2563EB' }} />
                      <span>Station Overview - MS with Linked DBS</span>
                    </Space>
                  }
                  bordered={false}
                  style={{
                    borderRadius: 12,
                    boxShadow: theme.card.boxShadow,
                    background: theme.card.background,
                  }}
                  extra={
                    <Tag color="blue" style={{ borderRadius: 12 }}>
                      {stats.msStations} MS → {stats.dbsStations} DBS
                    </Tag>
                  }
                >
                  <Table
                    columns={stationColumns}
                    dataSource={msWithDbs}
                    rowKey="id"
                    expandable={{
                      expandedRowRender,
                      rowExpandable: (record) => record.dbsCount > 0,
                    }}
                    pagination={false}
                    size="middle"
                  />
                </Card>
              </Col>
            </Row>
          )}

          {/* Quick Info */}
          <Row gutter={[20, 20]} style={{ marginTop: 24 }}>
            <Col xs={24}>
              <Card
                title={
                  <Space>
                    <RocketOutlined style={{ color: '#2563EB' }} />
                    <span>Quick Actions</span>
                  </Space>
                }
                bordered={false}
                style={{
                  borderRadius: 12,
                  boxShadow: theme.card.boxShadow,
                  background: theme.card.background,
                }}
              >
                <Row gutter={[16, 16]}>
                  {isAdmin && (
                    <>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<PlusOutlined />}
                          onClick={() => navigate('/dashboard/users')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          Add New User
                        </Button>
                      </Col>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<BankOutlined />}
                          onClick={() => navigate('/dashboard/stations')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          View Station
                        </Button>
                      </Col>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<CarOutlined />}
                          onClick={() => navigate('/dashboard/trips')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          View Trips
                        </Button>
                      </Col>

                    </>
                  )}
                  {isTransport && (
                    <>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<TeamOutlined />}
                          onClick={() => navigate('/dashboard/drivers')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          Manage Drivers
                        </Button>
                      </Col>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<CarOutlined />}
                          onClick={() => navigate('/dashboard/vehicles')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          Manage Vehicles
                        </Button>
                      </Col>
                      <Col xs={24} sm={12} md={8}>
                        <Button
                          block
                          size="large"
                          icon={<CalendarOutlined />}
                          onClick={() => navigate('/dashboard/shifts')}
                          style={{ height: 60, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          Create Shift
                        </Button>
                      </Col>
                    </>
                  )}
                </Row>
                <Divider />
                <div>
                  <Title level={5} style={{ marginBottom: 12 }}>
                    {isAdmin ? 'Admin Guide' : 'Transport Guide'}
                  </Title>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    {isAdmin ? (
                      <>
                        <Text type="secondary">
                          • Manage <Text strong>Users</Text> and assign appropriate roles
                        </Text>
                        <Text type="secondary">
                          • Monitor <Text strong>Logistics</Text> and track deliveries
                        </Text>
                        <Text type="secondary">
                          • Set up <Text strong>Permissions</Text> for fine-grained access control
                        </Text>
                      </>
                    ) : (
                      <>
                        <Text type="secondary">
                          • Register and manage your <Text strong>Drivers</Text>
                        </Text>
                        <Text type="secondary">
                          • Add and maintain <Text strong>Vehicles</Text> in your fleet
                        </Text>
                        <Text type="secondary">
                          • Create <Text strong>Shifts</Text> for daily operations
                        </Text>
                        <Text type="secondary">
                          • Shifts require EIC approval before activation
                        </Text>
                      </>
                    )}
                  </Space>
                </div>
              </Card>
            </Col>
          </Row>
        </>
      )}
    </div>
  );
};

export default Dashboard;
