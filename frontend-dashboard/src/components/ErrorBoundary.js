import React from 'react';
import { Button, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined, WarningOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { 
      hasError: false, 
      error: null, 
      errorInfo: null,
      errorId: null 
    };
  }

  static getDerivedStateFromError(error) {
    const errorId = `ERR-${Date.now().toString(36).toUpperCase()}`;
    return { hasError: true, errorId };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      const isDev = process.env.NODE_ENV === 'development';
      const isDark = document.body.classList.contains('theme-dark');

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
              maxWidth: 540,
              width: '100%',
              textAlign: 'center',
            }}
          >
            {/* Error Icon */}
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: isDark ? '#7C3AED' : '#6366F1',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 24px',
              }}
            >
              <WarningOutlined
                style={{
                  fontSize: 40,
                  color: '#fff',
                }}
              />
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
              Something Went Wrong
            </Title>
            
            <Text
              style={{
                fontSize: 16,
                color: isDark ? '#94A3B8' : '#64748B',
                display: 'block',
                marginBottom: 24,
                lineHeight: 1.6,
              }}
            >
              An unexpected error occurred. Please try reloading the page.
            </Text>

            {/* Error ID */}
            {this.state.errorId && (
              <div
                style={{
                  background: isDark ? 'rgba(239, 68, 68, 0.1)' : '#FEF2F2',
                  borderRadius: 6,
                  padding: '10px 16px',
                  marginBottom: 32,
                  display: 'inline-block',
                }}
              >
                <Text style={{ fontSize: 13, color: isDark ? '#94A3B8' : '#6B7280' }}>
                  Error ID:{' '}
                </Text>
                <Text 
                  strong 
                  style={{ 
                    color: isDark ? '#FCA5A5' : '#DC2626', 
                    fontFamily: 'monospace',
                    fontSize: 13,
                  }}
                >
                  {this.state.errorId}
                </Text>
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', marginBottom: 32 }}>
              <Button
                type="primary"
                size="large"
                icon={<ReloadOutlined />}
                onClick={this.handleReload}
                style={{
                  height: 44,
                  borderRadius: 8,
                  fontWeight: 500,
                  paddingLeft: 24,
                  paddingRight: 24,
                }}
              >
                Reload
              </Button>
              <Button
                size="large"
                icon={<HomeOutlined />}
                onClick={this.handleGoHome}
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
                Dashboard
              </Button>
            </div>

            {/* Technical Details (Development Only) */}
            {isDev && this.state.error && (
              <div
                style={{
                  textAlign: 'left',
                  background: isDark ? '#1E293B' : '#F8FAFC',
                  borderRadius: 8,
                  padding: 20,
                  border: isDark ? '1px solid #334155' : '1px solid #E2E8F0',
                }}
              >
                <div style={{ marginBottom: 12 }}>
                  <Text 
                    strong 
                    style={{ 
                      color: isDark ? '#FCA5A5' : '#DC2626',
                      fontSize: 13,
                    }}
                  >
                    Development Error Details
                  </Text>
                </div>
                <div
                  style={{
                    background: isDark ? '#0F172A' : '#FFFFFF',
                    borderRadius: 6,
                    padding: 12,
                    overflow: 'auto',
                    maxHeight: 200,
                    border: isDark ? '1px solid #1E293B' : '1px solid #E2E8F0',
                  }}
                >
                  <pre
                    style={{
                      margin: 0,
                      fontSize: 12,
                      color: isDark ? '#FCA5A5' : '#DC2626',
                      fontFamily: 'Monaco, Consolas, monospace',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {this.state.error.toString()}
                  </pre>
                  {this.state.errorInfo && (
                    <pre
                      style={{
                        margin: '12px 0 0',
                        fontSize: 11,
                        color: isDark ? '#64748B' : '#94A3B8',
                        fontFamily: 'Monaco, Consolas, monospace',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}
                    >
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
