import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, DatePicker, Alert, Typography, Card, Space, Tag, Upload, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UserOutlined, KeyOutlined, CopyOutlined, EyeOutlined, InboxOutlined, FileTextOutlined } from '@ant-design/icons';
import apiClient from '../services/api';
import moment from 'moment';

const { Option } = Select;
const { Text, Title } = Typography;
const { Dragger } = Upload;

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
    const [licenseFileList, setLicenseFileList] = useState([]);
    const [isPreviewModalVisible, setIsPreviewModalVisible] = useState(false);
    const [previewFile, setPreviewFile] = useState(null);
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
        // Generate simple, memorable passwords like: blue2026, red2025, etc.
        const words = ['blue', 'red', 'green', 'star', 'moon', 'sun', 'sky', 'tree', 'rock', 'wave'];
        const word = words[Math.floor(Math.random() * words.length)];
        const year = new Date().getFullYear();
        return `${word}${year}`;
    };

    const handleAdd = () => {
        setEditingDriver(null);
        form.resetFields();
        form.setFieldsValue({ password: generatePassword(), status: 'ACTIVE' });
        setLicenseFileList([]);
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
        // Set existing document if any
        if (record.license_document_url) {
            setLicenseFileList([{
                uid: '-1',
                name: 'License Document',
                status: 'done',
                url: record.license_document_url
            }]);
        } else {
            setLicenseFileList([]);
        }
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        Modal.confirm({
            title: 'Delete Driver',
            content: 'Are you sure you want to delete this driver? This action cannot be undone.',
            okText: 'Delete',
            okType: 'danger',
            cancelText: 'Cancel',
            onOk: async () => {
                try {
                    await apiClient.delete(`/drivers/${id}/`);
                    message.success('Driver deleted successfully');
                    fetchDrivers();
                } catch (error) {
                    message.error('Failed to delete driver');
                }
            }
        });
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        message.success('Copied to clipboard!');
    };

    // File upload validation
    const beforeUpload = (file) => {
        const isValidType = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'].includes(file.type);
        if (!isValidType) {
            message.error('Only PDF, PNG, and JPG files are allowed!');
            return Upload.LIST_IGNORE;
        }
        const isLt5M = file.size / 1024 / 1024 < 5;
        if (!isLt5M) {
            message.error('Document must be smaller than 5MB!');
            return Upload.LIST_IGNORE;
        }
        return false; // Prevent auto upload
    };

    const handleLicenseChange = ({ fileList }) => {
        setLicenseFileList(fileList.slice(-1)); // Keep only the last file
    };

    const handlePreviewDocument = (file) => {
        let previewUrl = null;
        let fileType = null;
        let fileName = file.name || 'Document';

        if (file.url) {
            // Existing uploaded file
            previewUrl = file.url;
            fileType = file.name?.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image';
        } else if (file.originFileObj) {
            // Newly selected file
            previewUrl = URL.createObjectURL(file.originFileObj);
            fileType = file.type?.startsWith('image/') ? 'image' : 'pdf';
        }

        setPreviewFile({ url: previewUrl, type: fileType, name: fileName });
        setIsPreviewModalVisible(true);
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();

            // Use FormData for file upload support
            const formData = new FormData();
            formData.append('full_name', values.full_name);
            formData.append('license_no', values.license_no);
            formData.append('phone', values.phone);
            formData.append('license_expiry', values.license_expiry.format('YYYY-MM-DD'));
            formData.append('status', values.status);
            if (values.assigned_vehicle) formData.append('assigned_vehicle', values.assigned_vehicle);

            // Add license document if uploaded
            if (licenseFileList.length > 0 && licenseFileList[0].originFileObj) {
                formData.append('license_document', licenseFileList[0].originFileObj);
            }

            setSubmitLoading(true);

            if (editingDriver) {
                await apiClient.put(`/drivers/${editingDriver.id}/`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                message.success('Driver updated successfully');
                setIsModalVisible(false);
            } else {
                // For new driver, also add email and password
                if (values.email) formData.append('email', values.email);
                formData.append('password', values.password);

                await apiClient.post('/drivers/', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                message.success('Driver created successfully');
                setIsModalVisible(false);
            }
            fetchDrivers();
        } catch (error) {
            console.error('Operation failed:', error);
            message.error(error.response?.data?.message || error.response?.data?.license_document?.[0] || 'Operation failed');
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
            title: 'License Doc',
            key: 'license_doc',
            render: (_, record) => record.license_document_url ? (
                <Tooltip title="View Document">
                    <Button
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => {
                            const fileName = record.license_document_url.split('/').pop() || 'License Document';
                            const fileType = fileName.toLowerCase().endsWith('.pdf') ? 'pdf' : 'image';
                            setPreviewFile({
                                url: record.license_document_url,
                                type: fileType,
                                name: `${record.full_name} - License Document`
                            });
                            setIsPreviewModalVisible(true);
                        }}
                        size="small"
                    >
                        View
                    </Button>
                </Tooltip>
            ) : (
                <Tag color="orange">Not uploaded</Tag>
            )
        },
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
            width: 120,
            render: (_, record) => (
                <Space>
                    <Tooltip title="Edit">
                        <Button icon={<EditOutlined />} onClick={() => handleEdit(record)} size="small" />
                    </Tooltip>
                    <Tooltip title="Delete">
                        <Button icon={<DeleteOutlined />} danger onClick={() => handleDelete(record.id)} size="small" />
                    </Tooltip>
                </Space>
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
                description="Phone number is the primary login credential for drivers. Email is optional. A simple, memorable password will be auto-generated for the driver mobile app login."
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
                scroll={{ x: 1200 }}
            />

            {/* Add/Edit Driver Modal */}
            <Modal
                title={editingDriver ? "Edit Driver" : "Add Driver"}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                confirmLoading={submitLoading}
                width={600}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="full_name"
                        label="Full Name"
                        rules={[{ required: true, message: 'Please enter full name' }]}
                    >
                        <Input placeholder="Enter driver's full name" />
                    </Form.Item>

                    <div style={{ display: 'flex', gap: 16 }}>
                        <Form.Item
                            name="license_no"
                            label="License Number"
                            rules={[{ required: true, message: 'Please enter license number' }]}
                            style={{ flex: 1 }}
                        >
                            <Input placeholder="e.g., DL-1234567890" />
                        </Form.Item>
                        <Form.Item
                            name="license_expiry"
                            label="License Expiry"
                            rules={[{ required: true, message: 'Please select expiry date' }]}
                            style={{ flex: 1 }}
                        >
                            <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                    </div>

                    <Form.Item
                        name="phone"
                        label="Phone Number"
                        rules={[{ required: true, message: 'Please enter phone number' }]}
                    >
                        <Input placeholder="e.g., +91 9876543210" />
                    </Form.Item>

                    {!editingDriver && (
                        <div style={{ display: 'flex', gap: 16 }}>
                            <Form.Item
                                name="email"
                                label="Login Email (Optional)"
                                rules={[
                                    { type: 'email', message: 'Please enter valid email' }
                                ]}
                                style={{ flex: 1 }}
                            >
                                <Input prefix={<UserOutlined />} placeholder="driver@example.com (optional)" />
                            </Form.Item>
                            <Form.Item
                                name="password"
                                label="Login Password"
                                rules={[{ required: true, message: 'Please enter password' }]}
                                style={{ flex: 1 }}
                            >
                                <Input.Password prefix={<KeyOutlined />} />
                            </Form.Item>
                        </div>
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
                    >
                        <Select>
                            <Option value="ACTIVE">Active</Option>
                            <Option value="INACTIVE">Inactive</Option>
                            <Option value="SUSPENDED">Suspended</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="License Document"
                        extra="Accepted formats: PDF, PNG, JPG. Max size: 5MB"
                        required={!editingDriver}
                    >
                        <Dragger
                            fileList={licenseFileList}
                            beforeUpload={beforeUpload}
                            onChange={handleLicenseChange}
                            maxCount={1}
                            accept=".pdf,.png,.jpg,.jpeg"
                            onPreview={handlePreviewDocument}
                            itemRender={(originNode, file) => {
                                // Custom render to show preview
                                const isPdf = file.name?.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf';
                                const isImage = file.type?.startsWith('image/');

                                return (
                                    <div style={{
                                        padding: '8px',
                                        border: '1px solid #d9d9d9',
                                        borderRadius: '4px',
                                        marginTop: '8px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px'
                                    }}>
                                        {isImage && file.url && (
                                            <img
                                                src={file.url}
                                                alt="License preview"
                                                style={{
                                                    width: '60px',
                                                    height: '60px',
                                                    objectFit: 'cover',
                                                    borderRadius: '4px'
                                                }}
                                            />
                                        )}
                                        {isImage && file.originFileObj && !file.url && (
                                            <img
                                                src={URL.createObjectURL(file.originFileObj)}
                                                alt="License preview"
                                                style={{
                                                    width: '60px',
                                                    height: '60px',
                                                    objectFit: 'cover',
                                                    borderRadius: '4px'
                                                }}
                                            />
                                        )}
                                        {isPdf && (
                                            <FileTextOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
                                        )}
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontWeight: 500 }}>{file.name}</div>
                                            {file.status === 'done' && (
                                                <Tag color="success" style={{ marginTop: '4px' }}>Uploaded</Tag>
                                            )}
                                        </div>
                                        <Space>
                                            <Tooltip title="Preview Document">
                                                <Button
                                                    type="link"
                                                    icon={<EyeOutlined />}
                                                    onClick={() => handlePreviewDocument(file)}
                                                >
                                                    Preview
                                                </Button>
                                            </Tooltip>
                                            <Button
                                                type="link"
                                                danger
                                                onClick={() => setLicenseFileList([])}
                                            >
                                                Remove
                                            </Button>
                                        </Space>
                                    </div>
                                );
                            }}
                        >
                            <p className="ant-upload-drag-icon">
                                <InboxOutlined />
                            </p>
                            <p className="ant-upload-text">Click or drag file to upload</p>
                            <p className="ant-upload-hint" style={{ color: '#888' }}>
                                Upload driver's license document
                            </p>
                        </Dragger>
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

            {/* Document Preview Modal */}
            <Modal
                title={previewFile?.name || "Document Preview"}
                open={isPreviewModalVisible}
                onCancel={() => {
                    setIsPreviewModalVisible(false);
                    setPreviewFile(null);
                }}
                footer={[
                    <Button key="close" onClick={() => {
                        setIsPreviewModalVisible(false);
                        setPreviewFile(null);
                    }}>
                        Close
                    </Button>
                ]}
                width={800}
                centered
            >
                {previewFile && (
                    <div style={{ textAlign: 'center' }}>
                        {previewFile.type === 'image' ? (
                            <img
                                src={previewFile.url}
                                alt="Document preview"
                                style={{
                                    maxWidth: '100%',
                                    maxHeight: '70vh',
                                    objectFit: 'contain'
                                }}
                            />
                        ) : (
                            <iframe
                                src={previewFile.url}
                                title="PDF preview"
                                style={{
                                    width: '100%',
                                    height: '70vh',
                                    border: 'none'
                                }}
                            />
                        )}
                    </div>
                )}
            </Modal>
        </div>
    );
};

export default DriverManagement;
