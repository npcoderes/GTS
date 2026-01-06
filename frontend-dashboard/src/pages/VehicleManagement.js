import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Upload, Tag, Tooltip, Space } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, FileTextOutlined, EyeOutlined, InboxOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

const { Option } = Select;
const { Dragger } = Upload;

const VehicleManagement = () => {
    const [vehicles, setVehicles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [submitLoading, setSubmitLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingVehicle, setEditingVehicle] = useState(null);
    const [stations, setStations] = useState([]);
    const [stationsLoading, setStationsLoading] = useState(false);
    const [documentFileList, setDocumentFileList] = useState([]);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchVehicles();
    }, []);

    const fetchVehicles = async () => {
        setLoading(true);
        try {
            const response = await apiClient.get('/vehicles/');
            setVehicles(response.data.results || response.data);
        } catch (error) {
            message.error('Failed to fetch vehicles');
        } finally {
            setLoading(false);
        }
    };

    const fetchStations = async () => {
        setStationsLoading(true);
        try {
            const response = await apiClient.get('/stations/?type=MS');
            setStations(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to fetch stations', error);
            message.error('Failed to load stations');
        } finally {
            setStationsLoading(false);
        }
    };

    const handleAdd = () => {
        setEditingVehicle(null);
        form.resetFields();
        setDocumentFileList([]);
        if (stations.length === 0 && !stationsLoading) {
            fetchStations();
        }
        setIsModalVisible(true);
    };

    const handleEdit = (record) => {
        setEditingVehicle(record);
        form.setFieldsValue({
            ...record,
            ms_home: record.ms_home_details?.id || record.ms_home
        });
        // Set existing document if any
        if (record.registration_document_url) {
            setDocumentFileList([{
                uid: '-1',
                name: 'Registration Document',
                status: 'done',
                url: record.registration_document_url
            }]);
        } else {
            setDocumentFileList([]);
        }
        if (stations.length === 0 && !stationsLoading) {
            fetchStations();
        }
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        Modal.confirm({
            title: 'Delete Vehicle',
            content: 'Are you sure you want to delete this vehicle? This action cannot be undone.',
            okText: 'Delete',
            okType: 'danger',
            cancelText: 'Cancel',
            onOk: async () => {
                try {
                    await apiClient.delete(`/vehicles/${id}/`);
                    message.success('Vehicle deleted successfully');
                    fetchVehicles();
                } catch (error) {
                    message.error('Failed to delete vehicle');
                }
            }
        });
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();

            // Use FormData for file upload support
            const formData = new FormData();
            formData.append('registration_no', values.registration_no);
            if (values.hcv_code) formData.append('hcv_code', values.hcv_code);
            if (values.ms_home) formData.append('ms_home', values.ms_home);

            // Add registration document if uploaded
            if (documentFileList.length > 0 && documentFileList[0].originFileObj) {
                formData.append('registration_document', documentFileList[0].originFileObj);
            }

            setSubmitLoading(true);

            if (editingVehicle) {
                await apiClient.put(`/vehicles/${editingVehicle.id}/`, formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                message.success('Vehicle updated successfully');
            } else {
                await apiClient.post('/vehicles/', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                message.success('Vehicle created successfully');
            }
            setIsModalVisible(false);
            fetchVehicles();
        } catch (error) {
            console.error('Operation failed:', error);
            message.error(error.response?.data?.message || error.response?.data?.registration_document?.[0] || 'Operation failed');
        } finally {
            setSubmitLoading(false);
        }
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

    const handleDocumentChange = ({ fileList }) => {
        setDocumentFileList(fileList.slice(-1)); // Keep only the last file
    };

    const columns = [
        {
            title: 'Registration No',
            dataIndex: 'registration_no',
            key: 'registration_no',
            render: (text) => <Tag color="blue">{text}</Tag>
        },
        { title: 'HCV Code', dataIndex: 'hcv_code', key: 'hcv_code' },
        { title: 'Vendor', dataIndex: ['vendor_details', 'full_name'], key: 'vendor' },
        { title: 'Home MS', dataIndex: ['ms_home_details', 'name'], key: 'ms_home' },
        {
            title: 'Reg. Document',
            key: 'registration_document',
            render: (_, record) => record.registration_document_url ? (
                <Tooltip title="View Document">
                    <Button
                        type="link"
                        icon={<EyeOutlined />}
                        onClick={() => window.open(record.registration_document_url, '_blank')}
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
        <div className="vehicle-management">
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2>Vehicle Management</h2>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                    Add Vehicle
                </Button>
            </div>
            <Table
                columns={columns}
                dataSource={vehicles}
                rowKey="id"
                loading={loading}
                pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50', '100'],
                    showTotal: (total) => `Total ${total} vehicles`
                }}
            />

            <Modal
                title={editingVehicle ? "Edit Vehicle" : "Add Vehicle"}
                open={isModalVisible}
                onOk={handleModalOk}
                onCancel={() => setIsModalVisible(false)}
                confirmLoading={submitLoading}
                width={500}
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="registration_no"
                        label="Registration Number"
                        rules={[{ required: true, message: 'Please enter registration number' }]}
                    >
                        <Input placeholder="e.g., MH-12-AB-1234" />
                    </Form.Item>
                    <Form.Item
                        name="hcv_code"
                        label="HCV Code"
                    >
                        <Input placeholder="e.g., HCV-001" />
                    </Form.Item>
                    <Form.Item
                        name="ms_home"
                        label="Home Mother Station"
                        rules={[{ required: true, message: 'Please select a home station' }]}
                    >
                        <Select
                            placeholder="Select MS"
                            loading={stationsLoading}
                            notFoundContent={stationsLoading ? 'Loading stations...' : 'No stations found'}
                        >
                            {stations.map(s => (
                                <Option key={s.id} value={s.id}>{s.name}</Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="Registration Document"
                        extra="Accepted formats: PDF, PNG, JPG. Max size: 5MB"
                    >
                        <Dragger
                            fileList={documentFileList}
                            beforeUpload={beforeUpload}
                            onChange={handleDocumentChange}
                            maxCount={1}
                            accept=".pdf,.png,.jpg,.jpeg"
                        >
                            <p className="ant-upload-drag-icon">
                                <InboxOutlined />
                            </p>
                            <p className="ant-upload-text">Click or drag file to upload</p>
                            <p className="ant-upload-hint" style={{ color: '#888' }}>
                                Upload vehicle registration document
                            </p>
                        </Dragger>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default VehicleManagement;
