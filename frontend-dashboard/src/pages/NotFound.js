import React from 'react';
import { Button, Typography } from 'antd';
import { HomeOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';

const { Title, Text } = Typography;

const NotFound = () => {
  const navigate = useNavigate();
  const { theme, isDark } = useTheme();

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: isDark 
          ? 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)' 
          : 'linear-gradient(135deg, #F8FAFC 0%, #E2E8F0 100%)',
        padding: 24,
      }}
    >
      <div
        style={{
          maxWidth: 480,
          width: '100%',
          textAlign: 'center',
        }}
      >
        {/* 404 Number */}
        <div style={{ marginBottom: 24 }}>
          <Title
            style={{
              fontSize: 120,
              fontWeight: 700,
              color: isDark ? '#4F46E5' : '#4F46E5',
              margin: 0,
              lineHeight: 1,
              letterSpacing: -4,
            }}
          >
            404
          </Title>
        </div>

        {/* Message */}
        <Title 
          level={3} 
          style={{ 
            marginBottom: 12, 
            color: isDark ? '#F1F5F9' : '#1E293B',
            fontWeight: 600,
          }}
        >
          Page Not Found
        </Title>
        
        <Text
          style={{
            fontSize: 16,
            color: isDark ? '#94A3B8' : '#64748B',
            display: 'block',
            marginBottom: 40,
            lineHeight: 1.6,
          }}
        >
          The page you're looking for doesn't exist or has been moved.
        </Text>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <Button
            type="primary"
            size="large"
            icon={<HomeOutlined />}
            onClick={() => navigate('/dashboard')}
            style={{
              height: 44,
              borderRadius: 8,
              fontWeight: 500,
              paddingLeft: 24,
              paddingRight: 24,
            }}
          >
            Dashboard
          </Button>
          <Button
            size="large"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(-1)}
            style={{
              height: 44,
              borderRadius: 8,
              fontWeight: 500,
              paddingLeft: 24,
              paddingRight: 24,
              background: isDark ? '#334155' : '#FFFFFF',
              color: isDark ? '#F1F5F9' : '#1E293B',
              borderColor: isDark ? '#475569' : '#E2E8F0',
            }}
          >
            Go Back
          </Button>
        </div>
      </div>
    </div>
  );
};

export default NotFound;
