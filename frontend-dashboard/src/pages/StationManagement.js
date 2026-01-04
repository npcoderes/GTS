import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Table, Card, Button, Modal, Form, Input, Select, InputNumber, message, Tag, Space, Typography, Tooltip, Badge } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, BankOutlined, NodeIndexOutlined, EnvironmentOutlined, LinkOutlined, CloudSyncOutlined, ReloadOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

const { Option } = Select;
const { Title, Text } = Typography;

// Check if in development mode (controlled via REACT_APP_DEV_MODE env variable)
const isDevelopment = process.env.REACT_APP_DEV_MODE === 'true';

// Helper function to convert text to Pascal Case
const toPascalCase = (str) => {
    if (!str) return 'N/A';
    return str
        .toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};

const StationManagement = () => {
    const [stations, setStations] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingStation, setEditingStation] = useState(null);
    const [viewMode, setViewMode] = useState('all'); // 'all', 'ms', 'dbs'
    const [linkedDbsModalVisible, setLinkedDbsModalVisible] = useState(false);
    const [selectedMsStation, setSelectedMsStation] = useState(null);
    // const [syncLoading, setSyncLoading] = useState(false); // Commented - SAP sync now automatic in backend
    const [form] = Form.useForm();

    useEffect(() => {
        fetchStations();
    }, []);

    const fetchStations = async () => {
        setLoading(true);
        try {
            const response = await apiClient.get('/stations/');
            setStations(response.data.results || response.data);
        } catch (error) {
            message.error('Failed to fetch stations');
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingStation(null);
        form.resetFields();
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingStation(record);
        form.setFieldsValue(record);
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        try {
            message.warning('Delete not implemented in backend yet');
        } catch (error) {
            message.error('Failed to delete station');
        }
    };

    // const syncStationsFromSAP = async () => {
    //     setSyncLoading(true);
    //     try {
    //         const response = await apiClient.post('/sap/sync-stations/');
    //         if (response.data.success) {
    //             const summary = response.data.summary || 'Completed';
    //             message.success(`SAP Import: ${summary}`, 4);
    //             fetchStations();
    //         } else {
    //             message.error(response.data.error || 'Import failed');
    //         }
    //     } catch (error) {
    //         message.error('SAP import failed');
    //     } finally {
    //         setSyncLoading(false);
    //     }
    // };

    const showSyncModal = () => {
        Modal.confirm({
            title: 'Import Stations from SAP',
            icon: <CloudSyncOutlined />,
            content: 'This will import all stations from SAP. Continue?',
            // onOk: syncStationsFromSAP,
            okText: 'Import Now',
        });
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            if (editingStation) {
                await apiClient.put(`/stations/${editingStation.id}/`, values);
                message.success('Station updated successfully');
            } else {
                await apiClient.post('/stations/', values);
                message.success('Station created successfully');
            }
            setIsModalVisible(false);
            fetchStations();
        } catch (error) {
            message.error(error.response?.data?.message || 'Operation failed');
        }
    };

    const getLinkedDbsCount = useCallback((msId) => {
        return stations.filter(s => s.type === 'DBS' && s.parent_station === msId).length;
    }, [stations]);

    const getLinkedDbsStations = useCallback((msId) => {
        return stations.filter(s => s.type === 'DBS' && s.parent_station === msId);
    }, [stations]);

    const handleShowLinkedDbs = useCallback((msStation) => {
        setSelectedMsStation(msStation);
        setLinkedDbsModalVisible(true);
    }, []);

    const getParentMsName = useCallback((parentId) => {
        const parent = stations.find(s => s.id === parentId);
        return parent ? parent.name : 'N/A';
    }, [stations]);

    const filteredStations = useMemo(() => {
        return stations.filter(s => {
            if (viewMode === 'all') return true;
            return s.type === viewMode.toUpperCase();
        });
    }, [stations, viewMode]);

    const msStations = useMemo(() => stations.filter(s => s.type === 'MS'), [stations]);
    const dbsStations = useMemo(() => stations.filter(s => s.type === 'DBS'), [stations]);

    const columns = [
        {
            title: 'Station',
            key: 'station',
            render: (_, record) => (
                <Space>
                    {record.type === 'MS' ? (
                        <div style={{
                            width: 40,
                            height: 40,
                            borderRadius: 10,
                            background: '#2563EB',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <BankOutlined style={{ color: '#fff', fontSize: 18 }} />
                        </div>
                    ) : (
                        <div style={{
                            width: 40,
                            height: 40,
                            borderRadius: 10,
                            background: '#13c2c2',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <NodeIndexOutlined style={{ color: '#fff', fontSize: 18 }} />
                        </div>
                    )}
                    <div>
                        <Text strong style={{ fontSize: 15 }}>{toPascalCase(record.name)}</Text>
                        <br />
                        <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase' }}>{record.code}</Text>
                    </div>
                </Space>
            ),
        },
        {
            title: 'Type',
            dataIndex: 'type',
            key: 'type',
            render: (type) => (
                <Tag
                    color={type === 'MS' ? '#2563EB' : '#13c2c2'}
                    style={{
                        borderRadius: 12,
                        padding: '4px 16px',
                        fontWeight: 600,
                        fontSize: 13
                    }}
                >
                    {type === 'MS' ? 'MS' : 'DBS'}
                </Tag>
            ),
        },
        {
            title: 'Location',
            dataIndex: 'city',
            key: 'city',
            render: (city, record) => (
                <Space>
                    <EnvironmentOutlined style={{ color: '#52c41a' }} />
                    <Text>{toPascalCase(city || record.address)}</Text>
                </Space>
            )
        },
        {
            title: 'Linked Stations',
            key: 'linked',
            render: (_, record) => {
                if (record.type === 'MS') {
                    const count = getLinkedDbsCount(record.id);
                    return (
                        <Tooltip title={count > 0 ? "Click to view linked DBS stations" : "No linked DBS stations"}>
                            <Badge
                                count={count}
                                style={{
                                    backgroundColor: count > 0 ? '#2563EB' : '#d9d9d9',
                                }}
                                showZero
                            >
                                <Tag 
                                    color="purple" 
                                    style={{ 
                                        borderRadius: 8, 
                                        padding: '2px 12px',
                                        cursor: count > 0 ? 'pointer' : 'default'
                                    }}
                                    onClick={() => count > 0 && handleShowLinkedDbs(record)}
                                >
                                    <LinkOutlined /> {count} DBS Linked
                                </Tag>
                            </Badge>
                        </Tooltip>
                    );
                } else {
                    return (
                        <Tooltip title="Parent Mother Station">
                            <Tag color="blue" style={{ borderRadius: 8 }}>
                                <BankOutlined /> {toPascalCase(getParentMsName(record.parent_station))}
                            </Tag>
                        </Tooltip>
                    );
                }
            }
        },
        // Only show actions column in development mode
        ...(isDevelopment ? [{
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space>
                    <Tooltip title="Edit">
                        <Button
                            icon={<EditOutlined />}
                            onClick={() => handleEdit(record)}
                            style={{ borderRadius: 8 }}
                        />
                    </Tooltip>
                    <Tooltip title="Delete">
                        <Button
                            icon={<DeleteOutlined />}
                            danger
                            onClick={() => handleDelete(record.id)}
                            style={{ borderRadius: 8 }}
                        />
                    </Tooltip>
                </Space>
            ),
        }] : []),
    ];

    return (
        <div className="station-management" style={{ padding: 24 }}>
            {/* Summary Cards */}
            <div style={{ marginBottom: 24, display: 'flex', gap: 16 }}>
                <Card
                    hoverable
                    onClick={() => setViewMode('all')}
                    style={{
                        flex: 1,
                        borderRadius: 12,
                        border: viewMode === 'all' ? '2px solid #2563EB' : '1px solid #f0f0f0',
                        cursor: 'pointer'
                    }}
                    bodyStyle={{ padding: 20 }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text type="secondary">All Stations</Text>
                            <div style={{ fontSize: 28, fontWeight: 700, color: '#1a1a2e' }}>
                                {stations.length}
                            </div>
                        </div>
                        <div style={{
                            width: 48,
                            height: 48,
                            borderRadius: 12,
                            background: '#f0f0f0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <EnvironmentOutlined style={{ fontSize: 24, color: '#666' }} />
                        </div>
                    </div>
                </Card>

                <Card
                    hoverable
                    onClick={() => setViewMode('ms')}
                    style={{
                        flex: 1,
                        borderRadius: 12,
                        border: viewMode === 'ms' ? '2px solid #2563EB' : '1px solid #f0f0f0',
                        cursor: 'pointer'
                    }}
                    bodyStyle={{ padding: 20 }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text type="secondary">Mother Stations</Text>
                            <div style={{ fontSize: 28, fontWeight: 700, color: '#2563EB' }}>
                                {msStations.length}
                            </div>
                        </div>
                        <div style={{
                            width: 48,
                            height: 48,
                            borderRadius: 12,
                            background: 'rgba(37, 99, 235, 0.08)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <BankOutlined style={{ fontSize: 24, color: '#2563EB' }} />
                        </div>
                    </div>
                </Card>

                <Card
                    hoverable
                    onClick={() => setViewMode('dbs')}
                    style={{
                        flex: 1,
                        borderRadius: 12,
                        border: viewMode === 'dbs' ? '2px solid #13c2c2' : '1px solid #f0f0f0',
                        cursor: 'pointer'
                    }}
                    bodyStyle={{ padding: 20 }}
                >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                            <Text type="secondary">DBS Stations</Text>
                            <div style={{ fontSize: 28, fontWeight: 700, color: '#13c2c2' }}>
                                {dbsStations.length}
                            </div>
                        </div>
                        <div style={{
                            width: 48,
                            height: 48,
                            borderRadius: 12,
                            background: 'rgba(19, 194, 194, 0.08)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <NodeIndexOutlined style={{ fontSize: 24, color: '#13c2c2' }} />
                        </div>
                    </div>
                </Card>
            </div>

            {/* Main Table Card */}
            <Card
                bordered={false}
                style={{ borderRadius: 12, boxShadow: '0 2px 12px rgba(0,0,0,0.06)' }}
            >
                <div style={{
                    marginBottom: 24,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div>
                        <Title level={3} style={{ margin: 0, color: '#1a1a2e' }}>
                            Station Management
                        </Title>
                        <Text type="secondary">Overview of all Mother Stations (MS) and Daughter Booster Stations (DBS)</Text>
                    </div>
                    <Space>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={fetchStations}
                            loading={loading}
                            size="large"
                            style={{ borderRadius: 8, height: 44 }}
                        >
                            Refresh
                        </Button>
                        {/* Commented - SAP sync is now handled automatically in backend
                        <Button
                            icon={<CloudSyncOutlined />}
                            onClick={showSyncModal}
                            loading={syncLoading}
                            size="large"
                            style={{ borderRadius: 8, height: 44 }}
                        >
                            Sync from SAP
                        </Button>
                        */}
                        {isDevelopment && (
                            <Button
                                type="primary"
                                icon={<PlusOutlined />}
                                onClick={handleAdd}
                                size="large"
                                style={{
                                    borderRadius: 8,
                                    height: 44,
                                    paddingLeft: 24,
                                    paddingRight: 24,
                                }}
                            >
                                Add Station
                            </Button>
                        )}
                    </Space>
                </div>

                <Table
                    columns={columns}
                    dataSource={filteredStations}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        defaultPageSize: 10,
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                        showTotal: (total) => `Total ${total} stations`
                    }}
                />
            </Card>

            <Modal
                title={editingStation ? 'Edit Station' : 'Add New Station'}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                width={520}
                okText={editingStation ? 'Update Station' : 'Add Station'}
                destroyOnClose
            >
                <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                    <Form.Item
                        name="code"
                        label={<Text strong>Station Code</Text>}
                        rules={[{ required: true, message: 'Please enter station code' }]}
                    >
                        <Input size="large" placeholder="e.g., MS01 or DBS01" />
                    </Form.Item>
                    <Form.Item
                        name="name"
                        label={<Text strong>Station Name</Text>}
                        rules={[{ required: true, message: 'Please enter station name' }]}
                    >
                        <Input size="large" placeholder="e.g., Main Station Alpha" />
                    </Form.Item>
                    <Form.Item
                        name="type"
                        label={<Text strong>Station Type</Text>}
                        rules={[{ required: true, message: 'Please select type' }]}
                    >
                        <Select size="large" placeholder="Select station type">
                            <Option value="MS">
                                <Space>
                                    <BankOutlined style={{ color: '#2563EB' }} />
                                    Mother Station (MS)
                                </Space>
                            </Option>
                            <Option value="DBS">
                                <Space>
                                    <NodeIndexOutlined style={{ color: '#13c2c2' }} />
                                    Daughter Booster Station (DBS)
                                </Space>
                            </Option>
                        </Select>
                    </Form.Item>
                    <Form.Item name="city" label={<Text strong>City</Text>}>
                        <Input size="large" placeholder="e.g., Mumbai" />
                    </Form.Item>
                    <Form.Item name="address" label={<Text strong>Address</Text>}>
                        <Input.TextArea rows={2} placeholder="Full address..." />
                    </Form.Item>
                    <div style={{ display: 'flex', gap: 16 }}>
                        <Form.Item name="lat" label={<Text strong>Latitude</Text>} style={{ flex: 1 }}>
                            <InputNumber style={{ width: '100%' }} size="large" placeholder="e.g., 19.0760" />
                        </Form.Item>
                        <Form.Item name="lng" label={<Text strong>Longitude</Text>} style={{ flex: 1 }}>
                            <InputNumber style={{ width: '100%' }} size="large" placeholder="e.g., 72.8777" />
                        </Form.Item>
                    </div>
                    <Form.Item
                        noStyle
                        shouldUpdate={(prevValues, currentValues) => prevValues.type !== currentValues.type}
                    >
                        {({ getFieldValue }) =>
                            getFieldValue('type') === 'DBS' ? (
                                <Form.Item
                                    name="parent_station"
                                    label={<Text strong>Parent Mother Station</Text>}
                                    rules={[{ required: true, message: 'Please select parent station' }]}
                                >
                                    <Select size="large" placeholder="Select parent MS">
                                        {msStations.map(ms => (
                                            <Option key={ms.id} value={ms.id}>
                                                <Space>
                                                    <BankOutlined style={{ color: '#2563EB' }} />
                                                    {ms.name} ({ms.code})
                                                </Space>
                                            </Option>
                                        ))}
                                    </Select>
                                </Form.Item>
                            ) : null
                        }
                    </Form.Item>
                </Form>
            </Modal>

            {/* Linked DBS Stations Modal */}
            <Modal
                title="Linked DBS Stations"
                open={linkedDbsModalVisible}
                onCancel={() => {
                    setLinkedDbsModalVisible(false);
                    setSelectedMsStation(null);
                }}
                destroyOnClose
                footer={[
                    <Button 
                        key="close" 
                        onClick={() => {
                            setLinkedDbsModalVisible(false);
                            setSelectedMsStation(null);
                        }}
                    >
                        Close
                    </Button>
                ]}
                width={600}
            >
                {selectedMsStation && (
                    <div style={{ marginTop: 16 }}>
                        {getLinkedDbsStations(selectedMsStation.id).length > 0 ? (
                            <Table
                                dataSource={getLinkedDbsStations(selectedMsStation.id)}
                                rowKey="id"
                                pagination={false}
                                size="small"
                                columns={[
                                    {
                                        title: 'Station Code',
                                        dataIndex: 'code',
                                        key: 'code',
                                        render: (code) => (
                                            <Tag color="cyan" style={{ borderRadius: 6 }}>
                                                {code}
                                            </Tag>
                                        )
                                    },
                                    {
                                        title: 'Station Name',
                                        dataIndex: 'name',
                                        key: 'name',
                                        render: (name) => (
                                            <Space>
                                                <NodeIndexOutlined style={{ color: '#13c2c2' }} />
                                                <Text strong>{toPascalCase(name)}</Text>
                                            </Space>
                                        )
                                    },
                                    {
                                        title: 'Location',
                                        dataIndex: 'city',
                                        key: 'city',
                                        render: (city, record) => (
                                            <Space>
                                                <EnvironmentOutlined style={{ color: '#52c41a' }} />
                                                <Text>{toPascalCase(city || record.address || 'N/A')}</Text>
                                            </Space>
                                        )
                                    }
                                ]}
                            />
                        ) : (
                            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                                <NodeIndexOutlined style={{ fontSize: 48, marginBottom: 16, opacity: 0.5 }} />
                                <div>No DBS stations linked to this Mother Station</div>
                            </div>
                        )}
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default StationManagement;
