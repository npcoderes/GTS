import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Select, message, DatePicker, TimePicker, Tag, Card, Radio, Space, Typography, Divider, Input } from 'antd';
import { PlusOutlined, CheckOutlined, CloseOutlined, CalendarOutlined, ClockCircleOutlined, EditOutlined } from '@ant-design/icons';
import apiClient from '../services/api';
import moment from 'moment';
import { useAuth } from '../context/AuthContext';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { Title, Text } = Typography;

const ShiftManagement = () => {
    const { user } = useAuth();
    const roleCode = (user?.role || '').toUpperCase();
    const canApproveReject = roleCode !== 'TRANSPORT_ADMIN';

    const [shifts, setShifts] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [drivers, setDrivers] = useState([]);
    const [vehicles, setVehicles] = useState([]);
    // const [scheduleType, setScheduleType] = useState('daily'); // Always daily now
    const [rejectModalVisible, setRejectModalVisible] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [rejectTarget, setRejectTarget] = useState(null);
    const [editingShift, setEditingShift] = useState(null);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchShifts();
        fetchDrivers();
        fetchVehicles();
    }, []);

    const fetchShifts = async () => {
        setLoading(true);
        try {
            const response = await apiClient.get('/shifts/');
            setShifts(response.data.results || response.data);
        } catch (error) {
            message.error('Failed to fetch shifts');
        } finally {
            setLoading(false);
        }
    };

    const fetchDrivers = async () => {
        try {
            const response = await apiClient.get('/drivers/');
            setDrivers(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to fetch drivers', error);
        }
    };

    const fetchVehicles = async () => {
        try {
            const response = await apiClient.get('/vehicles/');
            setVehicles(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to fetch vehicles', error);
        }
    };

    const handleAdd = () => {
        form.resetFields();
        setEditingShift(null);
        // setScheduleType('daily'); // Always daily
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingShift(record);
        // setScheduleType(record.is_recurring ? 'daily' : 'specific'); // Always daily
        
        // Always treat as daily/recurring
        form.setFieldsValue({
            driver: record.driver,
            vehicle: record.vehicle,
            dailyStartTime: moment(record.start_time),
            dailyEndTime: moment(record.end_time)
        });
        setIsModalVisible(true);
    };

    const handleDriverChange = (driverId) => {
        const driver = drivers.find(d => d.id === driverId);
        if (driver && driver.assigned_vehicle_details) {
            form.setFieldsValue({ vehicle: driver.assigned_vehicle_details.id });
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            
            // Always create daily/recurring shifts
            const today = moment();
            const startTime = values.dailyStartTime;
            const endTime = values.dailyEndTime;

            const payload = {
                driver: values.driver,
                vehicle: values.vehicle,
                start_time: today.clone().set({
                    hour: startTime.hour(),
                    minute: startTime.minute(),
                    second: 0
                }).toISOString(),
                end_time: today.clone().set({
                    hour: endTime.hour(),
                    minute: endTime.minute(),
                    second: 0
                }).toISOString(),
                status: 'PENDING',
                is_recurring: true,
                recurrence_pattern: 'DAILY'
            };

            if (editingShift) {
                await apiClient.put(`/shifts/${editingShift.id}/`, payload);
                message.success('Shift updated. Pending EIC approval.');
            } else {
                await apiClient.post('/shifts/', payload);
                message.success('Shift created successfully');
            }
            
            setIsModalVisible(false);
            setEditingShift(null);
            fetchShifts();
        } catch (error) {
            console.error('Validation failed:', error);
            message.error(error.response?.data?.message || 'Operation failed');
        }
    };

    const handleApprove = async (id) => {
        try {
            await apiClient.post(`/shifts/${id}/approve/`);
            message.success('Shift approved');
            fetchShifts();
        } catch (error) {
            message.error('Failed to approve shift (Only EIC allowed)');
        }
    };

    const openRejectModal = (id) => {
        setRejectTarget(id);
        setRejectReason('');
        setRejectModalVisible(true);
    };

    const submitReject = async () => {
        if (!rejectTarget) return;
        try {
            await apiClient.post(`/shifts/${rejectTarget}/reject/`, { reason: rejectReason });
            message.success('Shift rejected');
            setRejectModalVisible(false);
            setRejectTarget(null);
            setRejectReason('');
            fetchShifts();
        } catch (error) {
            message.error('Failed to reject shift (Only EIC allowed)');
        }
    };

    const getStatusColor = (status) => {
        switch (status) {
            case 'APPROVED': return '#52c41a';
            case 'REJECTED': return '#ff4d4f';
            case 'ACTIVE': return '#2563EB';
            case 'COMPLETED': return '#722ed1';
            default: return '#faad14';
        }
    };

    const columns = [
        {
            title: 'Driver',
            dataIndex: ['driver_details', 'full_name'],
            key: 'driver',
            render: (text) => <Text strong>{text}</Text>
        },
        {
            title: 'Vehicle',
            dataIndex: ['vehicle_details', 'registration_no'],
            key: 'vehicle',
            render: (text) => <Tag color="blue">{text}</Tag>
        },
        {
            title: 'Start Time',
            dataIndex: 'start_time',
            key: 'start_time',
            render: (text) => (
                <Space>
                    <CalendarOutlined style={{ color: '#2563EB' }} />
                    {moment(text).format('MMM DD, YYYY HH:mm')}
                </Space>
            )
        },
        {
            title: 'End Time',
            dataIndex: 'end_time',
            key: 'end_time',
            render: (text) => (
                <Space>
                    <ClockCircleOutlined style={{ color: '#722ed1' }} />
                    {moment(text).format('MMM DD, YYYY HH:mm')}
                </Space>
            )
        },
        {
            title: 'Type',
            key: 'type',
            render: (_, record) => (
                <Tag color={record.is_recurring ? 'purple' : 'cyan'}>
                    {record.is_recurring ? 'Daily' : 'One-time'}
                </Tag>
            )
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status) => (
                <Tag
                    color={getStatusColor(status)}
                    style={{
                        borderRadius: 12,
                        padding: '2px 12px',
                        fontWeight: 500
                    }}
                >
                    {status}
                </Tag>
            )
        },
        {
            title: 'Rejection Reason',
            dataIndex: 'rejection_reason',
            key: 'rejection_reason',
            render: (text, record) => record.status === 'REJECTED' ? (
                <Tag color="red" style={{ borderRadius: 12, padding: '2px 10px' }}>
                    {text || 'Not provided'}
                </Tag>
            ) : null,
        },
        // {
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <Space>
                    {record.status !== 'COMPLETED' && (
                        <Button
                            icon={<EditOutlined />}
                            size="small"
                            style={{ borderRadius: 6 }}
                            onClick={() => handleEdit(record)}
                        >
                            Edit
                        </Button>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <div className="shift-management" style={{ padding: 24 }}>
            <Card
                bordered={false}
                style={{
                    borderRadius: 12,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.08)'
                }}
            >
                <div style={{
                    marginBottom: 24,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div>
                        <Title level={3} style={{ margin: 0, color: '#1a1a2e' }}>
                            Shift Management
                        </Title>
                        <Text type="secondary">Create and manage driver shifts</Text>
                    </div>
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
                            background: '#2563EB'
                        }}
                    >
                        Create Shift
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={shifts}
                    rowKey="id"
                    loading={loading}
                    style={{ marginTop: 16 }}
                    pagination={{
                        defaultPageSize: 10,
                        showSizeChanger: true,
                        pageSizeOptions: ['10', '20', '50', '100'],
                        showTotal: (total) => `Total ${total} shifts`
                    }}
                />
            </Card>

            <Modal
                title="Reject Shift"
                open={rejectModalVisible}
                onOk={submitReject}
                onCancel={() => setRejectModalVisible(false)}
                okText="Reject"
                okButtonProps={{ danger: true }}
            >
                <Input.TextArea
                    rows={3}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter rejection reason (required for visibility)"
                />
            </Modal>

            <Modal
                title={
                    <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 16 }}>
                        <Title level={4} style={{ margin: 0 }}>{editingShift ? 'Edit Shift' : 'Create New Shift'}</Title>
                        <Text type="secondary">{editingShift ? 'Update shift details (requires EIC approval)' : 'Schedule a shift for a driver'}</Text>
                    </div>
                }
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                okText="Create Shift"
                width={500}
                okButtonProps={{
                    style: {
                        borderRadius: 6,
                        background: '#2563EB'
                    }
                }}
                cancelButtonProps={{ style: { borderRadius: 6 } }}
            >
                <Form form={form} layout="vertical" style={{ marginTop: 24 }}>
                    <Form.Item
                        name="driver"
                        label={<Text strong>Driver</Text>}
                        rules={[{ required: true, message: 'Please select a driver' }]}
                    >
                        <Select
                            placeholder="Select Driver"
                            onChange={handleDriverChange}
                            size="large"
                            style={{ borderRadius: 8 }}
                        >
                            {drivers.map(d => (
                                <Option key={d.id} value={d.id}>
                                    <Space>
                                        <span>{d.full_name}</span>
                                        {d.assigned_vehicle_details && (
                                            <Tag color="blue" style={{ marginLeft: 8 }}>
                                                {d.assigned_vehicle_details.registration_no}
                                            </Tag>
                                        )}
                                    </Space>
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="vehicle"
                        label={<Text strong>Vehicle</Text>}
                        rules={[{ required: true, message: 'Please select a vehicle' }]}
                    >
                        <Select placeholder="Select Vehicle" size="large">
                            {vehicles.map(v => (
                                <Option key={v.id} value={v.id}>{v.registration_no}</Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Divider />

                    {/* Schedule Type - Always Daily (commented out for now) */}
                    {/* <Form.Item label={<Text strong>Schedule Type</Text>}>
                        <Radio.Group
                            value={scheduleType}
                            onChange={(e) => setScheduleType(e.target.value)}
                            buttonStyle="solid"
                            style={{ width: '100%',display: 'flex',justifyContent: 'center' }}
                        >
                            <Radio.Button
                                value="daily"
                                style={{
                                    width: '50%',
                                    textAlign: 'center',
                                    borderRadius: '8px'
                                }}
                            >
                                <ClockCircleOutlined /> Daily Shift
                            </Radio.Button>
                        </Radio.Group>
                    </Form.Item> */}

                    {/* Always show daily shift form */}
                    <div style={{
                        background: '#f9f9fb',
                        padding: 16,
                        borderRadius: 8
                    }}>
                        <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
                            Set daily shift timing (repeats every day)
                        </Text>
                        <Space style={{ width: '100%' }} direction="vertical" size="middle">
                            <Form.Item
                                name="dailyStartTime"
                                label="Start Time"
                                rules={[{ required: true, message: 'Select start time' }]}
                                style={{ marginBottom: 0 }}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    size="large"
                                    style={{ width: '100%' }}
                                    placeholder="e.g., 09:00"
                                />
                            </Form.Item>
                            <Form.Item
                                name="dailyEndTime"
                                label="End Time"
                                rules={[{ required: true, message: 'Select end time' }]}
                                style={{ marginBottom: 0 }}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    size="large"
                                    style={{ width: '100%' }}
                                    placeholder="e.g., 18:00"
                                />
                            </Form.Item>
                        </Space>
                    </div>
                </Form>
            </Modal>
        </div>
    );
};

export default ShiftManagement;
