import React, { useState, useEffect } from 'react';
import { Table, Card, Tag, Button, message, Row, Col, Statistic, Space, Typography, Select, DatePicker } from 'antd';
import { ReloadOutlined, RocketOutlined, CheckCircleOutlined, ClockCircleOutlined, CarOutlined, FilterOutlined } from '@ant-design/icons';
import apiClient from '../services/api';
import dayjs from 'dayjs';

const { Text, Title } = Typography;

const TransportAdminLogistics = () => {
    const [trips, setTrips] = useState([]);
    const [filteredTrips, setFilteredTrips] = useState([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState(null);
    const [driverFilter, setDriverFilter] = useState(null);
    const [vehicleFilter, setVehicleFilter] = useState(null);
    const [dateRange, setDateRange] = useState(null);
    const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });

    useEffect(() => {
        fetchTrips(1);
    }, []);

    useEffect(() => {
        applyFilters();
    }, [trips, statusFilter, driverFilter, vehicleFilter, dateRange]);

    const fetchTrips = async (page = 1, pageSize = 20) => {
        setLoading(true);
        try {
            const res = await apiClient.get('/trips/', {
                params: { page, page_size: pageSize }
            });
            const tripsData = Array.isArray(res?.data?.results) ? res.data.results :
                              Array.isArray(res?.data) ? res.data : [];
            const total = res?.data?.count || tripsData.length;
            
            setTrips(tripsData);
            setFilteredTrips(tripsData);
            setPagination({ current: page, pageSize, total });
        } catch (error) {
            console.error('Failed to fetch trips:', error);
            message.error('Failed to load trips');
            setTrips([]);
            setFilteredTrips([]);
        } finally {
            setLoading(false);
        }
    };

    const handleTableChange = (newPagination) => {
        fetchTrips(newPagination.current, newPagination.pageSize);
    };

    const applyFilters = () => {
        let filtered = [...trips];

        if (statusFilter) {
            filtered = filtered.filter(t => t.status === statusFilter);
        }

        if (driverFilter) {
            filtered = filtered.filter(t => t.driver === driverFilter);
        }

        if (vehicleFilter) {
            filtered = filtered.filter(t => t.vehicle === vehicleFilter);
        }

        if (dateRange && dateRange[0] && dateRange[1]) {
            filtered = filtered.filter(t => {
                const tripDate = dayjs(t.created_at);
                return tripDate.isAfter(dateRange[0].startOf('day')) && tripDate.isBefore(dateRange[1].endOf('day'));
            });
        }

        setFilteredTrips(filtered);
    };

    const clearFilters = () => {
        setStatusFilter(null);
        setDriverFilter(null);
        setVehicleFilter(null);
        setDateRange(null);
    };

    const getUniqueDrivers = () => {
        const drivers = trips.map(t => ({ id: t.driver, name: t.driver_details?.full_name })).filter(d => d.id);
        return [...new Map(drivers.map(d => [d.id, d])).values()];
    };

    const getUniqueVehicles = () => {
        const vehicles = trips.map(t => ({ id: t.vehicle, name: t.vehicle_details?.registration_no })).filter(v => v.id);
        return [...new Map(vehicles.map(v => [v.id, v])).values()];
    };

    const getStatusColor = (status) => {
        const colors = {
            'COMPLETED': 'green',
            'CANCELLED': 'red',
            'PENDING': 'orange',
            'AT_MS': 'blue',
            'IN_TRANSIT': 'cyan',
            'AT_DBS': 'purple'
        };
        return colors[status] || 'default';
    };

    const columns = [
        { title: 'Trip ID', dataIndex: 'id', key: 'id', width: 80 },
        { 
            title: 'Driver', 
            key: 'driver', 
            render: (_, record) => (
                <Text strong>{record?.driver_details?.full_name || 'N/A'}</Text>
            )
        },
        { 
            title: 'Vehicle', 
            key: 'vehicle', 
            render: (_, record) => (
                <Tag color="blue">{record?.vehicle_details?.registration_no || 'N/A'}</Tag>
            )
        },
        { 
            title: 'Route', 
            key: 'route', 
            render: (_, record) => (
                <Space direction="vertical" size={0}>
                    <Text type="secondary" style={{ fontSize: 12 }}>From: {record?.ms_details?.name || 'N/A'}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>To: {record?.dbs_details?.name || 'N/A'}</Text>
                </Space>
            )
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status) => (
                <Tag color={getStatusColor(status)} style={{ borderRadius: 12, padding: '2px 12px' }}>
                    {status}
                </Tag>
            )
        },
        {
            title: 'Started',
            key: 'started',
            render: (_, record) => record.started_at ? 
                dayjs(record.started_at).format('MMM DD, HH:mm') : '-'
        },
        {
            title: 'Completed',
            key: 'completed',
            render: (_, record) => record.completed_at ? 
                dayjs(record.completed_at).format('MMM DD, HH:mm') : '-'
        },
    ];

    const activeTrips = filteredTrips.filter(t => !['COMPLETED', 'CANCELLED'].includes(t.status));
    const completedTrips = filteredTrips.filter(t => t.status === 'COMPLETED');

    return (
        <div style={{ padding: 24, background: '#f5f5f5', minHeight: '100vh' }}>
            <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div>
                        <Title level={2} style={{ margin: 0 }}>
                            <CarOutlined /> My Drivers' Trips
                        </Title>
                        <Text type="secondary">Monitor trips from your drivers</Text>
                    </div>
                    <Button icon={<ReloadOutlined />} onClick={fetchTrips} loading={loading}>
                        Refresh
                    </Button>
                </div>

                <Row gutter={16}>
                    <Col xs={24} sm={8}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Total Trips" 
                                value={filteredTrips.length} 
                                prefix={<RocketOutlined />}
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={8}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Active Trips" 
                                value={activeTrips.length}
                                prefix={<ClockCircleOutlined />}
                                valueStyle={{ color: '#1890ff' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={8}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Completed" 
                                value={completedTrips.length}
                                prefix={<CheckCircleOutlined />}
                                valueStyle={{ color: '#52c41a' }}
                            />
                        </Card>
                    </Col>
                </Row>
            </div>

            <Card style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
                <Space style={{ marginBottom: 16, width: '100%', flexWrap: 'wrap' }}>
                    <Select
                        placeholder="Filter by Status"
                        style={{ width: 180 }}
                        allowClear
                        value={statusFilter}
                        onChange={setStatusFilter}
                    >
                        <Select.Option value="PENDING">Pending</Select.Option>
                        <Select.Option value="AT_MS">At MS</Select.Option>
                        <Select.Option value="IN_TRANSIT">In Transit</Select.Option>
                        <Select.Option value="AT_DBS">At DBS</Select.Option>
                        <Select.Option value="COMPLETED">Completed</Select.Option>
                        <Select.Option value="CANCELLED">Cancelled</Select.Option>
                    </Select>

                    <Select
                        placeholder="Filter by Driver"
                        style={{ width: 200 }}
                        allowClear
                        showSearch
                        value={driverFilter}
                        onChange={setDriverFilter}
                        filterOption={(input, option) =>
                            (option?.children ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                    >
                        {getUniqueDrivers().map(d => (
                            <Select.Option key={d.id} value={d.id}>{d.name}</Select.Option>
                        ))}
                    </Select>

                    <Select
                        placeholder="Filter by Vehicle"
                        style={{ width: 180 }}
                        allowClear
                        showSearch
                        value={vehicleFilter}
                        onChange={setVehicleFilter}
                        filterOption={(input, option) =>
                            (option?.children ?? '').toLowerCase().includes(input.toLowerCase())
                        }
                    >
                        {getUniqueVehicles().map(v => (
                            <Select.Option key={v.id} value={v.id}>{v.name}</Select.Option>
                        ))}
                    </Select>

                    <DatePicker.RangePicker
                        style={{ width: 280 }}
                        value={dateRange}
                        onChange={setDateRange}
                        format="YYYY-MM-DD"
                    />

                    <Button onClick={clearFilters}>Clear Filters</Button>
                </Space>

                <Table
                    columns={columns}
                    dataSource={filteredTrips}
                    rowKey="id"
                    loading={loading}
                    pagination={{
                        ...pagination,
                        showSizeChanger: true,
                        showTotal: (total) => `Total ${total} trips`,
                        pageSizeOptions: ['10', '20', '50', '100']
                    }}
                    onChange={handleTableChange}
                />
            </Card>
        </div>
    );
};

export default TransportAdminLogistics;
