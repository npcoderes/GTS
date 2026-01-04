import React, { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Typography,
  Space,
  message,
  Tag,
  Popconfirm
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { rolesAPI } from '../services/api';
import './RoleManagement.css';

const { Title, Paragraph } = Typography;
const { TextArea } = Input;

const RoleManagement = () => {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const fetchRoles = useCallback(async () => {
    setLoading(true);
    try {
      const response = await rolesAPI.getAll({ page_size: 200 });
      const data = response.data.results || response.data;
      setRoles(Array.isArray(data) ? data : []);
    } catch (error) {
      message.error('Failed to fetch roles');
      setRoles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRoles();
  }, []);

  const openModal = (role = null) => {
    setEditingRole(role);
    if (role) {
      form.setFieldsValue({
        code: role.code,
        name: role.name,
        description: role.description,
      });
    } else {
      form.resetFields();
    }
    setModalVisible(true);
  };

  const closeModal = () => {
    setModalVisible(false);
    setEditingRole(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editingRole) {
        await rolesAPI.update(editingRole.id, values);
        message.success('Role updated successfully');
      } else {
        await rolesAPI.create(values);
        message.success('Role created successfully');
      }
      closeModal();
      fetchRoles();
    } catch (error) {
      if (error?.errorFields) {
        return;
      }
      message.error(error.response?.data?.message || 'Failed to save role');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (roleId) => {
    try {
      await rolesAPI.delete(roleId);
      message.success('Role deleted successfully');
      fetchRoles();
    } catch (error) {
      message.error('Failed to delete role');
      console.error('Failed to delete role:', error);
    }
  };

  const columns = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      render: (text) => <Tag color="purple">{text || 'N/A'}</Tag>,
    },
    {
      title: 'Role Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description',
      render: (text) => text || <span style={{ color: '#999' }}>No description provided</span>,
    },
    // {
    //   title: 'Actions',
    //   key: 'actions',
    //   render: (_, record) => (
    //     <Space size="small">
    //       <Button
    //         type="link"
    //         icon={<EditOutlined />}
    //         onClick={() => openModal(record)}
    //       >
    //         Edit
    //       </Button>
    //       <Popconfirm
    //         title="Are you sure you want to delete this role?"
    //         onConfirm={() => handleDelete(record.id)}
    //         okText="Yes"
    //         cancelText="No"
    //       >
    //         <Button type="link" danger icon={<DeleteOutlined />}>Delete</Button>
    //       </Popconfirm>
    //     </Space>
    //   ),
    // },
  ];

  return (
    <div className="role-management">
      <Card bordered={false}>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={3} style={{ margin: 0 }}>Roles Overview</Title>
              <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 4 }}>
                View all roles available in the Gas Transportation System.
              </Paragraph>
            </div>
            {/* <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => openModal()}
            >
              Add Role
            </Button> */}
          </div>

          <Table
            columns={columns}
            dataSource={Array.isArray(roles) ? roles : []}
            rowKey="id"
            loading={loading}
            pagination={{
              defaultPageSize: 10,
              showSizeChanger: true,
              pageSizeOptions: ['10', '20', '50', '100'],
              showTotal: (total) => `Total ${total} roles`,
            }}
          />
        </Space>
      </Card>

      <Modal
        title={editingRole ? 'Edit Role' : 'Create Role'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={closeModal}
        confirmLoading={submitting}
        width={520}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="code"
            label="Role Code"
            rules={[{ required: true, message: 'Please enter a unique role code' }]}
          >
            <Input placeholder="e.g. ADMIN" />
          </Form.Item>

          <Form.Item
            name="name"
            label="Role Name"
            rules={[{ required: true, message: 'Please enter the role name' }]}
          >
            <Input placeholder="Role name" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={4} placeholder="Describe the responsibilities of this role" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default RoleManagement;
