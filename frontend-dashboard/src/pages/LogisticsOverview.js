import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Table, Card, Tabs, Tag, Button, message, Modal, Timeline, Descriptions, Image, Row, Col, Space, Typography, Divider, Spin, Statistic, Alert, DatePicker, Select, Input } from 'antd';
import { ReloadOutlined, EyeOutlined, CheckCircleOutlined, ClockCircleOutlined, CarOutlined, EnvironmentOutlined, RocketOutlined, DashboardOutlined, FilterOutlined, SearchOutlined } from '@ant-design/icons';
import apiClient, { getImageUrl } from '../services/api';
import dayjs from 'dayjs';
import { useTheme } from '../context/ThemeContext';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const { Option } = Select;

const { TabPane } = Tabs;

const LogisticsOverview = () => {
    const { theme } = useTheme();
    const [stockRequests, setStockRequests] = useState([]);
    const [trips, setTrips] = useState([]);
    const [filteredTrips, setFilteredTrips] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedTrip, setSelectedTrip] = useState(null);
    const [tripDetails, setTripDetails] = useState(null);
    const [detailsLoading, setDetailsLoading] = useState(false);
    const [modalVisible, setModalVisible] = useState(false);
    
    // Filter states
    const [dateRange, setDateRange] = useState(null);
    const [statusFilter, setStatusFilter] = useState(null);
    const [varianceFilter, setVarianceFilter] = useState(null);
    const [searchText, setSearchText] = useState('');

    useEffect(() => {
        fetchData();
    }, []);
    
    const applyFilters = useCallback(() => {
        let filtered = [...trips];
        
        // Date range filter
        if (dateRange && dateRange[0] && dateRange[1]) {
            filtered = filtered.filter(trip => {
                const tripDate = dayjs(trip.created_at);
                return tripDate.isAfter(dateRange[0].startOf('day')) && tripDate.isBefore(dateRange[1].endOf('day'));
            });
        }
        
        // Status filter
        if (statusFilter) {
            filtered = filtered.filter(trip => trip.status === statusFilter);
        }
        
        // Variance filter
        if (varianceFilter) {
            filtered = filtered.filter(trip => {
                if (!trip.reconciliations || trip.reconciliations.length === 0) {
                    return false;
                }
                const recon = trip.reconciliations[0];
                const variance = Math.abs(recon.variance_pct || 0);
                
                if (varianceFilter === 'high') {
                    return variance > 0.5;
                } else if (varianceFilter === 'normal') {
                    return variance <= 0.5;
                }
                return true;
            });
        }
        
        // Search filter (vehicle, driver, MS, DBS)
        if (searchText) {
            const search = searchText.toLowerCase();
            filtered = filtered.filter(trip => 
                trip.vehicle_details?.registration_no?.toLowerCase().includes(search) ||
                trip.driver_details?.full_name?.toLowerCase().includes(search) ||
                trip.ms_details?.name?.toLowerCase().includes(search) ||
                trip.dbs_details?.name?.toLowerCase().includes(search)
            );
        }
        
        setFilteredTrips(filtered);
    }, [trips, dateRange, statusFilter, varianceFilter, searchText]);
    
    useEffect(() => {
        applyFilters();
    }, [applyFilters]);
    
    const handleResetFilters = useCallback(() => {
        setDateRange(null);
        setStatusFilter(null);
        setVarianceFilter(null);
        setSearchText('');
    }, []);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [srRes, tripsRes] = await Promise.all([
                apiClient.get('/stock-requests/'),
                apiClient.get('/trips/?limit=100')
            ]);
            const stockRequestsData = Array.isArray(srRes?.data?.results) ? srRes.data.results :
                                      Array.isArray(srRes?.data) ? srRes.data : [];
            const tripsData = Array.isArray(tripsRes?.data?.results) ? tripsRes.data.results :
                              Array.isArray(tripsRes?.data) ? tripsRes.data : [];
            
            setStockRequests(stockRequestsData);
            setTrips(tripsData);
        } catch (error) {
            message.error('Failed to load logistics data. Please try again.');
            setStockRequests([]);
            setTrips([]);
        } finally {
            setLoading(false);
        }
    }, []);

    const fetchTripDetails = useCallback(async (tripId) => {
        if (!tripId) {
            message.error('Invalid trip ID');
            return;
        }
        setDetailsLoading(true);
        try {
            const [tripRes, fillingsRes, decantingsRes, reconciliationRes] = await Promise.all([
                apiClient.get(`/trips/${tripId}/`),
                apiClient.get(`/trips/${tripId}/ms-fillings/`).catch(() => ({ data: [] })),
                apiClient.get(`/trips/${tripId}/dbs-decantings/`).catch(() => ({ data: [] })),
                apiClient.get(`/trips/${tripId}/reconciliations/`).catch(() => ({ data: [] }))
            ]);
            
            const msFillings = Array.isArray(fillingsRes?.data?.results) ? fillingsRes.data.results :
                               Array.isArray(fillingsRes?.data) ? fillingsRes.data : [];
            const dbsDecantings = Array.isArray(decantingsRes?.data?.results) ? decantingsRes.data.results :
                                  Array.isArray(decantingsRes?.data) ? decantingsRes.data : [];
            const reconciliations = Array.isArray(reconciliationRes?.data?.results) ? reconciliationRes.data.results :
                                    Array.isArray(reconciliationRes?.data) ? reconciliationRes.data : [];
            
            setTripDetails({
                ...(tripRes?.data || {}),
                ms_fillings: msFillings,
                dbs_decantings: dbsDecantings,
                reconciliations: reconciliations
            });
            setModalVisible(true);
        } catch (error) {
            message.error('Failed to load trip details. Please try again.');
            setTripDetails(null);
        } finally {
            setDetailsLoading(false);
        }
    }, []);

    const handleViewDetails = useCallback((trip) => {
        setSelectedTrip(trip);
        setModalVisible(true);
        setTripDetails(null); // Clear previous details
        fetchTripDetails(trip.id);
    }, [fetchTripDetails]);

    const srColumns = [
        { title: 'ID', dataIndex: 'id', key: 'id' },
        { title: 'DBS', dataIndex: ['dbs_details', 'name'], key: 'dbs' },
        { title: 'Source', dataIndex: 'source', key: 'source' },
        // { title: 'Qty (Kg)', dataIndex: 'requested_qty_kg', key: 'qty' },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                let color = 'default';
                if (status === 'PENDING') color = 'orange';
                if (status === 'APPROVED') color = 'green';
                if (status === 'REJECTED') color = 'red';
                return <Tag color={color}>{status}</Tag>;
            }
        },
        {
            title: 'Created At',
            dataIndex: 'created_at',
            key: 'created_at',
            render: (date) => dayjs(date).format('YYYY-MM-DD HH:mm')
        },
    ];

    const tripColumns = [
        { title: 'Trip ID', dataIndex: 'id', key: 'id', width: 80 },
        { title: 'Vehicle', key: 'vehicle', render: (_, record) => record?.vehicle_details?.registration_no || 'N/A' },
        { title: 'Driver', key: 'driver', render: (_, record) => record?.driver_details?.full_name || 'N/A' },
        { title: 'From (MS)', key: 'ms', render: (_, record) => record?.ms_details?.name || 'N/A' },
        { title: 'To (DBS)', key: 'dbs', render: (_, record) => record?.dbs_details?.name || 'N/A' },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            render: (status) => {
                let color = 'blue';
                if (status === 'COMPLETED') color = 'green';
                if (status === 'CANCELLED') color = 'red';
                if (status === 'PENDING') color = 'orange';
                return <Tag color={color}>{status}</Tag>;
            }
        },
        {
            title: 'Last Update',
            key: 'updated',
            render: (_, record) => {
                if (record.completed_at) return dayjs(record.completed_at).format('HH:mm');
                if (record.dbs_arrival_at) return `Arr DBS ${dayjs(record.dbs_arrival_at).format('HH:mm')}`;
                if (record.origin_confirmed_at) return `Arr MS ${dayjs(record.origin_confirmed_at).format('HH:mm')}`;
                return '-';
            }
        },
        {
            title: 'Action',
            key: 'action',
            width: 100,
            render: (_, record) => (
                <Button 
                    type="primary" 
                    icon={<EyeOutlined />} 
                    size="small"
                    onClick={() => handleViewDetails(record)}
                >
                    View
                </Button>
            )
        },
    ];

    const renderTripTimeline = () => {
        if (!tripDetails) return null;

        const items = [];

        // Trip Created
        if (tripDetails.created_at) {
            items.push({
                color: 'blue',
                dot: <ClockCircleOutlined />,
                children: (
                    <div>
                        <Text strong>Trip Created</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.created_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // Trip Started/Accepted
        if (tripDetails.started_at) {
            items.push({
                color: 'green',
                dot: <CheckCircleOutlined />,
                children: (
                    <div>
                        <Text strong>Trip Accepted by Driver</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.started_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // Arrived at MS
        if (tripDetails.origin_confirmed_at) {
            items.push({
                color: 'cyan',
                dot: <EnvironmentOutlined />,
                children: (
                    <div>
                        <Text strong>Arrived at MS ({tripDetails.ms_details?.name})</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.origin_confirmed_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // MS Filling
        if (tripDetails.ms_fillings && tripDetails.ms_fillings.length > 0) {
            const filling = tripDetails.ms_fillings[0];
            items.push({
                color: 'purple',
                children: (
                    <div>
                        <Text strong>MS Filling Completed</Text>
                        <br />
                        <Text type="secondary">
                            {filling.start_time && `Started: ${dayjs(filling.start_time).format('HH:mm:ss')}`}
                            {filling.end_time && ` | Ended: ${dayjs(filling.end_time).format('HH:mm:ss')}`}
                        </Text>
                        <br />
                        <Text>Filled Qty: <Text strong>{filling.filled_qty_kg || 'N/A'} kg</Text></Text>
                    </div>
                )
            });
        }

        // Departed MS
        if (tripDetails.ms_departure_at) {
            items.push({
                color: 'orange',
                dot: <CarOutlined />,
                children: (
                    <div>
                        <Text strong>Departed from MS</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.ms_departure_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // Arrived at DBS
        if (tripDetails.dbs_arrival_at) {
            items.push({
                color: 'cyan',
                dot: <EnvironmentOutlined />,
                children: (
                    <div>
                        <Text strong>Arrived at DBS ({tripDetails.dbs_details?.name})</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.dbs_arrival_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // DBS Decanting
        if (tripDetails.dbs_decantings && tripDetails.dbs_decantings.length > 0) {
            const decanting = tripDetails.dbs_decantings[0];
            items.push({
                color: 'purple',
                children: (
                    <div>
                        <Text strong>DBS Decanting Completed</Text>
                        <br />
                        <Text type="secondary">
                            {decanting.start_time && `Started: ${dayjs(decanting.start_time).format('HH:mm:ss')}`}
                            {decanting.end_time && ` | Ended: ${dayjs(decanting.end_time).format('HH:mm:ss')}`}
                        </Text>
                        <br />
                        <Text>Delivered Qty: <Text strong>{decanting.delivered_qty_kg || 'N/A'} kg</Text></Text>
                    </div>
                )
            });
        }

        // Departed DBS
        if (tripDetails.dbs_departure_at) {
            items.push({
                color: 'orange',
                dot: <CarOutlined />,
                children: (
                    <div>
                        <Text strong>Departed from DBS</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.dbs_departure_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // Returned to MS
        if (tripDetails.ms_return_at) {
            items.push({
                color: 'cyan',
                dot: <EnvironmentOutlined />,
                children: (
                    <div>
                        <Text strong>Returned to MS</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.ms_return_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        // Trip Completed
        if (tripDetails.completed_at) {
            items.push({
                color: 'green',
                dot: <CheckCircleOutlined />,
                children: (
                    <div>
                        <Text strong>Trip Completed</Text>
                        <br />
                        <Text type="secondary">{dayjs(tripDetails.completed_at).format('YYYY-MM-DD HH:mm:ss')}</Text>
                    </div>
                )
            });
        }

        return <Timeline items={items} />;
    };

    return (
        <div style={{ padding: 24, background: theme.token.colorBgLayout, minHeight: '100vh' }}>
            {/* Header */}
            <div style={{ marginBottom: 24 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                    <div>
                        <Title level={2} style={{ margin: 0 }}>
                            <DashboardOutlined /> Logistics Overview
                        </Title>
                        <Text type="secondary">Monitor trips and stock requests in real-time</Text>
                    </div>
                    <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>Refresh</Button>
                </div>

                {/* Stats Cards */}
                <Row gutter={16} style={{ marginBottom: 16 }}>
                    <Col xs={24} sm={12} lg={6}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Total Trips" 
                                value={trips.length} 
                                prefix={<RocketOutlined />}
                                valueStyle={{ color: '#3f8600' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Active Trips" 
                                value={trips.filter(t => !['COMPLETED', 'CANCELLED'].includes(t.status)).length}
                                valueStyle={{ color: '#1890ff' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={24} sm={12} lg={6}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Completed" 
                                value={trips.filter(t => t.status === 'COMPLETED').length}
                                valueStyle={{ color: '#52c41a' }}
                            />
                        </Card>
                    </Col>
                    {/* <Col xs={24} sm={12} lg={6}>
                        <Card size="small" style={{ borderRadius: 8 }}>
                            <Statistic 
                                title="Stock Requests" 
                                value={stockRequests.length}
                                valueStyle={{ color: '#faad14' }}
                            />
                        </Card>
                    </Col> */}
                </Row>
            </div>

            <Card style={{ borderRadius: 12, boxShadow: theme.card.boxShadow }}>
                <Tabs defaultActiveKey="1">
                    <TabPane tab={`Trips (${filteredTrips.length})`} key="1">
                        {/* Filters */}
                        <Card size="small" style={{ marginBottom: 16, background: theme.token.colorBgContainer }}>
                            <Row gutter={[16, 16]}>
                                <Col xs={24} sm={12} md={6}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>Date Range</Text>
                                    <RangePicker 
                                        style={{ width: '100%' }}
                                        value={dateRange}
                                        onChange={setDateRange}
                                        format="YYYY-MM-DD"
                                    />
                                </Col>
                                <Col xs={24} sm={12} md={6}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>Status</Text>
                                    <Select
                                        style={{ width: '100%' }}
                                        placeholder="All Status"
                                        allowClear
                                        value={statusFilter}
                                        onChange={setStatusFilter}
                                    >
                                        <Option value="PENDING">Pending</Option>
                                        <Option value="AT_MS">At MS</Option>
                                        <Option value="IN_TRANSIT">In Transit</Option>
                                        <Option value="AT_DBS">At DBS</Option>
                                        {/* <Option value="DECANTING_CONFIRMED">Decanting Confirmed</Option>
                                        <Option value="RETURNED_TO_MS">Returned to MS</Option> */}
                                        <Option value="COMPLETED">Completed</Option>
                                        <Option value="CANCELLED">Cancelled</Option>
                                    </Select>
                                </Col>
                                <Col xs={24} sm={12} md={6}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>Variance</Text>
                                    <Select
                                        style={{ width: '100%' }}
                                        placeholder="All Variance"
                                        allowClear
                                        value={varianceFilter}
                                        onChange={setVarianceFilter}
                                    >
                                        <Option value="high">High (&gt;0.5%)</Option>
                                        <Option value="normal">Normal (&lt;0.5%)</Option>
                                    </Select>
                                </Col>
                                <Col xs={24} sm={12} md={6}>
                                    <Text type="secondary" style={{ fontSize: 12 }}>Search</Text>
                                    <Input
                                        placeholder="Vehicle, Driver, Station..."
                                        prefix={<SearchOutlined />}
                                        value={searchText}
                                        onChange={(e) => setSearchText(e.target.value)}
                                        allowClear
                                    />
                                </Col>
                            </Row>
                            <Row style={{ marginTop: 12 }}>
                                <Col span={24}>
                                    <Space>
                                        <Button 
                                            size="small" 
                                            icon={<FilterOutlined />}
                                            onClick={handleResetFilters}
                                        >
                                            Reset Filters
                                        </Button>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            Showing {filteredTrips.length} of {trips.length} trips
                                        </Text>
                                    </Space>
                                </Col>
                            </Row>
                        </Card>
                        
                        <Table
                            columns={tripColumns}
                            dataSource={filteredTrips}
                            rowKey="id"
                            loading={loading}
                            pagination={{ 
                                defaultPageSize: 20, 
                                showSizeChanger: true,
                                pageSizeOptions: ['20', '50', '100'],
                                showTotal: (total) => `Total ${total} trips`
                            }}
                        />
                    </TabPane>
                    {/* <TabPane tab={`Stock Requests (${stockRequests.length})`} key="2">
                        <Table
                            columns={srColumns}
                            dataSource={stockRequests}
                            rowKey="id"
                            loading={loading}
                            pagination={{ 
                                defaultPageSize: 20, 
                                showSizeChanger: true,
                                pageSizeOptions: ['20', '50', '100'],
                                showTotal: (total) => `Total ${total} requests`
                            }}
                        />
                    </TabPane> */}
                </Tabs>
            </Card>

            <Modal
                title={
                    <Space>
                        <RocketOutlined />
                        <span>Trip #{selectedTrip?.id}</span>
                        {tripDetails?.token_details?.token_no && <Text type="secondary">({tripDetails.token_details.token_no})</Text>}
                        {selectedTrip && (
                            <Tag color={selectedTrip.status === 'COMPLETED' ? 'green' : 'blue'}>
                                {selectedTrip.status}
                            </Tag>
                        )}
                    </Space>
                }
                open={modalVisible}
                onCancel={() => setModalVisible(false)}
                width={1200}
                footer={[
                    <Button key="close" onClick={() => setModalVisible(false)}>
                        Close
                    </Button>
                ]}
            >
                {detailsLoading ? (
                    <div style={{ textAlign: 'center', padding: '80px 0' }}>
                        <Spin size="large" />
                        <div style={{ marginTop: 16 }}>
                            <Text type="secondary">Loading trip details...</Text>
                        </div>
                    </div>
                ) : tripDetails ? (
                    <div>
                        {/* Basic Info */}
                        <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
                            <Descriptions.Item label="Vehicle">{tripDetails.vehicle_details?.registration_no}</Descriptions.Item>
                            <Descriptions.Item label="Driver">{tripDetails.driver_details?.full_name}</Descriptions.Item>
                            <Descriptions.Item label="From (MS)">{tripDetails.ms_details?.name}</Descriptions.Item>
                            <Descriptions.Item label="To (DBS)">{tripDetails.dbs_details?.name}</Descriptions.Item>
                            <Descriptions.Item label="Token">{tripDetails.token_details?.token_no || 'N/A'}</Descriptions.Item>
                            <Descriptions.Item label="Created">{dayjs(tripDetails.created_at).format('YYYY-MM-DD HH:mm')}</Descriptions.Item>
                        </Descriptions>

                        <Row gutter={16}>
                            {/* Timeline */}
                            <Col xs={24} lg={12}>
                                <Card title="Trip Timeline" size="small" style={{ marginBottom: 16 }}>
                                    {renderTripTimeline()}
                                </Card>

                                {/* Reconciliation */}
                                {tripDetails.reconciliations && tripDetails.reconciliations.length > 0 && (
                                    <Card title="Reconciliation" size="small">
                                        {tripDetails.reconciliations.map((recon, idx) => (
                                            <div key={idx}>
                                                <Row gutter={[8, 8]}>
                                                    <Col span={12}>
                                                        <Statistic 
                                                            title="MS Filled" 
                                                            value={recon.ms_filled_qty_kg} 
                                                            suffix="kg"
                                                            valueStyle={{ fontSize: 18 }}
                                                        />
                                                    </Col>
                                                    <Col span={12}>
                                                        <Statistic 
                                                            title="DBS Delivered" 
                                                            value={recon.dbs_delivered_qty_kg} 
                                                            suffix="kg"
                                                            valueStyle={{ fontSize: 18 }}
                                                        />
                                                    </Col>
                                                    <Col span={12}>
                                                        <Statistic 
                                                            title="Difference" 
                                                            value={recon.diff_qty} 
                                                            suffix="kg"
                                                            valueStyle={{ 
                                                                fontSize: 18,
                                                                color: Math.abs(recon.diff_qty) > 0 ? '#ff4d4f' : '#52c41a'
                                                            }}
                                                        />
                                                    </Col>
                                                    <Col span={12}>
                                                        <Statistic 
                                                            title="Variance" 
                                                            value={recon.variance_pct} 
                                                            suffix="%"
                                                            valueStyle={{ 
                                                                fontSize: 18,
                                                                color: Math.abs(recon.variance_pct) > 0.5 ? '#ff4d4f' : '#52c41a'
                                                            }}
                                                        />
                                                    </Col>
                                                </Row>
                                                <Divider style={{ margin: '12px 0' }} />
                                                <div style={{ textAlign: 'center' }}>
                                                    <Tag color={recon.status === 'OK' ? 'green' : 'red'} style={{ fontSize: 14, padding: '4px 12px' }}>
                                                        {recon.status}
                                                    </Tag>
                                                </div>
                                            </div>
                                        ))}
                                    </Card>
                                )}
                            </Col>

                            {/* Images & Details */}
                            <Col xs={24} lg={12}>
                                {/* MS Filling */}
                                {tripDetails.ms_fillings && tripDetails.ms_fillings.length > 0 && (
                                    <Card title="MS Filling" size="small" style={{ marginBottom: 16 }}>
                                        {tripDetails.ms_fillings.map((filling, idx) => (
                                            <div key={idx}>
                                                <Descriptions column={1} size="small" bordered>
                                                    <Descriptions.Item label="Pre-fill Pressure">{filling.prefill_pressure_bar} bar</Descriptions.Item>
                                                    <Descriptions.Item label="Post-fill Pressure">{filling.postfill_pressure_bar} bar</Descriptions.Item>
                                                    <Descriptions.Item label="Pre-fill MFM">{filling.prefill_mfm}</Descriptions.Item>
                                                    <Descriptions.Item label="Post-fill MFM">{filling.postfill_mfm}</Descriptions.Item>
                                                    <Descriptions.Item label="Filled Qty"><Text strong>{filling.filled_qty_kg} kg</Text></Descriptions.Item>
                                                </Descriptions>
                                                <Divider orientation="left">Driver Photos</Divider>
                                                <Space>
                                                    {filling.prefill_photo && (
                                                        <div>
                                                            <Text type="secondary">Pre-fill</Text><br />
                                                            <Image width={120} src={getImageUrl(filling.prefill_photo)} />
                                                        </div>
                                                    )}
                                                    {filling.postfill_photo && (
                                                        <div>
                                                            <Text type="secondary">Post-fill</Text><br />
                                                            <Image width={120} src={getImageUrl(filling.postfill_photo)} />
                                                        </div>
                                                    )}
                                                </Space>
                                                {(filling.prefill_photo_operator || filling.postfill_photo_operator) && (
                                                    <>
                                                        <Divider orientation="left">MS Operator Photos</Divider>
                                                        <Space>
                                                            {filling.prefill_photo_operator && (
                                                                <div>
                                                                    <Text type="secondary">Pre-fill</Text><br />
                                                                    <Image width={120} src={getImageUrl(filling.prefill_photo_operator)} />
                                                                </div>
                                                            )}
                                                            {filling.postfill_photo_operator && (
                                                                <div>
                                                                    <Text type="secondary">Post-fill</Text><br />
                                                                    <Image width={120} src={getImageUrl(filling.postfill_photo_operator)} />
                                                                </div>
                                                            )}
                                                        </Space>
                                                    </>
                                                )}
                                            </div>
                                        ))}
                                    </Card>
                                )}

                                {/* DBS Decanting */}
                                {tripDetails.dbs_decantings && tripDetails.dbs_decantings.length > 0 && (
                                    <Card title="DBS Decanting" size="small">
                                        {tripDetails.dbs_decantings.map((decanting, idx) => (
                                            <div key={idx}>
                                                <Descriptions column={1} size="small" bordered>
                                                    <Descriptions.Item label="Pre-decant Pressure">{decanting.pre_dec_pressure_bar} bar</Descriptions.Item>
                                                    <Descriptions.Item label="Post-decant Pressure">{decanting.post_dec_pressure_bar} bar</Descriptions.Item>
                                                    <Descriptions.Item label="Pre-decant Reading">{decanting.pre_dec_reading}</Descriptions.Item>
                                                    <Descriptions.Item label="Post-decant Reading">{decanting.post_dec_reading}</Descriptions.Item>
                                                    <Descriptions.Item label="Delivered Qty"><Text strong>{decanting.delivered_qty_kg} kg</Text></Descriptions.Item>
                                                </Descriptions>
                                                <Divider orientation="left">Driver Photos</Divider>
                                                <Space>
                                                    {decanting.pre_decant_photo && (
                                                        <div>
                                                            <Text type="secondary">Pre-decant</Text><br />
                                                            <Image width={120} src={getImageUrl(decanting.pre_decant_photo)} />
                                                        </div>
                                                    )}
                                                    {decanting.post_decant_photo && (
                                                        <div>
                                                            <Text type="secondary">Post-decant</Text><br />
                                                            <Image width={120} src={getImageUrl(decanting.post_decant_photo)} />
                                                        </div>
                                                    )}
                                                </Space>
                                                {(decanting.pre_decant_photo_operator || decanting.post_decant_photo_operator) && (
                                                    <>
                                                        <Divider orientation="left">DBS Operator Photos</Divider>
                                                        <Space>
                                                            {decanting.pre_decant_photo_operator && (
                                                                <div>
                                                                    <Text type="secondary">Pre-decant</Text><br />
                                                                    <Image width={120} src={getImageUrl(decanting.pre_decant_photo_operator)} />
                                                                </div>
                                                            )}
                                                            {decanting.post_decant_photo_operator && (
                                                                <div>
                                                                    <Text type="secondary">Post-decant</Text><br />
                                                                    <Image width={120} src={getImageUrl(decanting.post_decant_photo_operator)} />
                                                                </div>
                                                            )}
                                                        </Space>
                                                    </>
                                                )}
                                            </div>
                                        ))}
                                    </Card>
                                )}
                            </Col>
                        </Row>
                    </div>
                ) : null}
            </Modal>
        </div>
    );
};

export default LogisticsOverview;
