import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Table,
  Button,
  Space,
  Tag,
  Input,
  Card,
  Modal,
  Form,
  message,
  Popconfirm,
  Row,
  Col,
  Select,
  DatePicker,
  Typography,
  Tooltip,
  Badge,
  Statistic,
  Dropdown,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  SafetyOutlined,
  ReloadOutlined,
  TeamOutlined,
  FilterOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloudSyncOutlined,
} from '@ant-design/icons';
import api, { usersAPI, rolesAPI, userRolesAPI, stationsAPI } from '../services/api';
import dayjs from 'dayjs';
import './UserManagement.css';

const { Title } = Typography;
const { Option } = Select;

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [stations, setStations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [isRoleModalVisible, setIsRoleModalVisible] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userRoles, setUserRoles] = useState([]);
  const [userRoleMap, setUserRoleMap] = useState({});
  // const [syncLoading, setSyncLoading] = useState(false); // Commented - SAP sync moved to backend auto-sync

  // Filter states
  const [statusFilter, setStatusFilter] = useState('all'); // all, active, inactive
  const [roleFilter, setRoleFilter] = useState('all');

  const [form] = Form.useForm();
  const [roleForm] = Form.useForm();
  const [selectedRoleCode, setSelectedRoleCode] = useState(null);

  // Generate simple password
  const generatePassword = () => {
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let password = '';
    for (let i = 0; i < 8; i++) {
      password += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return password;
  };

  const parseDateToDayjs = (value) => {
    if (!value) {
      return null;
    }
    const parsed = dayjs(value);
    return parsed.isValid() ? parsed : null;
  };

  const transformDateField = (value) => {
    if (value === null) {
      return null;
    }
    if (!value) {
      return undefined;
    }
    const parsed = dayjs(value);
    return parsed.isValid() ? parsed.toISOString() : undefined;
  };

  const getTimestamp = (value) => {
    if (!value) {
      return 0;
    }
    const parsed = dayjs(value);
    return parsed.isValid() ? parsed.valueOf() : 0;
  };

  useEffect(() => {
    fetchUsers();
    fetchRoles();
    fetchStations();
  }, []);

  const buildUserRoleMap = (assignments) => {
    if (!Array.isArray(assignments) || assignments.length === 0) {
      return {};
    }

    return assignments.reduce((acc, assignment) => {
      const userId = assignment?.user;
      if (!userId) {
        return acc;
      }

      const roleName = assignment?.role_detail?.name || assignment?.role?.name || 'Unknown Role';
      const roleCode = assignment?.role_detail?.code || assignment?.role?.code || '';
      const roleId = assignment?.role_detail?.id || assignment?.role?.id || assignment?.role || null;
      const stationId = assignment?.station_detail?.id || assignment?.station?.id || assignment?.station || null;
      const stationName = assignment?.station_detail?.name || assignment?.station?.name || null;
      const entry = {
        id: assignment?.id || 0,
        roleName,
        roleCode,
        stationName,
        active: assignment?.active === true,
        roleId,
        stationId,
      };

      if (!acc[userId]) {
        acc[userId] = [];
      }
      acc[userId].push(entry);
      return acc;
    }, {});
  };

  const extractResults = async (response) => {
    if (!response?.data) {
      return [];
    }

    const { data } = response;
    if (Array.isArray(data)) {
      return data;
    }

    let results = Array.isArray(data.results) ? [...data.results] : [];
    let nextUrl = data.next;

    while (nextUrl) {
      try {
        const nextResponse = await api.get(nextUrl);
        const nextData = nextResponse.data;

        if (Array.isArray(nextData)) {
          results = results.concat(nextData);
          break;
        }

        if (Array.isArray(nextData?.results)) {
          results = results.concat(nextData.results);
          nextUrl = nextData.next;
        } else {
          break;
        }
      } catch (paginationError) {
        console.error('Failed to fetch additional pages:', paginationError);
        break;
      }
    }

    return results;
  };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const [usersResponse, assignmentsResponse] = await Promise.all([
        usersAPI.getAll(),
        userRolesAPI.getAll(),
      ]);

      const userData = await extractResults(usersResponse);
      const assignmentData = await extractResults(assignmentsResponse);

      const safeUsers = Array.isArray(userData) ? userData : [];
      const safeAssignments = Array.isArray(assignmentData) ? assignmentData : [];

      setUsers(safeUsers);
      setUserRoleMap(buildUserRoleMap(safeAssignments));
    } catch (error) {
      console.error('Failed to fetch users:', error);
      message.error('Failed to load users. Please refresh.');
      setUsers([]);
      setUserRoleMap({});
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const response = await rolesAPI.getAll();
      const roleData = await extractResults(response);
      setRoles(Array.isArray(roleData) ? roleData : []);
    } catch (error) {
      console.error('Failed to fetch roles:', error);
      setRoles([]);
    }
  };

  const fetchStations = async () => {
    try {
      const response = await stationsAPI.getAll();
      const stationData = await extractResults(response);
      setStations(Array.isArray(stationData) ? stationData : []);
    } catch (error) {
      console.error('Failed to fetch stations:', error);
      setStations([]);
    }
  };

  const fetchUserRoles = async (userId) => {
    try {
      const response = await userRolesAPI.getByUser(userId);
      const userRoleData = await extractResults(response);
      setUserRoles(Array.isArray(userRoleData) ? userRoleData : []);
    } catch (error) {
      console.error('Failed to fetch user roles:', error);
      setUserRoles([]);
    }
  };

  const showModal = (user = null) => {
    setEditingUser(user);
    if (user) {
      form.setFieldsValue({
        email: user.email || '',
        full_name: user.full_name,
        phone: user.phone,
        is_active: user.is_active,
        role_in: parseDateToDayjs(user.role_in),
        role_out: parseDateToDayjs(user.role_out),
        role: userRoleMap[user.id]?.[0]?.roleId || undefined,
        station: userRoleMap[user.id]?.[0]?.stationId || undefined,
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        role_in: dayjs(),
        role_out: dayjs('9999-12-31'),
        password: generatePassword(),
      });
    }
    setIsModalVisible(true);
  };

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const roleInIso = transformDateField(values.role_in);
      const roleOutIso = transformDateField(values.role_out);
      const selectedRole = values.role || null;
      const selectedStation = values.station || null;
      const userPayload = { ...values };
      delete userPayload.role;
      delete userPayload.station;
      if (roleInIso !== undefined) {
        userPayload.role_in = roleInIso;
      } else {
        delete userPayload.role_in;
      }
      if (roleOutIso !== undefined) {
        userPayload.role_out = roleOutIso;
      } else {
        delete userPayload.role_out;
      }

      setLoading(true);

      if (editingUser) {
        await usersAPI.update(editingUser.id, userPayload);

        if (selectedRole) {
          const existingAssignments = userRoleMap[editingUser.id] || [];
          const primaryAssignment = existingAssignments[0];

          if (primaryAssignment) {
            await userRolesAPI.update(primaryAssignment.id, {
              user: editingUser.id,
              role: selectedRole,
              station: selectedStation || null,
              active: true,
            });
          } else {
            await userRolesAPI.assign({
              user: editingUser.id,
              role: selectedRole,
              station: selectedStation || null,
              active: true,
            });
          }
        }

        message.success('User updated successfully');
      } else {
        const createResponse = await usersAPI.create(userPayload);
        const createdUser = createResponse?.data;

        if (selectedRole && createdUser?.id) {
          await userRolesAPI.assign({
            user: createdUser.id,
            role: selectedRole,
            station: selectedStation || null,
            active: true,
          });
        }

        message.success('User created successfully');
      }

      await fetchUsers();
      setIsModalVisible(false);
      form.resetFields();
    } catch (error) {
      if (error.response) {
        message.error(error.response.data.message || 'Operation failed');
      } else if (error.errorFields) {
        message.error('Please fill in all required fields');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await usersAPI.delete(id);
      message.success('User deleted successfully');
      fetchUsers();
    } catch (error) {
      message.error('Failed to delete user');
      console.error(error);
    }
  };

  const showRoleModal = async (user) => {
    setSelectedUser(user);
    await fetchUserRoles(user.id);
    setIsRoleModalVisible(true);
  };

  const handleRoleAssign = async () => {
    try {
      const values = await roleForm.validateFields();
      const selectedRole = roles.find(r => r.id === values.role);

      // For EIC role with multiple stations, create multiple UserRole entries
      if (selectedRole?.code === 'EIC' && values.stations && values.stations.length > 0) {
        for (const stationId of values.stations) {
          await userRolesAPI.assign({
            user: selectedUser.id,
            role: values.role,
            station: stationId,
            active: true,
          });
        }
        message.success(`EIC role assigned with ${values.stations.length} MS station(s)`);
      } else {
        // Single station assignment for other roles
        await userRolesAPI.assign({
          user: selectedUser.id,
          role: values.role,
          station: values.station || null,
          active: true,
        });
        message.success('Role assigned successfully');
      }

      await fetchUserRoles(selectedUser.id);
      await fetchUsers();
      roleForm.resetFields();
      setSelectedRoleCode(null);
    } catch (error) {
      message.error(error.response?.data?.message || 'Failed to assign role');
    }
  };

  const handleRoleDelete = async (roleId) => {
    try {
      await userRolesAPI.delete(roleId);
      message.success('Role removed successfully');
      await fetchUserRoles(selectedUser.id);
      await fetchUsers();
    } catch (error) {
      message.error('Failed to remove role');
    }
  };

  // Commented out - SAP sync is now handled automatically in backend when users are created/updated
  // const syncUsersToSAP = async () => {
  //   setSyncLoading(true);
  //   try {
  //     const response = await api.post('/sap/sync-users/?active_only=true');
  //     if (response.data.success) {
  //       const summary = response.data.summary || 'Completed';
  //       message.success(`SAP Sync: ${summary}`, 4);
  //     } else {
  //       message.error(response.data.error || 'Sync failed');
  //     }
  //   } catch (error) {
  //     message.error('SAP sync failed');
  //   } finally {
  //     setSyncLoading(false);
  //   }
  // };

  // const showSyncModal = () => {
  //   Modal.confirm({
  //     title: 'Sync Users to SAP',
  //     icon: <CloudSyncOutlined />,
  //     content: 'This will sync all active users to SAP. Continue?',
  //     onOk: syncUsersToSAP,
  //     okText: 'Sync Now',
  //   });
  // };

  const columns = [
    {
      title: 'Full Name',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (text, record) => (
        <Space>
          <UserOutlined />
          <span style={{ fontWeight: 500 }}>{text}</span>
        </Space>
      ),
      sorter: (a, b) => a.full_name.localeCompare(b.full_name),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      render: (text) => (
        <Space>
          <MailOutlined />
          {text || <Tag color="default">Not Set</Tag>}
        </Space>
      ),
    },
    {
      title: 'Roles',
      key: 'roles',
      responsive: ['sm'],
      render: (_, record) => {
        const assignments = record?.id ? (userRoleMap[record.id] || []) : [];
        if (!Array.isArray(assignments) || assignments.length === 0) {
          return <Tag color="default">No roles</Tag>;
        }
        return (
          <Space size={[4, 4]} wrap>
            {assignments.map((assignment) => (
              <Tag key={assignment?.id || Math.random()} color={assignment?.active ? 'geekblue' : 'default'}>
                {assignment?.roleName || 'Unknown'}
                {assignment?.stationName ? ` • ${assignment.stationName}` : ''}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: 'Phone',
      dataIndex: 'phone',
      key: 'phone',
      responsive: ['sm'],
      render: (text) => (
        <Space>
          <PhoneOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Role In',
      dataIndex: 'role_in',
      key: 'role_in',
      responsive: ['md'],
      render: (value) => (
        value ? dayjs(value).format('MMM DD, YYYY') : <Tag color="default">Not set</Tag>
      ),
      sorter: (a, b) => getTimestamp(a.role_in) - getTimestamp(b.role_in),
    },
    {
      title: 'Role Out',
      dataIndex: 'role_out',
      key: 'role_out',
      responsive: ['md'],
      render: (value) => (
        value ? dayjs(value).format('MMM DD, YYYY') : <Tag color="default">Not set</Tag>
      ),
      sorter: (a, b) => getTimestamp(a.role_out) - getTimestamp(b.role_out),
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active) => (
        <Badge
          status={active ? 'success' : 'default'}
          text={active ? 'Active' : 'Inactive'}
        />
      ),
      filters: [
        { text: 'Active', value: true },
        { text: 'Inactive', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: 'Date Joined',
      dataIndex: 'date_joined',
      key: 'date_joined',
      render: (date) => dayjs(date).format('MMM DD, YYYY'),
      sorter: (a, b) => dayjs(a.date_joined).unix() - dayjs(b.date_joined).unix(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="Assign Roles">
            <Button
              type="link"
              icon={<SafetyOutlined />}
              onClick={() => showRoleModal(record)}
            >
              Roles
            </Button>
          </Tooltip>
          <Tooltip title="Edit User">
            <Button
              type="link"
              icon={<EditOutlined />}
              onClick={() => showModal(record)}
            />
          </Tooltip>
          <Popconfirm
            title="Are you sure you want to delete this user?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Tooltip title="Delete User">
              <Button type="link" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const lowerSearch = searchText.toLowerCase();

  const filteredUsers = Array.isArray(users) ? users.filter((user) => {
    // Text search
    const nameMatch = user?.full_name?.toLowerCase().includes(lowerSearch);
    const emailMatch = user?.email?.toLowerCase().includes(lowerSearch);
    const phoneMatch = user?.phone?.includes(searchText);
    const roleMatch = userRoleMap[user?.id]?.some((assignment) =>
      assignment.roleName.toLowerCase().includes(lowerSearch)
    );
    const roleInMatch = user?.role_in
      ? dayjs(user.role_in).format('MMM DD, YYYY').toLowerCase().includes(lowerSearch)
      : false;
    const roleOutMatch = user?.role_out
      ? dayjs(user.role_out).format('MMM DD, YYYY').toLowerCase().includes(lowerSearch)
      : false;

    const textMatch = !searchText || nameMatch || emailMatch || phoneMatch || roleMatch || roleInMatch || roleOutMatch;

    // Status filter
    const statusMatch = statusFilter === 'all' ||
      (statusFilter === 'active' && user.is_active) ||
      (statusFilter === 'inactive' && !user.is_active);

    // Role filter
    const roleFilterMatch = roleFilter === 'all' ||
      userRoleMap[user?.id]?.some((assignment) => String(assignment.roleId) === String(roleFilter));

    return textMatch && statusMatch && roleFilterMatch;
  }) : [];

  // Calculate stats
  const stats = {
    total: users.length,
    active: users.filter(u => u.is_active).length,
    inactive: users.filter(u => !u.is_active).length,
    withRoles: users.filter(u => userRoleMap[u.id]?.length > 0).length,
  };

  return (
    <div className="user-management">
      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: '#1F2937' }}>
              <TeamOutlined /> User Management
            </Title>
            <Typography.Text type="secondary">
              Manage users, roles, and permissions
            </Typography.Text>
          </Col>
          <Col>
            <Space>
              <Button icon={<ReloadOutlined />} onClick={fetchUsers} loading={loading}>
                Refresh
              </Button>
              {/* Commented - SAP sync is now handled automatically in backend
              <Button
                icon={<CloudSyncOutlined />}
                onClick={showSyncModal}
                loading={syncLoading}
              >
                Sync to SAP
              </Button>
              */}
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => showModal()}
              >
                Add User
              </Button>
            </Space>
          </Col>
        </Row>

        {/* Stats Cards */}
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card bordered={false} style={{ background: '#fff', borderRadius: 8 }}>
              <Statistic
                title="Total Users"
                value={stats.total}
                prefix={<UserOutlined />}
                valueStyle={{ color: '#2563EB' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card bordered={false} style={{ background: '#fff', borderRadius: 8 }}>
              <Statistic
                title="Active"
                value={stats.active}
                prefix={<CheckCircleOutlined />}
                valueStyle={{ color: '#52c41a' }}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card bordered={false} style={{ background: '#fff', borderRadius: 8 }}>
              <Statistic
                title="Inactive"
                value={stats.inactive}
                prefix={<CloseCircleOutlined />}
                valueStyle={{ color: '#ff4d4f' }}
              />
            </Card>
          </Col>
          {/* <Col xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card bordered={false} style={{ background: '#fff', borderRadius: 8 }}>
              <Statistic
                title="Staff"
                value={stats.staff}
                prefix={<SafetyOutlined />}
                valueStyle={{ color: '#722ed1' }}
              />
            </Card>
          </Col> */}
          {/* <Col xs={24} sm={12} md={8} lg={6} xl={4}>
            <Card bordered={false} style={{ background: '#fff', borderRadius: 8 }}>
              <Statistic
                title="With Roles"
                value={stats.withRoles}
                prefix={<TeamOutlined />}
                valueStyle={{ color: '#13c2c2' }}
              />
            </Card>
          </Col> */}
        </Row>
      </div>

      {/* Main Content Card */}
      <Card bordered={false}>
        {/* Search and Filters */}
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input
              placeholder="Search users..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="Status Filter"
              value={statusFilter}
              onChange={setStatusFilter}
            >
              <Option value="all">All Status</Option>
              <Option value="active">Active</Option>
              <Option value="inactive">Inactive</Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} md={8} lg={4}>
            <Select
              style={{ width: '100%' }}
              placeholder="Role Filter"
              value={roleFilter}
              onChange={setRoleFilter}
            >
              <Option value="all">All Roles</Option>
              {roles.map(role => (
                <Option key={role.id} value={String(role.id)}>{role.name}</Option>
              ))}
            </Select>
          </Col>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Space>
              <Typography.Text type="secondary">
                Showing {filteredUsers.length} of {users.length} users
              </Typography.Text>
            </Space>
          </Col>
        </Row>

        <div className="table-responsive">
          <Table
            columns={columns}
            dataSource={filteredUsers}
            rowKey="id"
            loading={loading}
            pagination={{
              defaultPageSize: 10,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (total) => `Total ${total} users`,
            }}
            scroll={{ x: 'max-content' }}
          />
        </div>
      </Card>

      {/* Create/Edit User Modal */}
      <Modal
        title={editingUser ? 'Edit User' : 'Create New User'}
        open={isModalVisible}
        onOk={handleOk}
        onCancel={() => {
          setIsModalVisible(false);
          form.resetFields();
        }}
        confirmLoading={loading}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="email"
            label="Email"
            // rules={[
            //   { message: 'Please input email!' },
            //   { type: 'email', message: 'Please enter a valid email!' },
            // ]}
          >
            <Input prefix={<MailOutlined />} placeholder="user@example.com" />
          </Form.Item>

          <Form.Item
            name="full_name"
            label="Full Name"
            rules={[{ required: true, message: 'Please input full name!' }]}
          >
            <Input prefix={<UserOutlined />} placeholder="John Doe" />
          </Form.Item>

          <Form.Item
            name="phone"
            label="Phone Number"
            rules={[{ required: true, message: 'Please input phone number!' }]}
          >
            <Input prefix={<PhoneOutlined />} placeholder="+1234567890" />
          </Form.Item>

          {!editingUser && (
            <Form.Item
              name="password"
              label="Password"
              rules={[
                { required: true, message: 'Please input password!' },
                { min: 6, message: 'Password must be at least 6 characters!' },
              ]}
            >
              <Input.Password placeholder="Enter password" />
            </Form.Item>
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="is_active"
                label="Active Status"
                initialValue={true}
              >
                <Select>
                  <Option value={true}>Active</Option>
                  <Option value={false}>Inactive</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="role_in"
                label="Role In"
              >
                <DatePicker
                  style={{ width: '100%' }}
                  placeholder="Select role in date"
                  allowClear
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="role_out"
                label="Role Out"
              >
                <DatePicker
                  style={{ width: '100%' }}
                  placeholder="Select role out date"
                  allowClear
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="role"
                label="Assign Role"
                rules={[{ required: true, message: 'Please select a role!' }]}
              >
                <Select
                  placeholder="Select role"
                  onChange={(value) => {
                    const role = roles.find(r => r.id === value);
                    setSelectedRoleCode(role?.code);
                    form.setFieldsValue({ station: undefined });
                  }}
                >
                  {roles.filter(role => role.code !== 'DRIVER').map((role) => (
                    <Option key={role.id} value={role.id}>
                      {role.name}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="station"
                label="Assign Station"
                rules={[{ required: true, message: 'Please select a station!' }]}
              >
                <Select
                  placeholder="Select station"
                  disabled={!selectedRoleCode}
                >
                  {selectedRoleCode === 'MS_OPERATOR' && stations.filter(s => s.type === 'MS').map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name}
                    </Option>
                  ))}
                  {selectedRoleCode === 'EIC' && stations.filter(s => s.type === 'MS').map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name}
                    </Option>
                  ))}
                  {selectedRoleCode === 'DBS_OPERATOR' && stations.filter(s => s.type === 'DBS').map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name}
                    </Option>
                  ))}
                  {selectedRoleCode === 'SGL_CUSTOMER' && stations.filter(s => s.type === 'DBS').map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name}
                    </Option>
                  ))}
                  {selectedRoleCode === 'SGL_TRANSPORT' && stations.map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name} ({station.type})
                    </Option>
                  ))}
                  {selectedRoleCode === 'FDODO_CUSTOMER' && stations.map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name} ({station.type})
                    </Option>
                  ))}
                  {/* {selectedRoleCode === 'DRIVER' && stations.map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name} ({station.type})
                    </Option>
                  ))} */}
                </Select>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      {/* Role Assignment Modal */}
      <Modal
        title={`Assign Roles - ${selectedUser?.full_name}`}
        open={isRoleModalVisible}
        onCancel={() => {
          setIsRoleModalVisible(false);
          roleForm.resetFields();
          setSelectedRoleCode(null);
        }}
        footer={null}
        width={700}
      >
        <Card
          title="Assign New Role"
          size="small"
          style={{ marginBottom: 16 }}
        >
          <Form form={roleForm} layout="vertical" onFinish={handleRoleAssign}>
            <Form.Item
              name="role"
              label="Select Role"
              rules={[{ required: true, message: 'Select a role!' }]}
            >
              <Select
                placeholder="Select Role"
                style={{ width: '100%' }}
                onChange={(value) => {
                  const role = roles.find(r => r.id === value);
                  setSelectedRoleCode(role?.code);
                  // Clear station selection when role changes
                  roleForm.setFieldsValue({ station: undefined, stations: undefined });
                }}
              >
                {roles.filter(role => role.code !== 'DRIVER').map((role) => (
                  <Option key={role.id} value={role.id}>
                    {role.name} ({role.code})
                  </Option>
                ))}
              </Select>
            </Form.Item>

            {/* For EIC role - show multi-select for MS stations */}
            {selectedRoleCode === 'EIC' ? (
              <Form.Item
                name="stations"
                label="Assign MS Stations (Multiple)"
                rules={[{ required: true, message: 'Select at least one MS station for EIC!' }]}
                extra="EIC can manage multiple Mother Stations"
              >
                <Select
                  mode="multiple"
                  placeholder="Select MS Stations"
                  style={{ width: '100%' }}
                  optionFilterProp="children"
                  showSearch
                >
                  {stations.filter(s => s.type === 'MS').map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name} ({station.code})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            ) : (
              <Form.Item
                name="station"
                label="Assign Station"
              >
                <Select placeholder="Select Station (Optional)" style={{ width: '100%' }} allowClear>
                  {stations.map((station) => (
                    <Option key={station.id} value={station.id}>
                      {station.name} ({station.type})
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            )}

            <Form.Item>
              <Button type="primary" htmlType="submit" block>
                {selectedRoleCode === 'EIC' ? 'Assign EIC to Selected Stations' : 'Assign Role'}
              </Button>
            </Form.Item>
          </Form>
        </Card>

        <Card title="Current Roles" size="small">
          {userRoles.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
              No roles assigned yet
            </div>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }}>
              {userRoles.map((userRole) => {
                const roleName = userRole.role_detail?.name || userRole.role?.name || 'Role';
                const stationName = userRole.station_detail?.name || userRole.station?.name || null;
                return (
                  <Card key={userRole.id} size="small">
                    <Row justify="space-between" align="middle">
                      <Col>
                        <Space direction="vertical" size="small">
                          <div>
                            <Tag color="blue">{roleName}</Tag>
                            {stationName && (
                              <Tag color="green">{stationName}</Tag>
                            )}
                            <Badge
                              status={userRole.active ? 'success' : 'default'}
                              text={userRole.active ? 'Active' : 'Inactive'}
                            />
                          </div>
                          <div style={{ fontSize: '12px', color: '#999' }}>
                            Assigned: {dayjs(userRole.created_at).format('MMM DD, YYYY')}
                          </div>
                        </Space>
                      </Col>
                      <Col>
                        <Popconfirm
                          title="Remove this role?"
                          onConfirm={() => handleRoleDelete(userRole.id)}
                        >
                          <Button type="link" danger size="small">
                            Remove
                          </Button>
                        </Popconfirm>
                      </Col>
                    </Row>
                  </Card>
                );
              })}
            </Space>
          )}
        </Card>
      </Modal>
    </div>
  );
};

export default UserManagement;
