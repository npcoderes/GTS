import React, { useState, useEffect, useCallback } from 'react';
import {
    Card, Table, Button, Modal, message, DatePicker, Tag, Space, Typography,
    Tooltip, Row, Col, Spin, Badge, Input, Empty, Descriptions, Image, Tabs, Statistic
} from 'antd';
import {
    CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
    CalendarOutlined, UserOutlined, CarOutlined, FileOutlined,
    ReloadOutlined, EyeOutlined, LeftOutlined, RightOutlined,
    IdcardOutlined, PhoneOutlined, SafetyCertificateOutlined,
    HistoryOutlined, ExclamationCircleOutlined
} from '@ant-design/icons';
import apiClient from '../services/api';
import moment from 'moment';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

const EICShiftApprovals = () => {
    // State
    const [loading, setLoading] = useState(false);
    const [pendingApprovals, setPendingApprovals] = useState([]);
    const [weekStart, setWeekStart] = useState(moment().startOf('week'));
    const [selectedApproval, setSelectedApproval] = useState(null);
    const [isDetailModalVisible, setIsDetailModalVisible] = useState(false);
    const [isRejectModalVisible, setIsRejectModalVisible] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [actionLoading, setActionLoading] = useState(false);
    const [isPendingListModalVisible, setIsPendingListModalVisible] = useState(false);
    
    // History state
    const [activeTab, setActiveTab] = useState('pending');
    const [historyLoading, setHistoryLoading] = useState(false);
    const [historyShifts, setHistoryShifts] = useState([]);
    const [historyCounts, setHistoryCounts] = useState({ approved: 0, rejected: 0, expired: 0 });
    const [historyPagination, setHistoryPagination] = useState({ page: 1, pageSize: 20, total: 0 });
    const [dateRange, setDateRange] = useState(null);

    // Fetch pending approvals
    const fetchPendingApprovals = useCallback(async () => {
        setLoading(true);
        try {
            const response = await apiClient.get('/eic/driver-approvals/pending');
            setPendingApprovals(response.data.pending || []);
        } catch (error) {
            console.error('Failed to fetch pending approvals:', error);
            message.error('Failed to load pending approvals');
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch shift history (approved, rejected, expired)
    const fetchShiftHistory = useCallback(async (status = null, page = 1, pageSize = 20) => {
        setHistoryLoading(true);
        try {
            const params = new URLSearchParams();
            if (status) params.append('status', status);
            params.append('page', page);
            params.append('page_size', pageSize);
            
            if (dateRange && dateRange[0] && dateRange[1]) {
                params.append('start_date', dateRange[0].format('YYYY-MM-DD'));
                params.append('end_date', dateRange[1].format('YYYY-MM-DD'));
            }
            
            const response = await apiClient.get(`/eic/driver-approvals/history?${params.toString()}`);
            setHistoryShifts(response.data.shifts || []);
            setHistoryCounts(response.data.counts || { approved: 0, rejected: 0, expired: 0 });
            setHistoryPagination({
                page: response.data.pagination?.page || 1,
                pageSize: response.data.pagination?.page_size || 20,
                total: response.data.pagination?.total_count || 0
            });
        } catch (error) {
            console.error('Failed to fetch shift history:', error);
            message.error('Failed to load shift history');
        } finally {
            setHistoryLoading(false);
        }
    }, [dateRange]);

    useEffect(() => {
        fetchPendingApprovals();
        fetchShiftHistory(); // Also fetch history counts on load
    }, [fetchPendingApprovals, fetchShiftHistory]);

    // When tab changes, fetch appropriate data
    useEffect(() => {
        if (activeTab === 'pending') {
            fetchPendingApprovals();
        } else if (activeTab === 'approved') {
            fetchShiftHistory('APPROVED');
        } else if (activeTab === 'rejected') {
            fetchShiftHistory('REJECTED');
        } else if (activeTab === 'expired') {
            fetchShiftHistory('EXPIRED');
        }
    }, [activeTab, fetchPendingApprovals, fetchShiftHistory]);

    // Navigation
    const goToPreviousWeek = () => setWeekStart(prev => prev.clone().subtract(1, 'week'));
    const goToNextWeek = () => setWeekStart(prev => prev.clone().add(1, 'week'));
    const goToCurrentWeek = () => setWeekStart(moment().startOf('week'));

    // Filter approvals by current week
    const filteredApprovals = pendingApprovals.filter(approval => {
        if (!approval.shiftDate) return true;
        const shiftDate = moment(approval.shiftDate);
        const weekEnd = weekStart.clone().add(6, 'days');
        return shiftDate.isBetween(weekStart, weekEnd, 'day', '[]');
    });

    // Group by date for timesheet view
    const groupedByDate = {};
    const dates = [];
    for (let i = 0; i < 7; i++) {
        const date = weekStart.clone().add(i, 'days').format('YYYY-MM-DD');
        dates.push(date);
        groupedByDate[date] = filteredApprovals.filter(a => a.shiftDate === date);
    }

    // View details
    const handleViewDetails = (approval) => {
        setSelectedApproval(approval);
        setIsDetailModalVisible(true);
    };

    // Approve shift
    const handleApprove = async (shiftId) => {
        setActionLoading(true);
        try {
            await apiClient.post(`/shifts/${shiftId}/approve/`);
            message.success('Shift approved successfully');
            setIsDetailModalVisible(false);
            fetchPendingApprovals();
        } catch (error) {
            console.error('Failed to approve shift:', error);
            message.error(error.response?.data?.message || 'Failed to approve shift');
        } finally {
            setActionLoading(false);
        }
    };

    // Open reject modal
    const handleOpenReject = () => {
        setRejectReason('');
        setIsRejectModalVisible(true);
    };

    // Submit reject
    const handleReject = async () => {
        if (!selectedApproval) return;
        setActionLoading(true);
        try {
            await apiClient.post(`/shifts/${selectedApproval.shiftId}/reject/`, {
                reason: rejectReason || 'Rejected by EIC'
            });
            message.success('Shift rejected');
            setIsRejectModalVisible(false);
            setIsDetailModalVisible(false);
            fetchPendingApprovals();
        } catch (error) {
            console.error('Failed to reject shift:', error);
            message.error('Failed to reject shift');
        } finally {
            setActionLoading(false);
        }
    };

    // Quick approve from table
    const handleQuickApprove = async (shiftId, e) => {
        e.stopPropagation();
        try {
            await apiClient.post(`/shifts/${shiftId}/approve/`);
            message.success('Shift approved');
            fetchPendingApprovals();
        } catch (error) {
            message.error('Failed to approve shift');
        }
    };

    // Table columns
    const columns = [
        {
            title: 'Driver',
            key: 'driver',
            width: 200,
            render: (_, record) => (
                <div>
                    <Text strong><UserOutlined style={{ marginRight: 8 }} />{record.name}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        <PhoneOutlined style={{ marginRight: 4 }} />{record.phone}
                    </Text>
                </div>
            )
        },
        {
            title: 'License',
            key: 'license',
            width: 180,
            render: (_, record) => (
                <div>
                    <Text><IdcardOutlined style={{ marginRight: 8 }} />{record.licenseNumber}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        Exp: {record.licenseExpiry ? moment(record.licenseExpiry).format('DD MMM YYYY') : 'N/A'}
                    </Text>
                    {record.licenseDocument && (
                        <Tooltip title="View License Document">
                            <Button
                                type="link"
                                size="small"
                                icon={<FileOutlined />}
                                onClick={(e) => { e.stopPropagation(); window.open(record.licenseDocument, '_blank'); }}
                            />
                        </Tooltip>
                    )}
                </div>
            )
        },
        {
            title: 'Vehicle',
            key: 'vehicle',
            width: 150,
            render: (_, record) => (
                <div>
                    <Text><CarOutlined style={{ marginRight: 8 }} />{record.vehicleNumber || 'Not Assigned'}</Text>
                    {record.vehicleDocument && (
                        <Tooltip title="View Registration Document">
                            <Button
                                type="link"
                                size="small"
                                icon={<FileOutlined />}
                                onClick={(e) => { e.stopPropagation(); window.open(record.vehicleDocument, '_blank'); }}
                            />
                        </Tooltip>
                    )}
                </div>
            )
        },
        {
            title: 'Shift',
            key: 'shift',
            width: 180,
            render: (_, record) => (
                <div>
                    <Tag color="blue">{record.preferredShift}</Tag>
                    <br />
                    <Text style={{ fontSize: 12 }}>
                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                        {record.requestedShiftStart} - {record.requestedShiftEnd}
                    </Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                        <CalendarOutlined style={{ marginRight: 4 }} />
                        {record.shiftDate ? moment(record.shiftDate).format('DD MMM YYYY') : 'N/A'}
                    </Text>
                </div>
            )
        },
        {
            title: 'Verification',
            key: 'verification',
            width: 140,
            render: (_, record) => (
                <Space direction="vertical" size={2}>
                    <Badge
                        status={record.trainingCompleted ? 'success' : 'warning'}
                        text={<Text style={{ fontSize: 12 }}>Training: {record.trainingCompleted ? 'Done' : 'Pending'}</Text>}
                    />
                    <Badge
                        status={record.licenseVerified ? 'success' : 'warning'}
                        text={<Text style={{ fontSize: 12 }}>License: {record.licenseVerified ? 'Verified' : 'Pending'}</Text>}
                    />
                </Space>
            )
        },
        {
            title: 'Created By',
            key: 'createdBy',
            width: 150,
            render: (_, record) => (
                <div>
                    <Text>{record.createdBy}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 11 }}>
                        {record.createdAt ? moment(record.createdAt).format('DD MMM HH:mm') : ''}
                    </Text>
                </div>
            )
        },
        {
            title: 'Actions',
            key: 'actions',
            width: 180,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    <Tooltip title="View Details">
                        <Button
                            type="default"
                            icon={<EyeOutlined />}
                            onClick={() => handleViewDetails(record)}
                        />
                    </Tooltip>
                    <Tooltip title="Approve">
                        <Button
                            type="primary"
                            icon={<CheckCircleOutlined />}
                            onClick={(e) => handleQuickApprove(record.shiftId, e)}
                            style={{ background: '#52c41a', borderColor: '#52c41a' }}
                        />
                    </Tooltip>
                    <Tooltip title="Reject">
                        <Button
                            danger
                            icon={<CloseCircleOutlined />}
                            onClick={(e) => { e.stopPropagation(); setSelectedApproval(record); handleOpenReject(); }}
                        />
                    </Tooltip>
                </Space>
            )
        }
    ];

    // History table columns
    const historyColumns = [
        {
            title: 'Driver',
            key: 'driver',
            width: 180,
            render: (_, record) => (
                <div>
                    <Text strong><UserOutlined style={{ marginRight: 8 }} />{record.driverName}</Text>
                    <br />
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        <PhoneOutlined style={{ marginRight: 4 }} />{record.driverPhone}
                    </Text>
                </div>
            )
        },
        {
            title: 'Vehicle',
            key: 'vehicle',
            width: 130,
            render: (_, record) => (
                <Tag icon={<CarOutlined />} color="blue">{record.vehicleNumber || 'N/A'}</Tag>
            )
        },
        {
            title: 'Shift Date',
            dataIndex: 'shiftDate',
            key: 'shiftDate',
            width: 120,
            render: (date) => (
                <Tag color="cyan">
                    <CalendarOutlined /> {date ? moment(date).format('DD MMM YYYY') : 'N/A'}
                </Tag>
            ),
            sorter: (a, b) => moment(a.shiftDate).unix() - moment(b.shiftDate).unix()
        },
        {
            title: 'Shift Time',
            key: 'shiftTime',
            width: 140,
            render: (_, record) => (
                <Space direction="vertical" size={0}>
                    <Tag color="green">{record.shiftType}</Tag>
                    <Text style={{ fontSize: 12 }}>
                        <ClockCircleOutlined /> {record.startTime} - {record.endTime}
                    </Text>
                </Space>
            )
        },
        {
            title: 'Status',
            dataIndex: 'status',
            key: 'status',
            width: 110,
            render: (status) => {
                const config = {
                    APPROVED: { color: 'success', icon: <CheckCircleOutlined /> },
                    REJECTED: { color: 'error', icon: <CloseCircleOutlined /> },
                    EXPIRED: { color: 'warning', icon: <ExclamationCircleOutlined /> }
                };
                return (
                    <Tag color={config[status]?.color} icon={config[status]?.icon}>
                        {status}
                    </Tag>
                );
            },
            filters: [
                { text: 'Approved', value: 'APPROVED' },
                { text: 'Rejected', value: 'REJECTED' },
                { text: 'Expired', value: 'EXPIRED' }
            ],
            onFilter: (value, record) => record.status === value
        },
        {
            title: 'Processed By',
            key: 'processedBy',
            width: 150,
            render: (_, record) => (
                <Space direction="vertical" size={0}>
                    <Text>{record.approvedBy || record.createdBy || 'System'}</Text>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                        {record.approvedAt ? moment(record.approvedAt).format('DD MMM, HH:mm') : 
                         record.updatedAt ? moment(record.updatedAt).format('DD MMM, HH:mm') : ''}
                    </Text>
                </Space>
            )
        },
        {
            title: 'Reason',
            dataIndex: 'rejectedReason',
            key: 'rejectedReason',
            width: 200,
            render: (reason) => reason ? (
                <Tooltip title={reason}>
                    <Text ellipsis style={{ maxWidth: 180 }}>{reason}</Text>
                </Tooltip>
            ) : '-'
        }
    ];

    // Render pending content
    const renderPendingContent = () => (
        <>
            {/* Week Navigation */}
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: 16,
                marginBottom: 24,
                padding: '12px 24px',
                background: '#f9f9fb',
                borderRadius: 8
            }}>
                <Button icon={<LeftOutlined />} onClick={goToPreviousWeek} size="large" />
                <div style={{ textAlign: 'center', minWidth: 200 }}>
                    <Text strong style={{ fontSize: 16 }}>
                        {weekStart.format('MMM D')} - {weekStart.clone().add(6, 'days').format('MMM D, YYYY')}
                    </Text>
                </div>
                <Button icon={<RightOutlined />} onClick={goToNextWeek} size="large" />
                <Button type="primary" onClick={goToCurrentWeek} style={{ marginLeft: 16 }}>
                    This Week
                </Button>
            </div>

            {/* Stats Cards */}
            <Row gutter={16} style={{ marginBottom: 24 }}>
                {dates.map(date => {
                    const count = groupedByDate[date]?.length || 0;
                    const isToday = moment(date).isSame(moment(), 'day');
                    return (
                        <Col span={Math.floor(24 / 7)} key={date}>
                            <Card
                                size="small"
                                style={{
                                    textAlign: 'center',
                                    borderColor: isToday ? '#1890ff' : '#f0f0f0',
                                    background: isToday ? '#e6f7ff' : count > 0 ? '#fff7e6' : '#fff'
                                }}
                            >
                                <Text strong style={{ color: isToday ? '#1890ff' : '#333' }}>
                                    {moment(date).format('ddd')}
                                </Text>
                                <br />
                                <Text style={{ fontSize: 18, fontWeight: 600 }}>
                                    {moment(date).format('D')}
                                </Text>
                                <br />
                                {count > 0 && (
                                    <Badge count={count} style={{ backgroundColor: '#faad14' }} />
                                )}
                            </Card>
                        </Col>
                    );
                })}
            </Row>

            {/* Approvals Table */}
            <Spin spinning={loading}>
                {filteredApprovals.length > 0 ? (
                    <Table
                        columns={columns}
                        dataSource={filteredApprovals}
                        rowKey="shiftId"
                        pagination={{ pageSize: 10 }}
                        scroll={{ x: 'max-content' }}
                        bordered
                        size="middle"
                        style={{ borderRadius: 8, overflow: 'hidden' }}
                        onRow={(record) => ({
                            onClick: () => handleViewDetails(record),
                            style: { cursor: 'pointer' }
                        })}
                    />
                ) : (
                    <Empty
                        description="No pending shift approvals for this week"
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        style={{ padding: 60 }}
                    />
                )}
            </Spin>
        </>
    );

    // Render history content
    const renderHistoryContent = (statusFilter) => (
        <>
            {/* Date Filter */}
            <div style={{ marginBottom: 16 }}>
                <Space>
                    <Text>Filter by Date:</Text>
                    <RangePicker
                        value={dateRange}
                        onChange={(dates) => {
                            setDateRange(dates);
                            if (dates) {
                                fetchShiftHistory(statusFilter);
                            }
                        }}
                        allowClear
                    />
                    <Button 
                        icon={<ReloadOutlined />} 
                        onClick={() => fetchShiftHistory(statusFilter)}
                        loading={historyLoading}
                    >
                        Refresh
                    </Button>
                </Space>
            </div>

            {/* History Table */}
            <Spin spinning={historyLoading}>
                {historyShifts.length > 0 ? (
                    <Table
                        columns={historyColumns}
                        dataSource={historyShifts}
                        rowKey="id"
                        pagination={{
                            current: historyPagination.page,
                            pageSize: historyPagination.pageSize,
                            total: historyPagination.total,
                            showSizeChanger: true,
                            showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} shifts`,
                            onChange: (page, pageSize) => {
                                setHistoryPagination(prev => ({ ...prev, page, pageSize }));
                                fetchShiftHistory(statusFilter, page, pageSize);
                            }
                        }}
                        scroll={{ x: 'max-content' }}
                        bordered
                        size="middle"
                        style={{ borderRadius: 8, overflow: 'hidden' }}
                    />
                ) : (
                    <Empty
                        description={`No ${statusFilter?.toLowerCase() || ''} shifts found`}
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        style={{ padding: 60 }}
                    />
                )}
            </Spin>
        </>
    );

    return (
        <div style={{ padding: 24, background: '#f0f2f5', minHeight: '100vh' }}>
            <Card
                bordered={false}
                style={{ borderRadius: 12, boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}
            >
                {/* Header */}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 24,
                    flexWrap: 'wrap',
                    gap: 16
                }}>
                    <div>
                        <Title level={3} style={{ margin: 0, color: '#1a1a2e' }}>
                            <SafetyCertificateOutlined style={{ marginRight: 12, color: '#1890ff' }} />
                            Shift Management
                        </Title>
                        <Text type="secondary">
                            Review, approve, and track all driver shift requests
                        </Text>
                    </div>

                    <Space size="middle">
                        <Tooltip title="Click to view all pending shifts">
                            <div 
                                style={{ cursor: 'pointer' }} 
                                onClick={() => setIsPendingListModalVisible(true)}
                            >
                                <Badge count={pendingApprovals.length} overflowCount={99}>
                                    <Tag color="orange" style={{ fontSize: 14, padding: '4px 12px' }}>
                                        Pending: {pendingApprovals.length}
                                    </Tag>
                                </Badge>
                            </div>
                        </Tooltip>
                    </Space>
                </div>

                {/* Summary Stats */}
                <Row gutter={16} style={{ marginBottom: 24 }}>
                    <Col xs={12} sm={6}>
                        <Card size="small" style={{ borderLeft: '4px solid #faad14' }}>
                            <Statistic 
                                title="Pending" 
                                value={pendingApprovals.length} 
                                prefix={<ClockCircleOutlined style={{ color: '#faad14' }} />}
                                valueStyle={{ color: '#faad14' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                        <Card size="small" style={{ borderLeft: '4px solid #52c41a' }}>
                            <Statistic 
                                title="Approved" 
                                value={historyCounts.approved} 
                                prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                                valueStyle={{ color: '#52c41a' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                        <Card size="small" style={{ borderLeft: '4px solid #ff4d4f' }}>
                            <Statistic 
                                title="Rejected" 
                                value={historyCounts.rejected} 
                                prefix={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
                                valueStyle={{ color: '#ff4d4f' }}
                            />
                        </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                        <Card size="small" style={{ borderLeft: '4px solid #d9d9d9' }}>
                            <Statistic 
                                title="Expired" 
                                value={historyCounts.expired} 
                                prefix={<ExclamationCircleOutlined style={{ color: '#d9d9d9' }} />}
                                valueStyle={{ color: '#8c8c8c' }}
                            />
                        </Card>
                    </Col>
                </Row>

                {/* Tabs */}
                <Tabs
                    activeKey={activeTab}
                    onChange={setActiveTab}
                    type="card"
                    items={[
                        {
                            key: 'pending',
                            label: (
                                <span>
                                    <ClockCircleOutlined />
                                    Pending
                                    <Badge count={pendingApprovals.length} size="small" style={{ marginLeft: 8 }} />
                                </span>
                            ),
                            children: renderPendingContent()
                        },
                        {
                            key: 'approved',
                            label: (
                                <span>
                                    <CheckCircleOutlined style={{ color: '#52c41a' }} />
                                    Approved
                                    <Badge count={historyCounts.approved} size="small" style={{ marginLeft: 8, backgroundColor: '#52c41a' }} />
                                </span>
                            ),
                            children: renderHistoryContent('APPROVED')
                        },
                        {
                            key: 'rejected',
                            label: (
                                <span>
                                    <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
                                    Rejected
                                    <Badge count={historyCounts.rejected} size="small" style={{ marginLeft: 8, backgroundColor: '#ff4d4f' }} />
                                </span>
                            ),
                            children: renderHistoryContent('REJECTED')
                        },
                        {
                            key: 'expired',
                            label: (
                                <span>
                                    <ExclamationCircleOutlined style={{ color: '#8c8c8c' }} />
                                    Expired
                                    <Badge count={historyCounts.expired} size="small" style={{ marginLeft: 8, backgroundColor: '#8c8c8c' }} />
                                </span>
                            ),
                            children: renderHistoryContent('EXPIRED')
                        }
                    ]}
                />
            </Card>

            {/* Detail Modal */}
            <Modal
                title={
                    <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 12 }}>
                        <Title level={4} style={{ margin: 0 }}>
                            <UserOutlined style={{ marginRight: 8 }} />
                            Shift Approval Details
                        </Title>
                    </div>
                }
                open={isDetailModalVisible}
                onCancel={() => setIsDetailModalVisible(false)}
                width={700}
                footer={[
                    <Button key="cancel" onClick={() => setIsDetailModalVisible(false)}>
                        Close
                    </Button>,
                    <Button
                        key="reject"
                        danger
                        icon={<CloseCircleOutlined />}
                        onClick={handleOpenReject}
                        loading={actionLoading}
                    >
                        Reject
                    </Button>,
                    <Button
                        key="approve"
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={() => handleApprove(selectedApproval?.shiftId)}
                        loading={actionLoading}
                        style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    >
                        Approve Shift
                    </Button>
                ]}
            >
                {selectedApproval && (
                    <Tabs
                        items={[
                            {
                                key: 'driver',
                                label: <span><UserOutlined /> Driver Info</span>,
                                children: (
                                    <Descriptions column={2} bordered size="small">
                                        <Descriptions.Item label="Name" span={2}>
                                            <Text strong>{selectedApproval.name}</Text>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Phone">
                                            {selectedApproval.phone}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="License No">
                                            {selectedApproval.licenseNumber}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="License Expiry">
                                            {selectedApproval.licenseExpiry ? moment(selectedApproval.licenseExpiry).format('DD MMM YYYY') : 'N/A'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Training">
                                            <Badge
                                                status={selectedApproval.trainingCompleted ? 'success' : 'warning'}
                                                text={selectedApproval.trainingCompleted ? 'Completed' : 'Pending'}
                                            />
                                        </Descriptions.Item>
                                        <Descriptions.Item label="License Verified">
                                            <Badge
                                                status={selectedApproval.licenseVerified ? 'success' : 'warning'}
                                                text={selectedApproval.licenseVerified ? 'Verified' : 'Pending'}
                                            />
                                        </Descriptions.Item>
                                        <Descriptions.Item label="License Document">
                                            {selectedApproval.licenseDocument ? (
                                                <Button
                                                    type="link"
                                                    icon={<FileOutlined />}
                                                    onClick={() => window.open(selectedApproval.licenseDocument, '_blank')}
                                                >
                                                    View Document
                                                </Button>
                                            ) : (
                                                <Text type="secondary">Not uploaded</Text>
                                            )}
                                        </Descriptions.Item>
                                    </Descriptions>
                                )
                            },
                            {
                                key: 'vehicle',
                                label: <span><CarOutlined /> Vehicle Info</span>,
                                children: (
                                    <Descriptions column={2} bordered size="small">
                                        <Descriptions.Item label="Registration No" span={2}>
                                            <Text strong>{selectedApproval.vehicleNumber || 'Not Assigned'}</Text>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Registration Document" span={2}>
                                            {selectedApproval.vehicleDocument ? (
                                                <Button
                                                    type="link"
                                                    icon={<FileOutlined />}
                                                    onClick={() => window.open(selectedApproval.vehicleDocument, '_blank')}
                                                >
                                                    View Document
                                                </Button>
                                            ) : (
                                                <Text type="secondary">Not uploaded</Text>
                                            )}
                                        </Descriptions.Item>
                                    </Descriptions>
                                )
                            },
                            {
                                key: 'shift',
                                label: <span><ClockCircleOutlined /> Shift Details</span>,
                                children: (
                                    <Descriptions column={2} bordered size="small">
                                        <Descriptions.Item label="Shift Date">
                                            {selectedApproval.shiftDate ? moment(selectedApproval.shiftDate).format('DD MMM YYYY') : 'N/A'}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Shift Type">
                                            <Tag color="blue">{selectedApproval.preferredShift}</Tag>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Start Time">
                                            {selectedApproval.requestedShiftStart}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="End Time">
                                            {selectedApproval.requestedShiftEnd}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Created By">
                                            {selectedApproval.createdBy}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Created At">
                                            {selectedApproval.createdAt ? moment(selectedApproval.createdAt).format('DD MMM YYYY HH:mm') : 'N/A'}
                                        </Descriptions.Item>
                                    </Descriptions>
                                )
                            }
                        ]}
                    />
                )}
            </Modal>

            {/* Reject Modal */}
            <Modal
                title="Reject Shift"
                open={isRejectModalVisible}
                onCancel={() => setIsRejectModalVisible(false)}
                onOk={handleReject}
                okText="Reject Shift"
                okButtonProps={{ danger: true, loading: actionLoading }}
            >
                <Text style={{ display: 'block', marginBottom: 12 }}>
                    Please provide a reason for rejecting this shift request:
                </Text>
                <TextArea
                    rows={4}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Enter rejection reason..."
                />
            </Modal>

            {/* All Pending Shifts Modal */}
            <Modal
                title={
                    <Space>
                        <ClockCircleOutlined style={{ color: '#faad14' }} />
                        <span>All Pending Shift Requests</span>
                        <Badge count={pendingApprovals.length} style={{ backgroundColor: '#faad14' }} />
                    </Space>
                }
                open={isPendingListModalVisible}
                onCancel={() => setIsPendingListModalVisible(false)}
                width={1100}
                footer={[
                    <Button key="close" onClick={() => setIsPendingListModalVisible(false)}>
                        Close
                    </Button>
                ]}
            >
                {pendingApprovals.length === 0 ? (
                    <Empty description="No pending shift requests" />
                ) : (
                    <Table
                        dataSource={pendingApprovals}
                        rowKey="shiftId"
                        size="small"
                        pagination={{ pageSize: 10, showSizeChanger: true, showTotal: (total) => `Total ${total} pending shifts` }}
                        columns={[
                            {
                                title: 'Driver',
                                key: 'driver',
                                width: 180,
                                render: (_, record) => (
                                    <Space direction="vertical" size={0}>
                                        <Text strong><UserOutlined /> {record.driverName}</Text>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            <PhoneOutlined /> {record.driverPhone}
                                        </Text>
                                    </Space>
                                )
                            },
                            {
                                title: 'License',
                                key: 'license',
                                width: 140,
                                render: (_, record) => (
                                    <Space direction="vertical" size={0}>
                                        <Text><IdcardOutlined /> {record.licenseNo}</Text>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            Exp: {moment(record.licenseExpiry).format('DD MMM YYYY')}
                                        </Text>
                                    </Space>
                                )
                            },
                            {
                                title: 'Vehicle',
                                key: 'vehicle',
                                width: 120,
                                render: (_, record) => (
                                    <Tag icon={<CarOutlined />} color="blue">{record.vehicleNo}</Tag>
                                )
                            },
                            {
                                title: 'Shift Date',
                                dataIndex: 'shiftDate',
                                key: 'shiftDate',
                                width: 110,
                                render: (date) => (
                                    <Tag color="cyan">
                                        <CalendarOutlined /> {moment(date).format('DD MMM YYYY')}
                                    </Tag>
                                ),
                                sorter: (a, b) => moment(a.shiftDate).unix() - moment(b.shiftDate).unix()
                            },
                            {
                                title: 'Shift Time',
                                key: 'shiftTime',
                                width: 130,
                                render: (_, record) => (
                                    <Space direction="vertical" size={0}>
                                        <Tag color="green">{record.shiftType || 'Custom'}</Tag>
                                        <Text style={{ fontSize: 12 }}>
                                            <ClockCircleOutlined /> {record.startTime} - {record.endTime}
                                        </Text>
                                    </Space>
                                )
                            },
                            {
                                title: 'Created By',
                                key: 'createdBy',
                                width: 150,
                                render: (_, record) => (
                                    <Space direction="vertical" size={0}>
                                        <Text>{record.createdBy || 'System'}</Text>
                                        <Text type="secondary" style={{ fontSize: 12 }}>
                                            {moment(record.createdAt).format('DD MMM, HH:mm')}
                                        </Text>
                                    </Space>
                                )
                            },
                            {
                                title: 'Actions',
                                key: 'actions',
                                width: 150,
                                fixed: 'right',
                                render: (_, record) => (
                                    <Space>
                                        <Tooltip title="View Details">
                                            <Button
                                                icon={<EyeOutlined />}
                                                size="small"
                                                onClick={() => {
                                                    setIsPendingListModalVisible(false);
                                                    handleViewDetails(record);
                                                }}
                                            />
                                        </Tooltip>
                                        <Tooltip title="Approve">
                                            <Button
                                                type="primary"
                                                icon={<CheckCircleOutlined />}
                                                size="small"
                                                onClick={() => {
                                                    setIsPendingListModalVisible(false);
                                                    handleApprove(record.shiftId);
                                                }}
                                            />
                                        </Tooltip>
                                        <Tooltip title="Reject">
                                            <Button
                                                danger
                                                icon={<CloseCircleOutlined />}
                                                size="small"
                                                onClick={() => {
                                                    setSelectedApproval(record);
                                                    setIsPendingListModalVisible(false);
                                                    setIsRejectModalVisible(true);
                                                }}
                                            />
                                        </Tooltip>
                                    </Space>
                                )
                            }
                        ]}
                        scroll={{ x: 1000 }}
                    />
                )}
            </Modal>
        </div>
    );
};

export default EICShiftApprovals;
