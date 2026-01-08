import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Popconfirm,
  Tag,
  Row,
  Col,
  Tabs,
  Switch,
  Spin,
  Typography,
  Tooltip,
  Badge,
  Empty,
  Divider,
  Layout,
  Breadcrumb,
  List,
  Collapse
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  UserOutlined,
  SearchOutlined,
  DesktopOutlined,
  MobileOutlined,
  GlobalOutlined,
  ReloadOutlined,
  AppstoreOutlined,
  BankOutlined,
  CheckOutlined,
  CloseOutlined,
  FilterFilled,
  MoreOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { permissionsAPI, rolesAPI, usersAPI, stationsAPI } from '../services/api';
import './PermissionManagement.css';

const { Text, Title, Paragraph } = Typography;
const { Option } = Select;
const { Panel } = Collapse;

// Platform configuration for grouping
const PLATFORM_CONFIG = {
  all: { label: 'All Platforms', color: 'purple', icon: 'global' },
  dashboard: { label: 'Dashboard Only', color: 'blue', icon: 'desktop' },
  mobile: { label: 'Mobile Only', color: 'green', icon: 'mobile' }
};

const PermissionManagement = () => {
  // Data state
  const [permissions, setPermissions] = useState([]);
  const [userPermissions, setUserPermissions] = useState([]);
  const [rolePermissions, setRolePermissions] = useState([]);
  const [rolePermCounts, setRolePermCounts] = useState({}); // {roleId: count}
  const [stationPermissions, setStationPermissions] = useState([]);
  const [stationPermCounts, setStationPermCounts] = useState({}); // {stationId: count}
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [stations, setStations] = useState([]);

  // Loading states
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Modal states
  const [permissionModalVisible, setPermissionModalVisible] = useState(false);
  const [userOverrideModalVisible, setUserOverrideModalVisible] = useState(false);
  const [rolePermModalVisible, setRolePermModalVisible] = useState(false);
  const [stationPermModalVisible, setStationPermModalVisible] = useState(false);

  // Selection states
  const [editingPermission, setEditingPermission] = useState(null);
  const [editingUserOverride, setEditingUserOverride] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [selectedStation, setSelectedStation] = useState(null);

  // Filter states
  const [searchText, setSearchText] = useState('');
  const [platformFilter, setPlatformFilter] = useState('all');
  const [modalSearch, setModalSearch] = useState('');
  const [modalPlatformFilter, setModalPlatformFilter] = useState('all');
  const [modalLoading, setModalLoading] = useState(false);

  // Permission values for modals
  const [rolePermValues, setRolePermValues] = useState({});
  const [stationPermValues, setStationPermValues] = useState({});

  // Forms
  const [permissionForm] = Form.useForm();
  const [userOverrideForm] = Form.useForm();

  // Initial fetch
  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchPermissions(),
        fetchRoles(),
        fetchRolePermissions(),
        fetchStations(),
        fetchStationPermissions(),
        fetchUserPermissions(),
        fetchUsers()
      ]);
    } catch (error) {
      console.error(error);
      message.error("Could not load permission data. Please try refreshing.");
    } finally {
      setLoading(false);
    }
  };

  // API Wrappers
  const fetchPermissions = async () => {
    const res = await permissionsAPI.getAll();
    setPermissions(res.data?.results || res.data || []);
  };
  const fetchRoles = async () => {
    const res = await rolesAPI.getAll();
    setRoles(res.data?.results || res.data || []);
  };
  const fetchStations = async () => {
    const res = await stationsAPI.getAll();
    setStations(res.data?.results || res.data || []);
  };
  const fetchRolePermissions = async () => {
    const res = await permissionsAPI.getRolePermissions();
    const data = res.data?.results || res.data || [];
    setRolePermissions(data);

    // Compute counts: group by role and count granted=true
    const counts = {};
    data.forEach(rp => {
      if (rp.granted) {
        counts[rp.role] = (counts[rp.role] || 0) + 1;
      }
    });
    setRolePermCounts(counts);
  };
  const fetchStationPermissions = async () => {
    const res = await permissionsAPI.getStationPermissions();
    const data = res.data?.results || res.data || [];
    setStationPermissions(data);

    // Compute counts: group by station and count granted=true
    const counts = {};
    data.forEach(sp => {
      if (sp.granted) {
        counts[sp.station] = (counts[sp.station] || 0) + 1;
      }
    });
    setStationPermCounts(counts);
  };
  const fetchUserPermissions = async () => {
    const res = await permissionsAPI.getUserOverrides(null);
    setUserPermissions(res.data?.results || res.data || []);
  };
  const fetchUsers = async () => {
    const res = await usersAPI.getAll();
    setUsers(res.data?.results || res.data || []);
  };

  // Filtering Permissions for Table
  const filteredPermissions = useMemo(() => {
    return permissions.filter(perm => {
      if (searchText && !perm.name.toLowerCase().includes(searchText.toLowerCase()) && !perm.code.toLowerCase().includes(searchText.toLowerCase())) return false;
      if (platformFilter !== 'all' && perm.platform !== platformFilter) return false;
      return true;
    });
  }, [permissions, searchText, platformFilter]);

  // Filtering Permissions for Modals - grouped by platform
  const groupedModalPermissions = useMemo(() => {
    let filtered = permissions;

    // 1. Text Search
    if (modalSearch) {
      const s = modalSearch.toLowerCase();
      filtered = filtered.filter(p => p.name.toLowerCase().includes(s) || p.code.toLowerCase().includes(s));
    }

    // 2. Platform Filter
    if (modalPlatformFilter !== 'all') {
      filtered = filtered.filter(p => p.platform === modalPlatformFilter || p.platform === 'all');
    }

    // 3. Group by Platform
    const groups = {};
    filtered.forEach(p => {
      const plat = p.platform || 'all';
      if (!groups[plat]) groups[plat] = [];
      groups[plat].push(p);
    });

    return groups;
  }, [permissions, modalSearch, modalPlatformFilter]);

  // --- Role Actions ---
  const handleManageRole = async (role) => {
    setSelectedRole(role);
    setModalSearch('');
    setModalPlatformFilter('all');
    setRolePermModalVisible(true);
    setModalLoading(true);

    // Fetch fresh matrix from backend for accurate toggle states
    try {
      const res = await permissionsAPI.getRolePermissionMatrix(role.id);
      const matrix = res.data || [];
      const values = {};
      matrix.forEach(p => values[p.code] = p.granted);
      setRolePermValues(values);
    } catch (e) {
      // Fallback to local data if API fails
      console.error('Failed to fetch role permission matrix:', e);
      const values = {};
      permissions.forEach(p => values[p.code] = false);
      const currentRolePerms = rolePermissions.filter(rp => rp.role === role.id && rp.granted);
      currentRolePerms.forEach(rp => values[rp.permission_code] = true);
      setRolePermValues(values);
    } finally {
      setModalLoading(false);
    }
  };

  const saveRolePermissions = async () => {
    setSaving(true);
    try {
      await permissionsAPI.bulkUpdateRolePermissions({
        role_id: selectedRole.id,
        permissions: rolePermValues
      });
      message.success(`Permissions updated for ${selectedRole.name}`);
      setRolePermModalVisible(false);
      // Update the count for this role immediately
      const grantedCount = Object.values(rolePermValues).filter(v => v === true).length;
      setRolePermCounts(prev => ({ ...prev, [selectedRole.id]: grantedCount }));
      await fetchRolePermissions();
    } catch (e) {
      message.error("Failed to save permissions");
    } finally {
      setSaving(false);
    }
  };

  // --- Station Actions ---
  const handleManageStation = async (station) => {
    setSelectedStation(station);
    setModalSearch('');
    setModalPlatformFilter('all');
    setStationPermModalVisible(true);
    setModalLoading(true);

    // Fetch fresh matrix from backend for accurate toggle states
    try {
      const res = await permissionsAPI.getStationPermissionMatrix(station.id);
      const matrix = res.data || [];
      const values = {};
      matrix.forEach(p => values[p.code] = p.granted);
      setStationPermValues(values);
    } catch (e) {
      // Fallback to local data if API fails
      console.error('Failed to fetch station permission matrix:', e);
      const values = {};
      permissions.forEach(p => values[p.code] = false);
      const currentStationPerms = stationPermissions.filter(sp => sp.station === station.id && sp.granted);
      currentStationPerms.forEach(sp => values[sp.permission_code] = true);
      setStationPermValues(values);
    } finally {
      setModalLoading(false);
    }
  };

  const saveStationPermissions = async () => {
    setSaving(true);
    try {
      await permissionsAPI.bulkUpdateStationPermissions({
        station_id: selectedStation.id,
        permissions: stationPermValues
      });
      message.success(`Permissions updated for ${selectedStation.name}`);
      setStationPermModalVisible(false);
      // Update the count for this station immediately
      const grantedCount = Object.values(stationPermValues).filter(v => v === true).length;
      setStationPermCounts(prev => ({ ...prev, [selectedStation.id]: grantedCount }));
      await fetchStationPermissions();
    } catch (e) {
      message.error("Failed to save permissions");
    } finally {
      setSaving(false);
    }
  };

  // --- User Override Actions ---
  const handleSaveUserOverride = async (values) => {
    try {
      if (editingUserOverride) {
        await permissionsAPI.updateUserPermission(editingUserOverride.id, values);
      } else {
        await permissionsAPI.createUserPermission(values);
      }
      message.success("Override saved");
      setUserOverrideModalVisible(false);
      fetchUserPermissions();
    } catch (e) {
      message.error("Failed to save");
    }
  };

  const handleDeleteOverride = async (id) => {
    try {
      await permissionsAPI.deleteUserPermission(id);
      message.success("Override removed");
      fetchUserPermissions();
    } catch (e) {
      message.error("Failed to delete");
    }
  };

  // --- Permission Definition Actions ---
  const handleSavePermission = async (values) => {
    try {
      if (editingPermission) {
        await permissionsAPI.updatePermission(editingPermission.id, values);
      } else {
        await permissionsAPI.createPermission(values);
      }
      message.success("Permission definition saved");
      setPermissionModalVisible(false);
      fetchPermissions();
    } catch (e) {
      message.error("Failed to save");
    }
  };

  // Helper counts
  const getRolePermCount = (rid) => rolePermCounts[rid] || 0;
  const getStationPermCount = (sid) => stationPermCounts[sid] || 0;

  // Table Columns
  const roleColumns = [
    { title: 'Role Name', dataIndex: 'name', key: 'name', render: (t) => <Text strong>{t}</Text> },
    { title: 'Description', dataIndex: 'description', key: 'desc', ellipsis: true },
    {
      title: 'Active Permissions',
      key: 'count',
      render: (_, r) => <Tag color="blue">{getRolePermCount(r.id)} permissions</Tag>
    },
    {
      key: 'action',
      width: 120,
      render: (_, r) => (
        <Button type="link" size="small" onClick={() => handleManageRole(r)}>Configure Access</Button>
      )
    }
  ];

  const stationColumns = [
    { title: 'Station Name', dataIndex: 'name', key: 'name', render: (t) => <Text strong>{t}</Text> },
    { title: 'Type', dataIndex: 'type', key: 'type', render: (t) => <Tag>{t}</Tag> },
    { title: 'Code', dataIndex: 'station_code', key: 'code', render: t => t || '-' },
    {
      title: 'Active Permissions',
      key: 'count',
      render: (_, r) => <Tag color="orange">{getStationPermCount(r.id)} permissions</Tag>
    },
    {
      key: 'action',
      width: 120,
      render: (_, r) => (
        <Button type="link" size="small" onClick={() => handleManageStation(r)}>Configure Access</Button>
      )
    }
  ];

  const permissionListColumns = [
    {
      title: 'Name', dataIndex: 'name', key: 'name', width: 200,
      render: (text, rec) => (
        <div>
          <span style={{ fontWeight: 500 }}>{text}</span>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>{rec.code}</Text>
        </div>
      )
    },
    {
      title: 'Platform', dataIndex: 'platform', key: 'platform', width: 140,
      render: (plat) => {
        const conf = PLATFORM_CONFIG[plat] || PLATFORM_CONFIG.all;
        const Icon = plat === 'mobile' ? MobileOutlined : plat === 'dashboard' ? DesktopOutlined : GlobalOutlined;
        return <Tag icon={<Icon />} color={conf.color}>{conf.label}</Tag>;
      }
    },
    {
      title: 'Description', dataIndex: 'description', key: 'description'
    },
    {
      key: 'action', width: 100, align: 'right',
      render: (_, rec) => (
        <Space>
          <Button type="text" size="small" icon={<EditOutlined />} onClick={() => { setEditingPermission(rec); permissionForm.setFieldsValue(rec); setPermissionModalVisible(true); }} />
          <Popconfirm title="Delete?" onConfirm={async () => { await permissionsAPI.deletePermission(rec.id); fetchPermissions(); }}>
            <Button type="text" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      )
    }
  ];

  const overrideCols = [
    { title: 'User', dataIndex: 'user_name', key: 'user', render: (t, r) => <div><Text strong>{t}</Text><br /><Text type="secondary" style={{ fontSize: 12 }}>{r.user_email}</Text></div> },
    { title: 'Permission', dataIndex: 'permission_name', key: 'perm', render: (t, r) => <div><Text>{t}</Text><br /><Text type="secondary" style={{ fontSize: 12 }}>{r.permission_code}</Text></div> },
    { title: 'Status', dataIndex: 'granted', key: 'status', render: (g) => g ? <Tag color="success">Granted</Tag> : <Tag color="error">Revoked</Tag> },
    { key: 'act', width: 100, align: 'right', render: (_, r) => <Button type="text" danger icon={<DeleteOutlined />} onClick={() => handleDeleteOverride(r.id)} /> }
  ];

  const renderPermissionGroup = (platformKey, perms, values, toggleHandler) => {
    const platConfig = PLATFORM_CONFIG[platformKey] || PLATFORM_CONFIG.all;
    const Icon = platformKey === 'mobile' ? MobileOutlined : platformKey === 'dashboard' ? DesktopOutlined : GlobalOutlined;

    return (
      <div key={platformKey} className="perm-group-section">
        <div className="perm-group-header">
          <Space>
            <Icon style={{ color: platConfig.color === 'purple' ? '#722ed1' : platConfig.color === 'blue' ? '#1890ff' : '#52c41a' }} />
            <Text strong>{platConfig.label}</Text>
          </Space>
          <Badge count={perms.length} style={{ backgroundColor: '#f0f0f0', color: '#999', boxShadow: 'none' }} />
        </div>
        <div className="perm-group-list">
          {perms.map(p => (
            <div key={p.id} className="perm-row-item" onClick={() => toggleHandler(p.code, !values[p.code])}>
              <div className="perm-row-check">
                <Switch
                  size="small"
                  checked={!!values[p.code]}
                  onClick={(checked, e) => e.stopPropagation()}
                  onChange={(checked) => toggleHandler(p.code, checked)}
                />
              </div>
              <div className="perm-row-info">
                <div className="perm-row-name">{p.name}</div>
                <div className="perm-row-desc">{p.description || "No description provided"}</div>
              </div>
              {values[p.code] && <CheckOutlined style={{ color: '#10b981' }} />}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="modern-perm-container">
      {/* Header */}
      <div className="modern-header">
        <div>
          <Title level={3} style={{ marginBottom: 0 }}>Permissions</Title>
          <Text type="secondary">Manage system access, roles, and functional privileges</Text>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={fetchAllData}>Refresh Data</Button>
        </Space>
      </div>

      <div className="modern-content">
        <Tabs
          type="line"
          defaultActiveKey="roles"
          className="modern-tabs"
          items={[
            {
              key: 'roles',
              label: 'Roles & Access',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text type="secondary">Define what each role can do within the application.</Text>
                  </div>
                  <Table
                    className="modern-table"
                    columns={roleColumns}
                    dataSource={roles}
                    rowKey="id"
                    pagination={false}
                    loading={loading}
                  />
                </div>
              )
            },
            {
              key: 'stations',
              label: 'Stations',
              children: (
                <div>
                  <div style={{ marginBottom: 16 }}>
                    <Text type="secondary">Configure granular permissions for specific stations.</Text>
                  </div>
                  <Table
                    className="modern-table"
                    columns={stationColumns}
                    dataSource={stations}
                    rowKey="id"
                    pagination={{ pageSize: 10 }}
                    loading={loading}
                  />
                </div>
              )
            },
            {
              key: 'users',
              label: 'User Overrides',
              children: (
                <div>
                  <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Text type="secondary">Grant or revoke specific permissions for individual users, overriding their role.</Text>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingUserOverride(null); userOverrideForm.resetFields(); setUserOverrideModalVisible(true); }}>Add Override</Button>
                  </div>
                  <Table className="modern-table" columns={overrideCols} dataSource={userPermissions} pagination={{ pageSize: 10 }} rowKey="id" loading={loading} />
                </div>
              )
            },
            {
              key: 'definitions',
              label: 'Permission List',
              children: (
                <div>
                  <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
                    <Space>
                      <Input
                        prefix={<SearchOutlined style={{ color: '#ccc' }} />}
                        placeholder="Search..."
                        value={searchText}
                        onChange={e => setSearchText(e.target.value)}
                        allowClear
                        style={{ width: 250 }}
                      />
                      <Select value={platformFilter} onChange={setPlatformFilter} style={{ width: 150 }}>
                        <Option value="all">All Platforms</Option>
                        <Option value="dashboard">Dashboard</Option>
                        <Option value="mobile">Mobile</Option>
                      </Select>
                    </Space>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => { setEditingPermission(null); permissionForm.resetFields(); setPermissionModalVisible(true); }}>New Permission</Button>
                  </div>
                  <Table className="modern-table" columns={permissionListColumns} dataSource={filteredPermissions} pagination={{ pageSize: 10 }} rowKey="id" loading={loading} />
                </div>
              )
            }
          ]}
        />
      </div>

      {/* Configuration Modal (Shared for Roles & Stations) */}
      <Modal
        title={
          <div>
            <div style={{ fontSize: 18, fontWeight: 600 }}>Configure Permissions</div>
            <div style={{ fontSize: 13, fontWeight: 400, color: '#666' }}>
              {rolePermModalVisible ? `Role: ${selectedRole?.name}` : `Station: ${selectedStation?.name}`}
            </div>
          </div>
        }
        open={rolePermModalVisible || stationPermModalVisible}
        onCancel={() => { setRolePermModalVisible(false); setStationPermModalVisible(false); }}
        onOk={rolePermModalVisible ? saveRolePermissions : saveStationPermissions}
        width={800}
        confirmLoading={saving}
        okText="Save Changes"
        styles={{ body: { padding: 0, height: '600px', display: 'flex', flexDirection: 'column' } }}
        destroyOnHidden
      >
        <div className="config-modal-toolbar">
          <Input
            prefix={<SearchOutlined />}
            placeholder="Find a permission..."
            value={modalSearch}
            onChange={e => setModalSearch(e.target.value)}
            style={{ width: 250 }}
            allowClear
          />
          <Select
            value={modalPlatformFilter}
            onChange={setModalPlatformFilter}
            style={{ width: 180 }}
            dropdownMatchSelectWidth={false}
          >
            <Option value="all">All Platforms</Option>
            <Option value="dashboard"><DesktopOutlined /> Dashboard</Option>
            <Option value="mobile"><MobileOutlined /> Mobile</Option>
          </Select>
        </div>

        <div className="config-modal-content">
          {modalLoading ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Spin size="large" />
            </div>
          ) : Object.keys(groupedModalPermissions).length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No permissions found matching your filters" />
          ) : (
            Object.entries(groupedModalPermissions).map(([plat, perms]) =>
              renderPermissionGroup(
                plat,
                perms,
                rolePermModalVisible ? rolePermValues : stationPermValues,
                rolePermModalVisible
                  ? (code, val) => setRolePermValues(prev => ({ ...prev, [code]: val }))
                  : (code, val) => setStationPermValues(prev => ({ ...prev, [code]: val }))
              )
            )
          )}
        </div>
      </Modal>

      {/* Add Permission Modal */}
      <Modal
        title={editingPermission ? "Edit Permission" : "New Permission"}
        open={permissionModalVisible}
        onCancel={() => setPermissionModalVisible(false)}
        onOk={() => permissionForm.submit()}
      >
        <Form form={permissionForm} layout="vertical" onFinish={handleSavePermission}>
          <Form.Item name="code" label="Code" rules={[{ required: true }]} extra="Unique identifier (snake_case)">
            <Input placeholder="e.g. can_view_reports" disabled={!!editingPermission} />
          </Form.Item>
          <Form.Item name="name" label="Name" rules={[{ required: true }]}>
            <Input placeholder="e.g. View Reports" />
          </Form.Item>
          <Form.Item name="platform" label="Platform" initialValue="all" rules={[{ required: true }]}>
            <Select>
              <Option value="all"><GlobalOutlined /> All Platforms</Option>
              <Option value="dashboard"><DesktopOutlined /> Dashboard</Option>
              <Option value="mobile"><MobileOutlined /> Mobile</Option>
            </Select>
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={2} placeholder="Explain what this permission allows user to do" />
          </Form.Item>
        </Form>
      </Modal>

      {/* User Override Modal */}
      <Modal
        title="User Permission Override"
        open={userOverrideModalVisible}
        onCancel={() => setUserOverrideModalVisible(false)}
        onOk={() => userOverrideForm.submit()}
      >
        <div style={{ marginBottom: 16, background: '#e6f7ff', padding: 12, borderRadius: 4, border: '1px solid #91d5ff' }}>
          <InfoCircleOutlined style={{ color: '#1890ff', marginRight: 8 }} />
          <Text style={{ fontSize: 13 }}>Overrides take precedence over role permissions.</Text>
        </div>
        <Form form={userOverrideForm} layout="vertical" onFinish={handleSaveUserOverride}>
          <Form.Item name="user" label="User" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={users.map(u => ({ label: `${u.full_name} (${u.email})`, value: u.id }))} />
          </Form.Item>
          <Form.Item name="permission" label="Permission" rules={[{ required: true }]}>
            <Select showSearch optionFilterProp="label" options={permissions.map(p => ({ label: p.name, value: p.id }))} />
          </Form.Item>
          <Form.Item name="granted" label="Access Level" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren="GRANT Access" unCheckedChildren="REVOKE Access" />
          </Form.Item>
        </Form>
      </Modal>

    </div>
  );
};

export default PermissionManagement;
