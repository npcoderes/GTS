import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Space, Alert, Tabs } from 'antd';
import { UserOutlined, LockOutlined, LoginOutlined, SafetyOutlined } from '@ant-design/icons';
import { useAuth } from '../context/AuthContext';
import './Login.css';

const { Title, Text } = Typography;

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('password');
  const { login } = useAuth();
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    setError('');
    
    // Prepare payload based on active tab
    const payload = {
      username: values.username,
      ...(activeTab === 'password' ? { password: values.password } : { mpin: values.mpin })
    };
    
    const result = await login(payload);
    setLoading(false);
    
    if (result.success) {
      // Check if password reset or MPIN setup is required
      if (result.reset_required) {
        navigate('/reset-password', { state: { forced: true } });
      } else if (result.mpin_required) {
        navigate('/setup-mpin', { state: { forced: true } });
      } else {
        navigate('/dashboard');
      }
    } else {
      setError(`Invalid credentials. Please try again.`);
    }
  };

  return (
    <div className="login-container">
      <div style={{ width: '100%', maxWidth: '400px', padding: '0 16px' }}>
        <Card className="login-card" bordered={false}>
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div className="login-header">
              <Title level={2} className="login-title" style={{ margin: 0 }}>
                GTS
              </Title>
              <Text className="login-subtitle">Gas Transportation System</Text>
            </div>

            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                closable
                onClose={() => setError('')}
                style={{ marginBottom: '0' }}
              />
            )}

            <Tabs 
              activeKey={activeTab} 
              onChange={(key) => {
                setActiveTab(key);
                setError('');
              }}
              centered
              items={[
                {
                  key: 'password',
                  label: (
                    <span>
                      <LockOutlined /> Password
                    </span>
                  ),
                  children: (
                    <Form
                      name="password-login"
                      onFinish={onFinish}
                      layout="vertical"
                      size="large"
                      requiredMark={false}
                    >
                      <Form.Item
                        name="username"
                        rules={[
                          { required: true, message: 'Please input your email or phone!' }
                        ]}
                      >
                        <Input
                          prefix={<UserOutlined />}
                          placeholder="Email or Phone"
                          autoComplete="username"
                        />
                      </Form.Item>

                      <Form.Item
                        name="password"
                        rules={[{ required: true, message: 'Please input your password!' }]}
                      >
                        <Input.Password
                          prefix={<LockOutlined />}
                          placeholder="Password"
                          autoComplete="current-password"
                        />
                      </Form.Item>

                      <div style={{ textAlign: 'right', marginBottom: '16px' }}>
                        <Button 
                          type="link" 
                          size="small" 
                          className="login-link"
                          onClick={() => navigate('/forgot-password')}
                        >
                          Forgot password?
                        </Button>
                      </div>

                      <Form.Item style={{ marginBottom: 0 }}>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={loading}
                          block
                          icon={<LoginOutlined />}
                        >
                          Sign In
                        </Button>
                      </Form.Item>
                    </Form>
                  )
                },
                {
                  key: 'mpin',
                  label: (
                    <span>
                      <SafetyOutlined /> MPIN
                    </span>
                  ),
                  children: (
                    <Form
                      name="mpin-login"
                      onFinish={onFinish}
                      layout="vertical"
                      size="large"
                      requiredMark={false}
                    >
                      <Form.Item
                        name="username"
                        rules={[
                          { required: true, message: 'Please input your email or phone!' }
                        ]}
                      >
                        <Input
                          prefix={<UserOutlined />}
                          placeholder="Email or Phone"
                          autoComplete="username"
                        />
                      </Form.Item>

                      <Form.Item
                        name="mpin"
                        rules={[
                          { required: true, message: 'Please input your MPIN!' },
                          { len: 4, message: 'MPIN must be 4 digits!' }
                        ]}
                      >
                        <Input.Password
                          prefix={<SafetyOutlined />}
                          placeholder="4-Digit MPIN"
                          maxLength={4}
                          autoComplete="off"
                        />
                      </Form.Item>

                      <Form.Item style={{ marginBottom: 0, marginTop: '40px' }}>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={loading}
                          block
                          icon={<LoginOutlined />}
                        >
                          Sign In
                        </Button>
                      </Form.Item>
                    </Form>
                  )
                }
              ]}
            />

            <div className="login-footer">
              <Text type="secondary" style={{ fontSize: '12px' }}>
                © 2025 GTS. All rights reserved.
              </Text>
            </div>
          </Space>
        </Card>
      </div>
    </div>
  );
};

export default Login;