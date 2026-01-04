import React, { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, Select, message, Card, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import apiClient from '../services/api';

const { Option } = Select;

const VehicleManagement = () => {
    const [vehicles, setVehicles] = useState([]);
    const [loading, setLoading] = useState(false);
    const [isModalVisible, setIsModalVisible] = useState(false);
    const [editingVehicle, setEditingVehicle] = useState(null);
    const [stations, setStations] = useState([]);
    const [stationsLoading, setStationsLoading] = useState(false);
    const [form] = Form.useForm();

    useEffect(() => {
        fetchVehicles();
        // Don't fetch stations on mount - fetch only when modal opens
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
        // Fetch stations only when modal opens if not already loaded
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
        // Fetch stations only when modal opens if not already loaded
        if (stations.length === 0 && !stationsLoading) {
            fetchStations();
        }
        setIsModalVisible(true);
    };

    const handleDelete = async (id) => {
        try {
            await apiClient.delete(`/vehicles/${id}/`);
            message.success('Vehicle deleted successfully');
            fetchVehicles();
        } catch (error) {
            message.error('Failed to delete vehicle');
        }
    };

    const handleModalOk = async () => {
        try {
            const values = await form.validateFields();
            if (editingVehicle) {
                await apiClient.put(`/vehicles/${editingVehicle.id}/`, values);
                message.success('Vehicle updated successfully');
            } else {
                await apiClient.post('/vehicles/', values);
                message.success('Vehicle created successfully');
            }
            setIsModalVisible(false);
            fetchVehicles();
        } catch (error) {
            console.error('Validation failed:', error);
            message.error(error.response?.data?.message || 'Operation failed');
        }
    };

    const columns = [
        { title: 'Registration No', dataIndex: 'registration_no', key: 'registration_no' },
        { title: 'HCV Code', dataIndex: 'hcv_code', key: 'hcv_code' },
        { title: 'Vendor', dataIndex: ['vendor_details', 'full_name'], key: 'vendor' },
        { title: 'Home MS', dataIndex: ['ms_home_details', 'name'], key: 'ms_home' },
        { title: 'Capacity (Kg)', dataIndex: 'capacity_kg', key: 'capacity_kg' },
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
            >
                <Form form={form} layout="vertical">
                    <Form.Item
                        name="registration_no"
                        label="Registration Number"
                        rules={[{ required: true, message: 'Please enter registration number' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        name="hcv_code"
                        label="HCV Code"
                    >
                        <Input />
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
                        name="capacity_kg"
                        label="Capacity (Kg)"
                        rules={[{ required: true, message: 'Please enter capacity' }]}
                    >
                        <Input type="number" />
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
};

export default VehicleManagement;
