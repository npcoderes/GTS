import React, { useState } from 'react';
import { Card, Form, Input, Button, message, Divider, Typography, Space, Tag } from 'antd';
import { UserOutlined, LockOutlined, PhoneOutlined, MailOutlined, KeyOutlined } from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import apiClient from '../services/api';

const { Title, Text } = Typography;

const Profile = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const handleChangePassword = async (values) => {
    setLoading(true);
    try {
      await apiClient.post('/auth/change-password/', {
        old_password: values.old_password,
        new_password: values.new_password,
        mpin: values.mpin
      });
      message.success('Password and MPIN updated successfully!');
      form.resetFields();
    } catch (error) {
      message.error(error.response?.data?.message || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={3}>
              <UserOutlined /> Profile
            </Title>
            <Text type="secondary">Manage your account settings</Text>
          </div>

          <Divider />

          {/* User Info */}
          <div>
            <Title level={5}>Account Information</Title>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary"><MailOutlined /> Email:</Text>
                <Text strong>{user?.email || 'N/A'}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary"><UserOutlined /> Name:</Text>
                <Text strong>{user?.name || user?.full_name || 'N/A'}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text type="secondary"><KeyOutlined /> Role:</Text>
                <Tag color="blue">{user?.role || 'N/A'}</Tag>
              </div>
            </Space>
          </div>

          <Divider />

          {/* Change Password Form */}
          <div>
            <Title level={5}>Change Password & MPIN</Title>
            <Form
              form={form}
              layout="vertical"
              onFinish={handleChangePassword}
              autoComplete="off"
            >
              <Form.Item
                name="old_password"
                label="Current Password"
                rules={[{ required: true, message: 'Please enter current password' }]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Current password" />
              </Form.Item>

              <Form.Item
                name="new_password"
                label="New Password"
                rules={[
                  { required: true, message: 'Please enter new password' },
                  { min: 6, message: 'Password must be at least 6 characters' }
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="New password" />
              </Form.Item>

              <Form.Item
                name="confirm_password"
                label="Confirm New Password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Please confirm new password' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('new_password') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Passwords do not match'));
                    },
                  }),
                ]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Confirm new password" />
              </Form.Item>

              <Form.Item
                name="mpin"
                label="New MPIN (4 digits)"
                rules={[
                  { required: true, message: 'Please enter MPIN' },
                  { pattern: /^\d{4}$/, message: 'MPIN must be 4 digits' }
                ]}
              >
                <Input.Password
                  prefix={<PhoneOutlined />}
                  placeholder="4-digit MPIN"
                  maxLength={4}
                />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  Update Password & MPIN
                </Button>
              </Form.Item>
            </Form>
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default Profile;
