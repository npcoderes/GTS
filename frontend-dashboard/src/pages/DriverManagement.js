import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, DatePicker, Alert, Typography, Card, Space, Tag, TimePicker, Divider } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined, KeyOutlined, CopyOutlined } from '@ant-design/icons';
import apiClient from '../services/api';
import moment from 'moment';

const { Option } = Select;
const { Text, Title } = Typography;

const DriverManagement = () => {
    const [drivers, setDrivers] = useState([]);
    const [driverCountsByVehicle, setDriverCountsByVehicle] = useState({});
    const [loading, setLoading] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [isCredentialsModalVisible, setIsCredentialsModalVisible] = useState(false);
    const [createdDriverCredentials, setCreatedDriverCredentials] = useState(null);
    const [editingDriver, setEditingDriver] = useState(null);
    const [vehicles, setVehicles] = useState([]);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchDrivers();
        fetchVehicles();
    }, []);

    const fetchDrivers = async () => {
        setLoading(true);
        try {
            const response = await apiClient.get('/drivers/');
            const driverList = response.data.results || response.data;
            setDrivers(driverList);

            // Build driver count per vehicle for UI hints
            const counts = {};
            (driverList || []).forEach(d => {
                const vid = d.assigned_vehicle_details?.id || d.assigned_vehicle;
                if (vid) counts[vid] = (counts[vid] || 0) + 1;
            });
            setDriverCountsByVehicle(counts);
        } catch (error) {
            message.error('Failed to fetch drivers');
        } finally {
            setLoading(false);
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

    const generatePassword = () => {
        const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
        let password = '';
        for (let i = 0; i < 8; i++) {
            password += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return password;
    };

    const handleAdd = () => {
        setEditingDriver(null);
        form.resetFields();
        form.setFieldsValue({ password: generatePassword() });
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingDriver(record);
        form.setFieldsValue({
            ...record,
            assigned_vehicle: record.assigned_vehicle_details?.id,
            license_expiry: record.license_expiry ? moment(record.license_expiry) : null,
            status: record.status
        });
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        try {
            await apiClient.delete(`/drivers/${id}/`);
            message.success('Driver deleted successfully');
            fetchDrivers();
        } catch (error) {
            message.error('Failed to delete driver');
        }
    };

    // Generate credentials locally for display (matches backend signal logic)
    const generateCredentials = (phone, fullName, driverId) => {
        const phoneClean = phone?.replace(/\D/g, '') || '';
        const email = phoneClean
            ? `driver_${phoneClean}@gts.local`
            : `driver_${fullName.toLowerCase().replace(/\s+/g, '_')}_${driverId}@gts.local`;
        const password = phoneClean
            ? `driver_${phoneClean.slice(-4)}`
            : `driver_${driverId}`;
        return { email, password };
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        message.success('Copied to clipboard!');
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            const payload = {
                ...values,
                license_expiry: values.license_expiry.format('YYYY-MM-DD')
            };

            setSubmitLoading(true);

            if (editingDriver) {
                await apiClient.put(`/drivers/${editingDriver.id}/`, payload);
                message.success('Driver updated successfully');
                setIsModalVisible(false);
            } else {
                // Create new driver with optional shift
                const driverPayload = { ...payload };
                delete driverPayload.shift_start_time;
                delete driverPayload.shift_end_time;
                
                const response = await apiClient.post('/drivers/', driverPayload);
                const driverId = response.data.id;
                
                // Create shift if time fields are provided
                if (values.shift_start_time && values.shift_end_time && values.assigned_vehicle) {
                    try {
                        const today = moment();
                        const startDateTime = today.clone().set({
                            hour: values.shift_start_time.hour(),
                            minute: values.shift_start_time.minute(),
                            second: 0
                        });
                        const endDateTime = today.clone().set({
                            hour: values.shift_end_time.hour(),
                            minute: values.shift_end_time.minute(),
                            second: 0
                        });
                        
                        await apiClient.post('/shifts/', {
                            driver: driverId,
                            vehicle: values.assigned_vehicle,
                            start_time: startDateTime.toISOString(),
                            end_time: endDateTime.toISOString(),
                            is_recurring: true,
                            recurrence_pattern: 'DAILY'
                        });
                        message.success('Driver and shift created successfully');
                    } catch (shiftError) {
                        message.warning('Driver created but shift creation failed: ' + 
                            (shiftError.response?.data?.message || shiftError.response?.data?.error || 'Unknown error'));
                    }
                } else {
                    message.success('Driver created successfully');
                }
                setIsModalVisible(false);
            }
            fetchDrivers();
        } catch (error) {
            message.error(error.response?.data?.message || 'Operation failed');
        } finally {
            setSubmitLoading(false);
        }
    };

    const columns = [
        { title: 'Full Name', dataIndex: 'full_name', key: 'full_name' },
        { title: 'License No', dataIndex: 'license_no', key: 'license_no' },
        { title: 'Phone', dataIndex: 'phone', key: 'phone' },
        { title: 'Vendor', dataIndex: ['vendor_details', 'full_name'], key: 'vendor' },
        { title: 'Assigned Vehicle', dataIndex: ['assigned_vehicle_details', 'registration_no'], key: 'assigned_vehicle' },
        {
            title: 'Login Email',
            dataIndex: ['user_details', 'email'],
            key: 'login_email',
            render: (email) => email ? <Tag color="blue">{email}</Tag> : <Tag color="orange">Not Created</Tag>
        },
        {
            title: 'Status', dataIndex: 'status', key: 'status',
            render: (status) => {
                const colors = { ACTIVE: 'green', INACTIVE: 'default', SUSPENDED: 'red' };
                return <Tag color={colors[status] || 'default'}>{status}</Tag>;
            }
        },
        {
            title: 'Actions',
            key: 'actions',
            render: (_, record) => (
                <>
                    <Button icon={<EditOutlined />} onClick={() => handleEdit(record)} style={{ marginRight: 8 }} />
                    <Button icon={<DeleteOutlined />} danger onClick={() => handleDelete(record.id)} />
                </>
            ),
        },
    ];

    return (
        <div className="driver-management">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Driver Management</h2>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    Add Driver
                </Button>
            </div>

            <Alert
                message="Driver Account Creation"
                description="Please provide an email and password for the driver. These credentials will be used for the driver mobile app login."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
            />

            <Table 
                columns={columns} 
                dataSource={drivers} 
                rowKey="id" 
                loading={loading}
                pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total) => `Total ${total} drivers`
                }}
            />

            {/* Add/Edit Driver Modal */}
            <Modal
                title={editingDriver ? "Edit Driver" : "Add Driver"}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                confirmLoading={submitLoading}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="full_name"
                        label="Full Name"
                        rules={[{ required: true, message: 'Please enter full name' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="license_no"
                        label="License Number"
                        rules={[{ required: true, message: 'Please enter license number' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="license_expiry"
                        label="License Expiry"
                        rules={[{ required: true, message: 'Please select expiry date' }]}
                    >
                        <DatePicker style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item
                        name="phone"
                        label="Phone Number"
                        rules={[{ required: true, message: 'Please enter phone number' }]}
                    >
                        <Input />
                    </Form.Item>

                    {!editingDriver && (
                        <>
                            <Form.Item
                                name="email"
                                label="Login Email (Optional)"
                                rules={[
                                    { type: 'email', message: 'Please enter valid email' }
                                ]}
                            >
                                <Input prefix={<UserOutlined />} placeholder="Enter email" />
                            </Form.Item>
                            <Form.Item  
                                name="password"
                                label="Login Password"
                                rules={[{ required: true, message: 'Please enter password' }]}
                            >
                                <Input.Password prefix={<KeyOutlined />} />
                            </Form.Item>
                            
                            <Divider>Create Daily Shift (Optional)</Divider>
                            
                            <Form.Item
                                name="shift_start_time"
                                label="Shift Start Time"
                            >
                                <TimePicker style={{ width: '100%' }} format="HH:mm" />
                            </Form.Item>
                            <Form.Item
                                name="shift_end_time"
                                label="Shift End Time"
                            >
                                <TimePicker style={{ width: '100%' }} format="HH:mm" />
                            </Form.Item>
                        </>
                    )}
                    <Form.Item
                        name="assigned_vehicle"
                        label="Assigned Vehicle"
                    >
                        <Select placeholder="Select Vehicle" allowClear>
                            {vehicles.map(v => {
                                const count = driverCountsByVehicle[v.id] || 0;
                                const isEditingSame = editingDriver && editingDriver.assigned_vehicle_details?.id === v.id;
                                const isFull = count >= 2 && !isEditingSame;
                                const label = `${v.registration_no} (${count}/2 drivers${isFull ? ' - FULL' : ''})`;
                                return (
                                    <Option key={v.id} value={v.id} disabled={isFull}>
                                        {label}
                                    </Option>
                                );
                            })}
                        </Select>
                    </Form.Item>
                    <Form.Item
                        name="status"
                        label="Status"
                        initialValue="ACTIVE"
                    >
                        <Select>
                            <Option value="ACTIVE">Active</Option>
                            <Option value="INACTIVE">Inactive</Option>
                            <Option value="SUSPENDED">Suspended</Option>
                        </Select>
                    </Form.Item>
                </Form>
            </Modal>

            {/* Credentials Display Modal */}
            <Modal
                title="Driver Created Successfully!"
                open={isCredentialsModalVisible}
                onOk={() => setIsCredentialsModalVisible(false)}
                onCancel={() => setIsCredentialsModalVisible(false)}
                footer={[
                    <Button key="ok" type="primary" onClick={() => setIsCredentialsModalVisible(false)}>
                        Done
                    </Button>
                ]}
            >
                {createdDriverCredentials && (
                    <Card>
                        <Alert
                            message="Important: Save These Credentials"
                            description="Share these login credentials with the driver. They can use these to login to the mobile app."
                            type="warning"
                            showIcon
                            style={{ marginBottom: 16 }}
                        />

                        <Title level={5}>Driver: {createdDriverCredentials.fullName}</Title>

                        <Space direction="vertical" style={{ width: '100%' }}>
                            <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
                                <Space>
                                    <UserOutlined />
                                    <Text strong>Login Email:</Text>
                                </Space>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                                    <Text code style={{ fontSize: 14 }}>{createdDriverCredentials.email}</Text>
                                    <Button
                                        icon={<CopyOutlined />}
                                        size="small"
                                        onClick={() => copyToClipboard(createdDriverCredentials.email)}
                                    >
                                        Copy
                                    </Button>
                                </div>
                            </div>

                            <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 8 }}>
                                <Space>
                                    <KeyOutlined />
                                    <Text strong>Default Password:</Text>
                                </Space>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
                                    <Text code style={{ fontSize: 14 }}>{createdDriverCredentials.password}</Text>
                                    <Button
                                        icon={<CopyOutlined />}
                                        size="small"
                                        onClick={() => copyToClipboard(createdDriverCredentials.password)}
                                    >
                                        Copy
                                    </Button>
                                </div>
                            </div>
                        </Space>

                        <Alert
                            message="Driver should change password on first login"
                            type="info"
                            style={{ marginTop: 16 }}
                        />
                    </Card>
                )}
            </Modal>
        </div>
    );
};

export default DriverManagement;

