import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Space, Alert } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import { authAPI } from '../services/api';
import './Login.css';

const { Title, Text } = Typography;

const SetupMPIN = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const onFinish = async (values) => {
    setLoading(true);
    setError('');
    
    try {
      await authAPI.setMPIN({
        mpin: values.mpin
      });
      
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to set MPIN');
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
                Setup MPIN
              </Title>
              <Text type="secondary">
                Please set a 4-digit MPIN for quick login
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
              name="setup-mpin"
              onFinish={onFinish}
              layout="vertical"
              size="large"
              requiredMark={false}
            >
              <Form.Item
                name="mpin"
                label="4-Digit MPIN"
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
                  Set MPIN
                </Button>
              </Form.Item>

              <div style={{ textAlign: 'center', marginTop: '16px' }}>
                <Button 
                  type="link" 
                  onClick={() => navigate('/dashboard')}
                >
                  Skip for now
                </Button>
              </div>
            </Form>
          </Space>
        </Card>
      </div>
    </div>
  );
};

export default SetupMPIN;
