import React, { useState } from 'react';
import { Card, Button, Space, Typography, Row, Col, message, Modal, Select, Switch, Alert, Divider } from 'antd';
import { SyncOutlined, DatabaseOutlined, UserOutlined, CloudSyncOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

const { Title, Text } = Typography;
const { Option } = Select;

const SAPSyncManagement = () => {
  const [loading, setLoading] = useState({
    stations: false,
    users: false,
  });

  const syncStationsFromSAP = async (stationType = null, updateExisting = false) => {
    setLoading(prev => ({ ...prev, stations: true }));
    try {
      const params = new URLSearchParams();
      if (stationType) params.append('station_type', stationType);
      if (updateExisting) params.append('update_existing', 'true');
      
      const response = await apiClient.post(`/sap/sync-stations/?${params.toString()}`);
      
      if (response.data.success) {
        message.success(`Stations synced successfully! ${response.data.summary || ''}`);
      } else {
        message.error(response.data.error || 'Failed to sync stations');
      }
    } catch (error) {
      message.error(error.response?.data?.error || 'Failed to sync stations from SAP');
    } finally {
      setLoading(prev => ({ ...prev, stations: false }));
    }
  };

  const syncUsersToSAP = async (activeOnly = true) => {
    setLoading(prev => ({ ...prev, users: true }));
    try {
      const params = new URLSearchParams();
      if (activeOnly) params.append('active_only', 'true');
      
      const response = await apiClient.post(`/sap/sync-users/?${params.toString()}`);
      
      if (response.data.success) {
        message.success(`Users synced successfully! ${response.data.summary || ''}`);
      } else {
        message.error(response.data.error || 'Failed to sync users');
      }
    } catch (error) {
      message.error(error.response?.data?.error || 'Failed to sync users to SAP');
    } finally {
      setLoading(prev => ({ ...prev, users: false }));
    }
  };

  const showStationSyncModal = () => {
    let stationType = null;
    let updateExisting = false;

    Modal.confirm({
      title: 'Sync Stations from SAP',
      icon: <DatabaseOutlined />,
      content: (
        <div style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Text strong>Station Type:</Text>
              <Select
                style={{ width: '100%', marginTop: 8 }}
                placeholder="Select station type (optional)"
                allowClear
                onChange={(value) => { stationType = value; }}
              >
                <Option value="MS">Mother Stations (MS)</Option>
                <Option value="DB">Daughter Stations (DBS)</Option>
              </Select>
            </div>
            <div>
              <Space>
                <Switch onChange={(checked) => { updateExisting = checked; }} />
                <Text>Update existing stations</Text>
              </Space>
            </div>
          </Space>
        </div>
      ),
      onOk: () => syncStationsFromSAP(stationType, updateExisting),
      okText: 'Sync Stations',
      cancelText: 'Cancel',
    });
  };

  const showUserSyncModal = () => {
    let activeOnly = true;

    Modal.confirm({
      title: 'Sync Users to SAP',
      icon: <UserOutlined />,
      content: (
        <div style={{ marginTop: 16 }}>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Alert
              message="This will sync all users to SAP system"
              type="info"
              showIcon
            />
            <div>
              <Space>
                <Switch defaultChecked onChange={(checked) => { activeOnly = checked; }} />
                <Text>Sync active users only</Text>
              </Space>
            </div>
          </Space>
        </div>
      ),
      onOk: () => syncUsersToSAP(activeOnly),
      okText: 'Sync Users',
      cancelText: 'Cancel',
    });
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>
        <CloudSyncOutlined /> SAP Sync Management
      </Title>
      <Text type="secondary">
        Manage synchronization between the application and SAP system
      </Text>

      <Row gutter={[24, 24]} style={{ marginTop: 24 }}>
        {/* Station Sync */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>Station Synchronization</span>
              </Space>
            }
            bordered={false}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>Import stations from SAP into the local database</Text>
              
              <Divider />
              
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  icon={<SyncOutlined />}
                  loading={loading.stations}
                  onClick={showStationSyncModal}
                  block
                >
                  Sync All Stations from SAP
                </Button>
                
                <Space style={{ width: '100%' }}>
                  <Button
                    icon={<SyncOutlined />}
                    loading={loading.stations}
                    onClick={() => syncStationsFromSAP('MS')}
                  >
                    Sync MS Only
                  </Button>
                  <Button
                    icon={<SyncOutlined />}
                    loading={loading.stations}
                    onClick={() => syncStationsFromSAP('DB')}
                  >
                    Sync DBS Only
                  </Button>
                </Space>
              </Space>

              <Alert
                message="Station sync will import new stations and optionally update existing ones"
                type="info"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Space>
          </Card>
        </Col>

        {/* User Sync */}
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <UserOutlined />
                <span>User Synchronization</span>
              </Space>
            }
            bordered={false}
          >
            <Space direction="vertical" style={{ width: '100%' }}>
              <Text>Sync users from local database to SAP system</Text>
              
              <Divider />
              
              <Space direction="vertical" style={{ width: '100%' }}>
                <Button
                  type="primary"
                  icon={<SyncOutlined />}
                  loading={loading.users}
                  onClick={showUserSyncModal}
                  block
                >
                  Sync Users to SAP
                </Button>
                
                <Button
                  icon={<SyncOutlined />}
                  loading={loading.users}
                  onClick={() => syncUsersToSAP(true)}
                >
                  Sync Active Users Only
                </Button>
              </Space>

              <Alert
                message="User sync will create/update user records in SAP"
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Instructions */}
      <Card title="Sync Instructions" style={{ marginTop: 24 }}>
        <Row gutter={[24, 16]}>
          <Col xs={24} md={12}>
            <Title level={5}>Station Sync (SAP → Local)</Title>
            <ul>
              <li>Imports station data from SAP system</li>
              <li>Creates new stations in local database</li>
              <li>Can update existing stations if enabled</li>
              <li>Supports filtering by station type (MS/DBS)</li>
            </ul>
          </Col>
          <Col xs={24} md={12}>
            <Title level={5}>User Sync (Local → SAP)</Title>
            <ul>
              <li>Sends user data to SAP system</li>
              <li>Creates user accounts in SAP</li>
              <li>Includes role and station assignments</li>
              <li>Can filter to active users only</li>
            </ul>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default SAPSyncManagement;