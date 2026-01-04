import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Space, Alert } from 'antd';
import { LockOutlined, SafetyOutlined } from '@ant-design/icons';
import { authAPI } from '../services/api';
import './Login.css';

const { Title, Text } = Typography;

const ResetPassword = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const forced = location.state?.forced;

  const onFinish = async (values) => {
    setLoading(true);
    setError('');
    
    try {
      await authAPI.changePassword({
        new_password: values.newPassword,
        mpin: values.mpin
      });
      
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 16px' }}>
        <Card className="login-card" bordered={false}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div className="login-header">
              <Title level={2} style={{ margin: 0, color: '#2563EB' }}>
                {forced ? 'Reset Required' : 'Reset Password'}
              </Title>
              <Text type="secondary">
                {forced ? 'Please set a new password and MPIN' : 'Create new password and MPIN'}
              </Text>
            </div>

            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                closable
                onClose={() => setError('')}
              />
            )}

            <Form
              name="reset-password"
              onFinish={onFinish}
              layout="vertical"
              size="large"
              requiredMark={false}
            >
              <Form.Item
                name="newPassword"
                label="New Password"
                rules={[
                  { required: true, message: 'Please input your new password!' },
                  { min: 6, message: 'Password must be at least 6 characters!' }
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="New Password"
                />
              </Form.Item>

              <Form.Item
                name="confirmPassword"
                label="Confirm Password"
                dependencies={['newPassword']}
                rules={[
                  { required: true, message: 'Please confirm your password!' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('newPassword') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('Passwords do not match!'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Confirm Password"
                />
              </Form.Item>

              <Form.Item
                name="mpin"
                label="Set 4-Digit MPIN"
                rules={[
                  { required: true, message: 'Please set your MPIN!' },
                  { len: 4, message: 'MPIN must be exactly 4 digits!' },
                  { pattern: /^\d+$/, message: 'MPIN must contain only numbers!' }
                ]}
              >
                <Input.Password
                  prefix={<SafetyOutlined />}
                  placeholder="4-Digit MPIN"
                  maxLength={4}
                />
              </Form.Item>

              <Form.Item
                name="confirmMpin"
                label="Confirm MPIN"
                dependencies={['mpin']}
                rules={[
                  { required: true, message: 'Please confirm your MPIN!' },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      if (!value || getFieldValue('mpin') === value) {
                        return Promise.resolve();
                      }
                      return Promise.reject(new Error('MPINs do not match!'));
                    },
                  }),
                ]}
              >
                <Input.Password
                  prefix={<SafetyOutlined />}
                  placeholder="Confirm MPIN"
                  maxLength={4}
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 0, marginTop: '24px' }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                >
                  Reset Password & Set MPIN
                </Button>
              </Form.Item>
            </Form>
          </Space>
        </Card>
      </div>
    </div>
  );
};

export default ResetPassword;
