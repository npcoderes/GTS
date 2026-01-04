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
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyOutlined,
  UserOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { permissionsAPI, rolesAPI, usersAPI } from '../services/api';

const { Option } = Select;
const { TextArea } = Input;
const { Search } = Input;

// Define which roles should be hidden from the Role Permissions tab (case-insensitive check will be used)
const HIDDEN_ROLES = ['fdodo customer', 'sgl transport vendor', 'super administrator', 'super admin', 'sgl customer'];

// Define allowed permissions per role (only these will appear in Manage modal)
// If a role is not listed here, it will show NO permissions (empty list)
// Keys are lowercase for case-insensitive matching
const ROLE_PERMISSION_MAP = {
  'dbs operator': [
    'can_approve_request',
    'can_submit_manual_request',
  ],
  'engineer in charge': [
    'can_approve_request',
    'can_manage_clusters',
    'can_override_tokens',
    'can_trigger_correction_actions',
    'can_manage_drivers',
  ],
  'ms operator': [
    // No permissions for MS Operator
  ],
  'sgl customer': [
    'can_approve_request',
    'can_submit_manual_request',
  ],
  'driver': [
    // No permissions for Driver
  ],
};

const PermissionManagement = () => {
  const [permissions, setPermissions] = useState([]);
  const [userPermissions, setUserPermissions] = useState([]);
  const [rolePermissions, setRolePermissions] = useState([]);
  const [roles, setRoles] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userPermLoading, setUserPermLoading] = useState(false);
  const [rolePermLoading, setRolePermLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [userPermModalVisible, setUserPermModalVisible] = useState(false);
  const [rolePermModalVisible, setRolePermModalVisible] = useState(false);
  const [editingPermission, setEditingPermission] = useState(null);
  const [editingUserPerm, setEditingUserPerm] = useState(null);
  const [selectedRole, setSelectedRole] = useState(null);
  const [rolePermValues, setRolePermValues] = useState({});
  const [userSearch, setUserSearch] = useState('');
  const [permSearch, setPermSearch] = useState('');
  const [form] = Form.useForm();
  const [userPermForm] = Form.useForm();
  const [rolePermForm] = Form.useForm();
  const [activeTab, setActiveTab] = useState('role-permissions');

  const categories = [
    { value: 'requests', label: 'Stock Requests' },
    { value: 'trips', label: 'Trips' },
    { value: 'drivers', label: 'Drivers' },
    { value: 'stations', label: 'Stations' },
    { value: 'tokens', label: 'Tokens' },
    { value: 'system', label: 'System' },
  ];

  useEffect(() => {
    fetchPermissions();
    fetchUsers();
    fetchRoles();
  }, []);

  // Debug logging removed for performance
  // useEffect(() => {
  //   console.log('Roles state updated:', roles);
  //   console.log('Role Permissions state:', rolePermissions);
  // }, [roles, rolePermissions]);

  useEffect(() => {
    if (activeTab === 'user-overrides') {
      fetchUserPermissions();
    } else if (activeTab === 'role-permissions' && rolePermissions.length === 0) {
      fetchRolePermissions();
    }
  }, [activeTab]);

  const fetchRoles = async () => {
    try {
      const response = await rolesAPI.getAll();
      const data = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      setRoles(data);
    } catch (error) {
      setRoles([]);
    }
  };

  const fetchRolePermissions = async () => {
    setRolePermLoading(true);
    try {
      const response = await permissionsAPI.getRolePermissions();
      const data = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      setRolePermissions(data);
    } catch (error) {
      setRolePermissions([]);
    } finally {
      setRolePermLoading(false);
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await usersAPI.getAll();
      const data = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      setUsers(data);
    } catch (error) {
      setUsers([]);
    }
  };

  const fetchUserPermissions = async () => {
    setUserPermLoading(true);
    try {
      const response = await permissionsAPI.getUserOverrides(null);
      const data = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      setUserPermissions(data);
    } catch (error) {
      setUserPermissions([]);
    } finally {
      setUserPermLoading(false);
    }
  };

  const fetchPermissions = async () => {
    setLoading(true);
    try {
      const response = await permissionsAPI.getAll();
      const data = Array.isArray(response.data) ? response.data : (response.data.results || []);
      setPermissions(data);
    } catch (error) {
      message.error('Failed to fetch permissions');
      setPermissions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingPermission(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingPermission(record);
    form.setFieldsValue({
      code: record.code,
      name: record.name,
      description: record.description,
      category: record.category,
    });
    setModalVisible(true);
  };

  const handleDelete = async (id) => {
    try {
      await permissionsAPI.deleteUserPermission(id);
      message.success('Permission deleted successfully');
      fetchPermissions();
    } catch (error) {
      message.error('Failed to delete permission');
      console.error(error);
    }
  };

  const handleAddUserPerm = () => {
    setEditingUserPerm(null);
    userPermForm.resetFields();
    setUserPermModalVisible(true);
  };

  const handleEditUserPerm = (record) => {
    setEditingUserPerm(record);
    userPermForm.setFieldsValue({
      user: record.user,
      permission: record.permission,
      granted: record.granted,
    });
    setUserPermModalVisible(true);
  };

  const handleDeleteUserPerm = async (id) => {
    try {
      await permissionsAPI.deleteUserPermission(id);
      message.success('User permission override deleted successfully');
      fetchUserPermissions();
    } catch (error) {
      message.error('Failed to delete user permission override');
      console.error(error);
    }
  };

  const handleManageRolePerms = async (role) => {
    setSelectedRole(role);

    // Pre-populate form with existing permissions
    try {
      const response = await permissionsAPI.getRolePermissions(role.id);
      const data = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      console.log('Loading permissions for role:', role.name, data);

      // Initialize all permissions to false first
      const formValues = {};
      permissions.forEach((perm) => {
        formValues[perm.code] = false;
      });

      // Set granted permissions to true
      data.forEach((rp) => {
        if (rp.permission_code && rp.granted) {
          formValues[rp.permission_code] = true;
        }
      });

      console.log('Form values to set:', formValues);
      setRolePermValues(formValues);

      // Use setTimeout to ensure form is rendered before setting values
      setTimeout(() => {
        rolePermForm.setFieldsValue(formValues);
      }, 100);
    } catch (error) {
      console.error('Failed to load role permissions:', error);
    }

    setRolePermModalVisible(true);
  };

  const handleRolePermSave = async () => {
    try {
      const values = await rolePermForm.validateFields();

      await permissionsAPI.bulkUpdateRolePermissions({
        role_id: selectedRole.id,
        permissions: values,
      });

      message.success(`Permissions updated for ${selectedRole.name}`);
      setRolePermModalVisible(false);
      rolePermForm.resetFields();
      fetchRolePermissions();
    } catch (error) {
      message.error('Failed to update role permissions');
      console.error(error);
    }
  };

  const handleUserPermSubmit = async (values) => {
    try {
      if (editingUserPerm) {
        await permissionsAPI.updateUserPermission(editingUserPerm.id, values);
        message.success('User permission override updated successfully');
      } else {
        await permissionsAPI.createUserPermission(values);
        message.success('User permission override created successfully');
      }
      setUserPermModalVisible(false);
      userPermForm.resetFields();
      fetchUserPermissions();
    } catch (error) {
      message.error(
        error.response?.data?.message || 'Failed to save user permission override'
      );
      console.error(error);
    }
  };

  const handleSubmit = async (values) => {
    try {
      if (editingPermission) {
        await permissionsAPI.updateRolePermission(editingPermission.id, values);
        message.success('Permission updated successfully');
      } else {
        await permissionsAPI.createRolePermission(values);
        message.success('Permission created successfully');
      }
      setModalVisible(false);
      form.resetFields();
      fetchPermissions();
    } catch (error) {
      message.error(
        error.response?.data?.message || 'Failed to save permission'
      );
      console.error(error);
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      requests: 'blue',
      trips: 'green',
      drivers: 'orange',
      stations: 'purple',
      tokens: 'cyan',
      system: 'red',
    };
    return colors[category] || 'default';
  };

  const userPermColumns = [
    {
      title: 'User',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 200,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>{record.user_email}</div>
        </div>
      ),
    },
    {
      title: 'Permission',
      dataIndex: 'permission_name',
      key: 'permission_name',
      width: 200,
      render: (text, record) => (
        <div>
          <div>{text}</div>
          <code style={{ fontSize: '11px', color: '#666' }}>{record.permission_code}</code>
        </div>
      ),
    },
    {
      title: 'Category',
      dataIndex: 'permission_category',
      key: 'permission_category',
      width: 120,
      render: (category) => {
        const cat = categories.find((c) => c.value === category);
        return (
          <Tag color={getCategoryColor(category)}>
            {cat?.label || category}
          </Tag>
        );
      },
    },
    {
      title: 'Status',
      dataIndex: 'granted',
      key: 'granted',
      width: 100,
      render: (granted) => (
        <Tag color={granted ? 'green' : 'red'}>
          {granted ? 'Granted' : 'Revoked'}
        </Tag>
      ),
    },
    {
      title: 'Created By',
      dataIndex: 'created_by_name',
      key: 'created_by_name',
      width: 150,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEditUserPerm(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this override?"
            onConfirm={() => handleDeleteUserPerm(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      width: 250,
      render: (text) => <code style={{ fontSize: '12px' }}>{text}</code>,
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      width: 150,
      render: (category) => {
        const cat = categories.find((c) => c.value === category);
        return (
          <Tag color={getCategoryColor(category)}>
            {cat?.label || category}
          </Tag>
        );
      },
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 150,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this permission?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={24}>
          <Card>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <h2 style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                  <SafetyOutlined style={{ marginRight: 8 }} />
                  Permission Management
                </h2>
                <p style={{ margin: '8px 0 0 0', color: '#666' }}>
                  Manage system permissions and user-specific overrides
                </p>
              </div>
              {activeTab === 'permissions' && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAdd}
                >
                  Add Permission
                </Button>
              )}
              {activeTab === 'user-overrides' && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleAddUserPerm}
                >
                  Add User Override
                </Button>
              )}
            </div>
          </Card>
        </Col>
      </Row>

      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} defaultActiveKey="role-permissions">
          <Tabs.TabPane
            tab={
              <span>
                <SafetyOutlined />
                Permissions
              </span>
            }
            key="permissions"
          >
            <Table
              columns={columns}
              dataSource={permissions}
              rowKey="id"
              loading={loading}
              pagination={{
                defaultPageSize: 10,
                showSizeChanger: true,
                pageSizeOptions: ['10', '20', '50', '100'],
                showTotal: (total) => `Total ${total} permissions`,
              }}
            />
          </Tabs.TabPane>
          <Tabs.TabPane
            tab={
              <span>
                <SafetyOutlined />
                Role Permissions
              </span>
            }
            key="role-permissions"
          >
            {rolePermLoading ? (
              <div style={{ textAlign: 'center', padding: '50px' }}>
                <Spin size="large" tip="Loading roles..." />
              </div>
            ) : roles.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '50px', color: '#999' }}>
                <SafetyOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                <div>No roles found</div>
              </div>
            ) : (
              <Row gutter={[16, 16]}>
                {roles
                  .filter((role) => !HIDDEN_ROLES.includes(role.name.toLowerCase()))
                  .map((role) => {
                  const rolePerms = rolePermissions.filter(
                    (rp) => rp.role === role.id && rp.granted
                  );
                  console.log(`Role ${role.name} (ID: ${role.id}):`, rolePerms);

                  return (
                    <Col xs={24} sm={12} lg={8} key={role.id}>
                      <Card
                        title={
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <SafetyOutlined />
                            <span>{role.name}</span>
                          </div>
                        }
                        extra={
                          <Button
                            type="primary"
                            size="small"
                            onClick={() => handleManageRolePerms(role)}
                          >
                            Manage
                          </Button>
                        }
                        style={{ height: '100%' }}
                      >
                        <div style={{ minHeight: 120 }}>
                          {rolePerms.length > 0 ? (
                            <div>
                              <div style={{ marginBottom: 8, fontSize: '12px', color: '#666' }}>
                                {rolePerms.length} permission{rolePerms.length !== 1 ? 's' : ''}
                              </div>
                              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                                {rolePerms.slice(0, 5).map((rp) => (
                                  <Tag key={rp.id} color="blue">
                                    {rp.permission_name}
                                  </Tag>
                                ))}
                                {rolePerms.length > 5 && (
                                  <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                                    +{rolePerms.length - 5} more
                                  </div>
                                )}
                              </Space>
                            </div>
                          ) : (
                            <div style={{
                              color: '#999',
                              fontStyle: 'italic',
                              textAlign: 'center',
                              padding: '20px 0'
                            }}>
                              No permissions assigned
                              <div style={{ fontSize: '12px', marginTop: 8 }}>
                                Click Manage to add permissions
                              </div>
                            </div>
                          )}
                        </div>
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            )}
          </Tabs.TabPane>
          <Tabs.TabPane
            tab={
              <span>
                <UserOutlined />
                User Overrides
              </span>
            }
            key="user-overrides"
          >
            <Table
              columns={userPermColumns}
              dataSource={userPermissions}
              rowKey="id"
              loading={userPermLoading}
              pagination={{
                defaultPageSize: 10,
                showSizeChanger: true,
                pageSizeOptions: ['10', '20', '50', '100'],
                showTotal: (total) => `Total ${total} user overrides`,
              }}
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      <Modal
        title={editingPermission ? 'Edit Permission' : 'Add Permission'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            label="Permission Code"
            name="code"
            rules={[
              { required: true, message: 'Please enter permission code' },
              {
                pattern: /^[a-z_]+$/,
                message: 'Only lowercase letters and underscores allowed',
              },
            ]}
            extra="Use snake_case format (e.g., can_view_trips)"
          >
            <Input placeholder="can_view_trips" />
          </Form.Item>

          <Form.Item
            label="Permission Name"
            name="name"
            rules={[{ required: true, message: 'Please enter permission name' }]}
          >
            <Input placeholder="View Trips" />
          </Form.Item>

          <Form.Item
            label="Category"
            name="category"
            rules={[{ required: true, message: 'Please select a category' }]}
          >
            <Select placeholder="Select category">
              {categories.map((cat) => (
                <Option key={cat.value} value={cat.value}>
                  {cat.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="Description" name="description">
            <TextArea
              rows={3}
              placeholder="Detailed description of what this permission allows"
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setModalVisible(false);
                  form.resetFields();
                }}
              >
                Cancel
              </Button>
              <Button type="primary" htmlType="submit">
                {editingPermission ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingUserPerm ? 'Edit User Permission Override' : 'Add User Permission Override'}
        open={userPermModalVisible}
        onCancel={() => {
          setUserPermModalVisible(false);
          userPermForm.resetFields();
        }}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form form={userPermForm} layout="vertical" onFinish={handleUserPermSubmit}>
          <Form.Item label="Search User" style={{ marginBottom: 16 }}>
            <Search
              placeholder="Search by name or email"
              allowClear
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              prefix={<SearchOutlined />}
            />
          </Form.Item>

          <Form.Item
            label="User"
            name="user"
            rules={[{ required: true, message: 'Please select a user' }]}
          >
            <Select
              placeholder="Select user"
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) => {
                const searchText = userSearch.toLowerCase();
                const userName = option.label?.toLowerCase() || '';
                return userName.includes(searchText) || userName.includes(input.toLowerCase());
              }}
            >
              {users
                .filter((user) => {
                  if (!userSearch) return true;
                  const search = userSearch.toLowerCase();
                  return (
                    user.full_name?.toLowerCase().includes(search) ||
                    user.email?.toLowerCase().includes(search)
                  );
                })
                .map((user) => (
                  <Select.Option
                    key={user.id}
                    value={user.id}
                    label={`${user.full_name} ${user.email}`}
                  >
                    {user.full_name} ({user.email})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item label="Search Permission" style={{ marginBottom: 16 }}>
            <Search
              placeholder="Search by name or code"
              allowClear
              value={permSearch}
              onChange={(e) => setPermSearch(e.target.value)}
              prefix={<SearchOutlined />}
            />
          </Form.Item>

          <Form.Item
            label="Permission"
            name="permission"
            rules={[{ required: true, message: 'Please select a permission' }]}
          >
            <Select
              placeholder="Select permission"
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) => {
                const searchText = permSearch.toLowerCase();
                const permText = option.label?.toLowerCase() || '';
                return permText.includes(searchText) || permText.includes(input.toLowerCase());
              }}
            >
              {permissions
                .filter((perm) => {
                  if (!permSearch) return true;
                  const search = permSearch.toLowerCase();
                  return (
                    perm.name?.toLowerCase().includes(search) ||
                    perm.code?.toLowerCase().includes(search)
                  );
                })
                .map((perm) => (
                  <Select.Option
                    key={perm.id}
                    value={perm.id}
                    label={`${perm.name} ${perm.code}`}
                  >
                    {perm.name} ({perm.code})
                  </Select.Option>
                ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="Grant Permission"
            name="granted"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="Granted" unCheckedChildren="Revoked" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setUserPermModalVisible(false);
                  userPermForm.resetFields();
                }}
              >
                Cancel
              </Button>
              <Button type="primary" htmlType="submit">
                {editingUserPerm ? 'Update' : 'Create'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Manage Permissions for ${selectedRole?.name || 'Role'}`}
        open={rolePermModalVisible}
        onCancel={() => {
          setRolePermModalVisible(false);
          rolePermForm.resetFields();
          setSelectedRole(null);
          setRolePermValues({});
        }}
        onOk={handleRolePermSave}
        width={700}
        okText="Save"
        destroyOnClose
        forceRender={false}
      >
        {selectedRole && permissions.length > 0 ? (
          <Form form={rolePermForm} layout="vertical">
            <div style={{ marginBottom: 16, padding: '12px', background: '#f0f7ff', borderRadius: 6 }}>
              <strong>Role: {selectedRole.name}</strong>
              <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                Toggle permissions on/off. Users with this role will inherit these permissions.
              </div>
            </div>
            <div style={{ maxHeight: '500px', overflowY: 'auto', paddingRight: '10px' }}>
              {/* Filter permissions based on role - only show allowed permissions */}
              {(() => {
                const allowedPerms = ROLE_PERMISSION_MAP[selectedRole.name.toLowerCase()];
                const filteredPermissions = allowedPerms 
                  ? permissions.filter(perm => allowedPerms.includes(perm.code))
                  : []; // If role not in map, show no permissions
                
                if (filteredPermissions.length === 0) {
                  return (
                    <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                      <SafetyOutlined style={{ fontSize: 36, marginBottom: 12 }} />
                      <div>No permissions available for this role</div>
                    </div>
                  );
                }
                
                return filteredPermissions.map((perm) => {
                const isChecked = rolePermValues[perm.code] || false;
                return (
                  <div
                    key={perm.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '12px',
                      border: `1px solid ${isChecked ? '#1890ff' : '#f0f0f0'}`,
                      borderRadius: 6,
                      backgroundColor: isChecked ? '#f0f7ff' : '#fafafa',
                      marginBottom: 8,
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, marginBottom: 4 }}>{perm.name}</div>
                      <div style={{ fontSize: '12px', color: '#666' }}>
                        <code style={{ background: '#fff', padding: '2px 6px', borderRadius: 3 }}>
                          {perm.code}
                        </code>
                        {perm.description && ` - ${perm.description}`}
                      </div>
                    </div>
                    <Form.Item
                      name={perm.code}
                      valuePropName="checked"
                      style={{ margin: 0 }}
                    >
                      <Switch
                        checked={isChecked}
                        onChange={(checked) => {
                          const newValues = { ...rolePermValues, [perm.code]: checked };
                          setRolePermValues(newValues);
                          rolePermForm.setFieldsValue({ [perm.code]: checked });
                        }}
                      />
                    </Form.Item>
                  </div>
                );
              });
              })()}
            </div>
          </Form>
        ) : (
          <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
            No permissions available
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PermissionManagement;
