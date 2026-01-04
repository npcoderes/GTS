import React, { useState } from 'react';
import { Card, Form, Input, Button, message, Steps, Typography, Space } from 'antd';
import { MailOutlined, SafetyOutlined, LockOutlined, PhoneOutlined, CheckCircleFilled } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/api';
import './ForgotPassword.css';

const { Title, Text } = Typography;
const { Step } = Steps;

const ForgotPassword = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [username, setUsername] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [form] = Form.useForm();

  // Step 1: Request OTP
  const handleRequestOTP = async (values) => {
    setLoading(true);
    try {
      await apiClient.post('/auth/forgot-password/request/', {
        username: values.username
      });
      setUsername(values.username);
      message.success('OTP sent to your registered email');
      setCurrentStep(1);
    } catch (error) {
      message.error(error.response?.data?.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOTP = async (values) => {
    setLoading(true);
    try {
      const response = await apiClient.post('/auth/forgot-password/verify/', {
        username: username,
        otp: values.otp
      });
      setResetToken(response.data.reset_token);
      message.success('OTP verified successfully');
      setCurrentStep(2);
    } catch (error) {
      message.error(error.response?.data?.message || 'Invalid or expired OTP');
    } finally {
      setLoading(false);
    }
  };

  // Step 3: Reset Password
  const handleResetPassword = async (values) => {
    setLoading(true);
    try {
      await apiClient.post('/auth/forgot-password/confirm/', {
        reset_token: resetToken,
        new_password: values.new_password,
        mpin: values.mpin
      });
      message.success('Password reset successfully! Please login.');
      setTimeout(() => navigate('/login'), 2000);
    } catch (error) {
      message.error(error.response?.data?.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  };

  const getStepIcon = (index) => {
    if (index < currentStep) return <CheckCircleFilled />;
    if (index === 0) return <MailOutlined />;
    if (index === 1) return <SafetyOutlined />;
    return <LockOutlined />;
  };

  const steps = [
    { title: 'Request OTP' },
    { title: 'Verify OTP' },
    { title: 'Reset Password' }
  ];

  return (
    <div className="forgot-password-container">
      <Card className="forgot-password-card" bordered={false}>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div className="forgot-password-header">
            <Title level={3} className="forgot-password-title" style={{ margin: 0 }}>Forgot Password</Title>
            <Text className="forgot-password-subtitle">Reset your password in 3 simple steps</Text>
          </div>

          <Steps current={currentStep} size="small">
            {steps.map((step, index) => (
              <Step 
                key={index} 
                title={step.title} 
                icon={getStepIcon(index)}
                status={index < currentStep ? 'finish' : index === currentStep ? 'process' : 'wait'}
              />
            ))}
          </Steps>

          {/* Step 1: Request OTP */}
          {currentStep === 0 && (
            <Form form={form} layout="vertical" onFinish={handleRequestOTP}>
              <Form.Item
                name="username"
                label="Email or Phone"
                rules={[{ required: true, message: 'Please enter your email or phone' }]}
              >
                <Input
                  prefix={<MailOutlined />}
                  placeholder="Enter email or phone number"
                  size="large"
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block size="large">
                  Send OTP
                </Button>
              </Form.Item>
              <Button type="link" className="forgot-password-link" onClick={() => navigate('/login')} block>
                Back to Login
              </Button>
            </Form>
          )}

          {/* Step 2: Verify OTP */}
          {currentStep === 1 && (
            <Form form={form} layout="vertical" onFinish={handleVerifyOTP}>
              <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                Enter the 6-digit OTP sent to {username}
              </Text>
              <Form.Item
                name="otp"
                label="OTP Code"
                rules={[
                  { required: true, message: 'Please enter OTP' },
                  { pattern: /^\d{6}$/, message: 'OTP must be 6 digits' }
                ]}
              >
                <Input
                  prefix={<SafetyOutlined />}
                  placeholder="Enter 6-digit OTP"
                  maxLength={6}
                  size="large"
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block size="large">
                  Verify OTP
                </Button>
              </Form.Item>
              <Button type="link" className="forgot-password-link" onClick={() => setCurrentStep(0)} block>
                Resend OTP
              </Button>
            </Form>
          )}

          {/* Step 3: Reset Password */}
          {currentStep === 2 && (
            <Form form={form} layout="vertical" onFinish={handleResetPassword}>
              <Form.Item
                name="new_password"
                label="New Password"
                rules={[
                  { required: true, message: 'Please enter new password' },
                  { min: 6, message: 'Password must be at least 6 characters' }
                ]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="New password"
                  size="large"
                />
              </Form.Item>

              <Form.Item
                name="confirm_password"
                label="Confirm Password"
                dependencies={['new_password']}
                rules={[
                  { required: true, message: 'Please confirm password' },
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
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Confirm password"
                  size="large"
                />
              </Form.Item>

              <Form.Item
                name="mpin"
                label="Set MPIN (4 digits)"
                rules={[
                  { required: true, message: 'Please enter MPIN' },
                  { pattern: /^\d{4}$/, message: 'MPIN must be 4 digits' }
                ]}
              >
                <Input.Password
                  prefix={<PhoneOutlined />}
                  placeholder="4-digit MPIN"
                  maxLength={4}
                  size="large"
                />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block size="large">
                  Reset Password
                </Button>
              </Form.Item>
            </Form>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default ForgotPassword;
