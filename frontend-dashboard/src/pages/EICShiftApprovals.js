import React, { useState, useEffect, useCallback } from 'react';
import {
    Card, Table, Button, Modal, message, DatePicker, Tag, Space, Typography,
    Tooltip, Row, Col, Spin, Badge, Input, Empty, Descriptions, Image, Tabs, Statistic, Select, Divider
} from 'antd';
import {
    CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
    CalendarOutlined, UserOutlined, CarOutlined, FileOutlined,
    ReloadOutlined, EyeOutlined, LeftOutlined, RightOutlined,
    IdcardOutlined, PhoneOutlined, SafetyCertificateOutlined,
    HistoryOutlined, ExclamationCircleOutlined, ScheduleOutlined, ClearOutlined
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
    const [pendingSearchText, setPendingSearchText] = useState('');
    const [pendingViewMode, setPendingViewMode] = useState('week'); // 'week' | 'today' | 'timeline'
    const [timelineData, setTimelineData] = useState({ dates: [], drivers: [] }); // For Grid View
    const [timelineLoading, setTimelineLoading] = useState(false);
    const [isBulkApproveLoading, setIsBulkApproveLoading] = useState(false);
    const [isBulkApproveModalVisible, setIsBulkApproveModalVisible] = useState(false);
    const [bulkApprovalPeriod, setBulkApprovalPeriod] = useState(null); // 'week' or 'month'
    const [selectedDriverForBulk, setSelectedDriverForBulk] = useState(null); // null means all drivers

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
        }
        // else if (activeTab === 'expired') {
        //     fetchShiftHistory('EXPIRED');
        // }
    }, [activeTab, fetchPendingApprovals, fetchShiftHistory]);

    // Navigation
    const goToPreviousWeek = () => setWeekStart(prev => prev.clone().subtract(1, 'week'));
    const goToNextWeek = () => setWeekStart(prev => prev.clone().add(1, 'week'));
    const goToCurrentWeek = () => setWeekStart(moment().startOf('week'));

    // Filter approvals by current week
    // Filter approvals by current week AND Search
    const filteredApprovals = pendingApprovals.filter(approval => {
        const matchesSearch = !pendingSearchText ||
            (approval.name || approval.driverName || '').toLowerCase().includes(pendingSearchText.toLowerCase()) ||
            (approval.vehicleNumber || approval.vehicleNo || '').toLowerCase().includes(pendingSearchText.toLowerCase());

        if (!approval.shiftDate) return matchesSearch;
        const shiftDate = moment(approval.shiftDate);

        if (pendingViewMode === 'today') {
            return matchesSearch && shiftDate.isSame(moment(), 'day');
        }

        const weekEnd = weekStart.clone().add(6, 'days');
        return matchesSearch && shiftDate.isBetween(weekStart, weekEnd, 'day', '[]');
    });

    // Group by date for timesheet view
    const groupedByDate = {};
    const dates = [];
    for (let i = 0; i < 7; i++) {
        const date = weekStart.clone().add(i, 'days').format('YYYY-MM-DD');
        dates.push(date);
        groupedByDate[date] = filteredApprovals.filter(a => a.shiftDate === date);
    }

    // Timeline Data Fetch
    const fetchTimelineData = async () => {
        if (pendingViewMode !== 'timeline') return;

        setTimelineLoading(true);
        try {
            const startStr = weekStart.format('YYYY-MM-DD');
            const response = await apiClient.get('/timesheet/', {
                params: {
                    start_date: startStr,
                    search: pendingSearchText
                }
            });
            setTimelineData(response.data);
        } catch (error) {
            console.error('Error fetching timeline:', error);
            message.error('Failed to load timeline data');
        } finally {
            setTimelineLoading(false);
        }
    };

    useEffect(() => {
        if (pendingViewMode === 'timeline') {
            fetchTimelineData();
        }
    }, [pendingViewMode, weekStart, pendingSearchText]);

    // Open Bulk Approve Modal
    const handleOpenBulkApprove = (period) => {
        setBulkApprovalPeriod(period);
        setSelectedDriverForBulk(null); // Reset to "All Drivers"
        setIsBulkApproveModalVisible(true);
    };

    // Bulk Approve Logic
    const handleBulkApprove = async () => {
        setIsBulkApproveLoading(true);
        try {
            let start_date, end_date;

            if (bulkApprovalPeriod === 'week') {
                start_date = weekStart.format('YYYY-MM-DD');
                end_date = weekStart.clone().add(6, 'days').format('YYYY-MM-DD');
            } else if (bulkApprovalPeriod === 'month') {
                start_date = moment().startOf('month').format('YYYY-MM-DD');
                end_date = moment().endOf('month').format('YYYY-MM-DD');
            }

            const payload = {
                start_date,
                end_date
            };

            // Add driver_id if a specific driver is selected
            if (selectedDriverForBulk) {
                payload.driver_id = selectedDriverForBulk;
            }

            const response = await apiClient.post('/eic/driver-approvals/bulk-approve', payload);

            if (response.data.success) {
                message.success(response.data.message);
                setIsBulkApproveModalVisible(false);
                // Refresh data
                if (pendingViewMode === 'timeline') {
                    fetchTimelineData();
                } else {
                    fetchPendingApprovals();
                }
                fetchShiftHistory(); // Refresh counts
            }
        } catch (error) {
            console.error('Bulk approve error:', error);
            message.error('Failed to process bulk approval');
        } finally {
            setIsBulkApproveLoading(false);
        }
    };

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

    // Filter Logic
    const [searchText, setSearchText] = useState('');

    const getFilteredHistory = () => {
        if (!searchText) return historyShifts;
        return historyShifts.filter(item =>
            item.driverName?.toLowerCase().includes(searchText.toLowerCase()) ||
            item.vehicleNumber?.toLowerCase().includes(searchText.toLowerCase())
        );
    };

    // Render Status Badge
    const renderStatusBadge = (status) => {
        const styles = {
            APPROVED: { bg: '#ECFDF5', text: '#059669', border: '#D1FAE5' },
            REJECTED: { bg: '#FEF2F2', text: '#DC2626', border: '#FEE2E2' },
            PENDING: { bg: '#FFFBEB', text: '#D97706', border: '#FEF3C7' },
        };
        const style = styles[status] || styles.PENDING;

        return (
            <span style={{
                background: style.bg,
                color: style.text,
                border: `1px solid ${style.border}`,
                padding: '2px 8px',
                borderRadius: '9999px',
                fontSize: '12px',
                fontWeight: 500,
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px'
            }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: style.text }}></span>
                {status}
            </span>
        );
    };

    return (
        <div style={{ padding: '24px 32px', background: '#F9FAFB', minHeight: '100vh' }}>
            <div style={{ maxWidth: 1400, margin: '0 auto' }}>

                {/* Header */}
                <div style={{ marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <Title level={2} style={{ margin: 0, fontWeight: 700, color: '#111827', letterSpacing: '-0.5px' }}>
                            Shift Approvals
                        </Title>
                        <Text style={{ color: '#6B7280', fontSize: 16 }}>
                            Manage driver shift requests and review history
                        </Text>
                    </div>
                    <Space>
                        <Button
                            onClick={() => setIsPendingListModalVisible(true)}
                            type="primary"
                            size="large"
                            style={{
                                background: '#F59E0B',
                                borderColor: '#F59E0B',
                                boxShadow: '0 4px 6px -1px rgba(245, 158, 11, 0.1)',
                                height: 44
                            }}
                            icon={<ClockCircleOutlined />}
                        >
                            Pending Requests ({pendingApprovals.length})
                        </Button>
                    </Space>
                </div>

                {/* Stats Row */}
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(4, 1fr)',
                    gap: 24,
                    marginBottom: 32
                }}>
                    {[
                        { title: 'Pending', value: pendingApprovals.length, color: '#F59E0B', icon: <ClockCircleOutlined /> },
                        { title: 'Approved', value: historyCounts.approved, color: '#10B981', icon: <CheckCircleOutlined /> },
                        { title: 'Rejected', value: historyCounts.rejected, color: '#EF4444', icon: <CloseCircleOutlined /> },
                        { title: 'Total Processed', value: historyCounts.approved + historyCounts.rejected, color: '#6366F1', icon: <HistoryOutlined /> },
                    ].map((stat, i) => (
                        <Card
                            key={i}
                            bordered={false}
                            bodyStyle={{ padding: 24 }}
                            style={{
                                borderRadius: 12,
                                boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div>
                                    <Text style={{ color: '#6B7280', fontSize: 14, fontWeight: 500 }}>{stat.title}</Text>
                                    <div style={{ fontSize: 28, fontWeight: 700, color: '#111827', marginTop: 4 }}>
                                        {stat.value}
                                    </div>
                                </div>
                                <div style={{
                                    width: 48,
                                    height: 48,
                                    borderRadius: 12,
                                    background: `${stat.color}15`,
                                    color: stat.color,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: 24
                                }}>
                                    {stat.icon}
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>

                {/* Main Content Card */}
                <Card
                    bordered={false}
                    style={{
                        borderRadius: 16,
                        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
                        overflow: 'hidden'
                    }}
                    bodyStyle={{ padding: 0 }}
                >
                    <div style={{ borderBottom: '1px solid #E5E7EB' }}>
                        <Tabs
                            activeKey={activeTab}
                            onChange={setActiveTab}
                            size="large"
                            tabBarStyle={{ margin: 0, padding: '0 24px' }}
                            items={[
                                {
                                    key: 'pending',
                                    label: <span style={{ fontSize: 15 }}>Pending Overview</span>
                                },
                                {
                                    key: 'approved',
                                    label: <span style={{ fontSize: 15 }}>Approved History</span>
                                },
                                {
                                    key: 'rejected',
                                    label: <span style={{ fontSize: 15 }}>Rejected History</span>
                                }
                            ]}
                        />
                    </div>

                    <div style={{ padding: 24 }}>
                        {activeTab === 'pending' ? (
                            <>
                                <div style={{ marginBottom: 24, display: 'flex', gap: 16, alignItems: 'center', justifyContent: 'space-between' }}>
                                    {/* Week Navigation */}
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 16,
                                        padding: '8px 16px',
                                        background: '#F9FAFB',
                                        borderRadius: 12,
                                        border: '1px solid #F3F4F6'
                                    }}>
                                        <Button icon={<LeftOutlined />} onClick={goToPreviousWeek} />
                                        <div style={{ textAlign: 'center', minWidth: 140 }}>
                                            <div style={{ fontSize: 12, color: '#6B7280', textTransform: 'uppercase', fontWeight: 600 }}>Current Week</div>
                                            <div style={{ fontSize: 15, fontWeight: 600, color: '#111827' }}>
                                                {weekStart.format('MMM D')} - {weekStart.clone().add(6, 'days').format('MMM D')}
                                            </div>
                                        </div>
                                        <Button icon={<RightOutlined />} onClick={goToNextWeek} />
                                    </div>

                                    {/* Search & Actions */}
                                    <Space size="middle">
                                        <Input
                                            placeholder="Search Pending..."
                                            prefix={<UserOutlined style={{ color: '#9CA3AF' }} />}
                                            value={pendingSearchText}
                                            onChange={e => setPendingSearchText(e.target.value)}
                                            style={{ width: 250, borderRadius: 8 }}
                                        />
                                        <div style={{ background: '#E5E7EB', padding: 4, borderRadius: 8, display: 'flex' }}>
                                            <Button
                                                type={pendingViewMode === 'week' ? 'text' : 'text'}
                                                style={{
                                                    background: pendingViewMode === 'week' ? '#fff' : 'transparent',
                                                    boxShadow: pendingViewMode === 'week' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                                    borderRadius: 6,
                                                    fontWeight: 500
                                                }}
                                                onClick={() => {
                                                    setPendingViewMode('week');
                                                    goToCurrentWeek();
                                                }}
                                            >
                                                Week View
                                            </Button>
                                            <Button
                                                type={pendingViewMode === 'today' ? 'text' : 'text'}
                                                style={{
                                                    background: pendingViewMode === 'today' ? '#fff' : 'transparent',
                                                    boxShadow: pendingViewMode === 'today' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                                    borderRadius: 6,
                                                    fontWeight: 500,
                                                    color: pendingViewMode === 'today' ? '#059669' : undefined
                                                }}
                                                onClick={() => setPendingViewMode('today')}
                                            >
                                                Today Only
                                            </Button>
                                            <Button
                                                type={pendingViewMode === 'timeline' ? 'text' : 'text'}
                                                style={{
                                                    background: pendingViewMode === 'timeline' ? '#fff' : 'transparent',
                                                    boxShadow: pendingViewMode === 'timeline' ? '0 1px 2px rgba(0,0,0,0.1)' : 'none',
                                                    borderRadius: 6,
                                                    fontWeight: 500,
                                                    color: pendingViewMode === 'timeline' ? '#2563EB' : undefined
                                                }}
                                                onClick={() => setPendingViewMode('timeline')}
                                            >
                                                Timeline
                                            </Button>
                                        </div>

                                        {/* Bulk Actions */}
                                        <Space>
                                            <Button
                                                type="primary"
                                                icon={<CheckCircleOutlined />}
                                                onClick={() => handleOpenBulkApprove('week')}
                                                style={{
                                                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                                    borderColor: '#667eea',
                                                    fontWeight: 600,
                                                    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
                                                }}
                                            >
                                                Approve Week
                                            </Button>
                                            <Button
                                                type="primary"
                                                icon={<CalendarOutlined />}
                                                onClick={() => handleOpenBulkApprove('month')}
                                                style={{
                                                    background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                                                    borderColor: '#f093fb',
                                                    fontWeight: 600,
                                                    boxShadow: '0 4px 12px rgba(240, 147, 251, 0.3)'
                                                }}
                                            >
                                                Approve Month
                                            </Button>
                                        </Space>
                                    </Space>
                                </div>

                                {/* Conditional Render: Timeline Grid or Table */}
                                {pendingViewMode === 'timeline' ? (
                                    <div style={{ overflowX: 'auto', border: '1px solid #E5E7EB', borderRadius: 8 }}>
                                        <div style={{ minWidth: 1000 }}>
                                            {/* Header */}
                                            <div style={{ display: 'flex', borderBottom: '1px solid #E5E7EB', background: '#F9FAFB' }}>
                                                <div style={{ width: 200, padding: 12, fontWeight: 600, color: '#6B7280', borderRight: '1px solid #E5E7EB' }}>
                                                    Driver
                                                </div>
                                                {timelineData.dates.map(date => (
                                                    <div key={date} style={{ flex: 1, padding: 12, textAlign: 'center', borderRight: '1px solid #E5E7EB', minWidth: 120 }}>
                                                        <div style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{moment(date).format('ddd')}</div>
                                                        <div style={{ fontSize: 12, color: '#6B7280' }}>{moment(date).format('MMM D')}</div>
                                                    </div>
                                                ))}
                                            </div>

                                            {/* Rows */}
                                            {timelineLoading ? (
                                                <div style={{ padding: 40, textAlign: 'center' }}><Spin /></div>
                                            ) : timelineData.drivers.map(driver => (
                                                <div key={driver.id} style={{ display: 'flex', borderBottom: '1px solid #E5E7EB' }}>
                                                    {/* Driver Info */}
                                                    <div style={{ width: 200, padding: 12, borderRight: '1px solid #E5E7EB', background: '#fff' }}>
                                                        <div style={{ fontWeight: 500, color: '#111827' }}>{driver.name}</div>
                                                        <div style={{ fontSize: 12, color: '#6B7280' }}>
                                                            {driver.vehicle ? <><CarOutlined /> {driver.vehicle}</> : 'No Vehicle'}
                                                        </div>
                                                    </div>

                                                    {/* Days */}
                                                    {timelineData.dates.map(date => {
                                                        const shift = driver.shifts[date];
                                                        return (
                                                            <div key={date} style={{ flex: 1, padding: 8, borderRight: '1px solid #E5E7EB', minWidth: 120, background: '#fff' }}>
                                                                {shift ? (
                                                                    <div
                                                                        onClick={() => {
                                                                            if (shift.status === 'PENDING') {
                                                                                handleViewDetails({
                                                                                    shiftId: shift.id,
                                                                                    driverName: driver.name,
                                                                                    driverId: driver.id,
                                                                                    // Ensure all required fields for modal are present
                                                                                    name: driver.name,
                                                                                    vehicleNumber: driver.vehicle,
                                                                                    shiftDate: date,
                                                                                    requestedShiftStart: moment(shift.start_time).format('HH:mm'),
                                                                                    requestedShiftEnd: moment(shift.end_time).format('HH:mm'),
                                                                                    status: shift.status
                                                                                });
                                                                            }
                                                                        }}
                                                                        style={{
                                                                            padding: 8,
                                                                            borderRadius: 6,
                                                                            cursor: shift.status === 'PENDING' ? 'pointer' : 'default',
                                                                            border: '1px solid',
                                                                            fontSize: 12,
                                                                            background: shift.status === 'APPROVED' ? '#f6ffed' : shift.status === 'PENDING' ? '#fffbe6' : shift.status === 'EXPIRED' ? '#fff1f0' : '#fff',
                                                                            borderColor: shift.status === 'APPROVED' ? '#b7eb8f' : shift.status === 'PENDING' ? '#ffe58f' : shift.status === 'EXPIRED' ? '#ffa39e' : '#d9d9d9',
                                                                            color: shift.status === 'APPROVED' ? '#135200' : shift.status === 'PENDING' ? '#d46b08' : shift.status === 'EXPIRED' ? '#cf1322' : '#000000D9'
                                                                        }}
                                                                    >
                                                                        <div style={{ fontWeight: 600, marginBottom: 4 }}>
                                                                            {shift.status === 'EXPIRED' ? 'EXPIRED' : shift.status}
                                                                        </div>
                                                                        <div>{moment(shift.start_time).format('HH:mm')} - {moment(shift.end_time).format('HH:mm')}</div>
                                                                    </div>
                                                                ) : (
                                                                    <div style={{ height: '100%', minHeight: 40 }}></div>
                                                                )}
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            ))}
                                            {!timelineLoading && timelineData.drivers.length === 0 && (
                                                <Empty description="No drivers found" style={{ padding: 40 }} />
                                            )}
                                        </div>
                                    </div>
                                ) : (
                                    <Table
                                        columns={columns} // Using original columns which define handleViewDetails correctly
                                        dataSource={filteredApprovals}
                                        rowKey="shiftId"
                                        pagination={{ pageSize: 10 }}
                                        loading={loading}
                                        rowClassName="hover-row"
                                        onRow={(record) => ({
                                            onClick: () => handleViewDetails(record),
                                            style: { cursor: 'pointer' }
                                        })}
                                    />
                                )}
                            </>
                        ) : (
                            <>
                                {/* Filter Bar for History */}
                                <Row gutter={16} style={{ marginBottom: 24 }} align="middle">
                                    <Col span={8}>
                                        <Input
                                            placeholder="Search by driver or vehicle..."
                                            prefix={<UserOutlined style={{ color: '#9CA3AF' }} />}
                                            size="large"
                                            value={searchText}
                                            onChange={e => setSearchText(e.target.value)}
                                            style={{ borderRadius: 8 }}
                                        />
                                    </Col>
                                    <Col flex="auto">
                                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
                                            <Button
                                                onClick={() => {
                                                    const today = [moment(), moment()];
                                                    setDateRange(today);
                                                    fetchShiftHistory(activeTab === 'approved' ? 'APPROVED' : 'REJECTED');
                                                }}
                                            >
                                                Today
                                            </Button>
                                            <RangePicker
                                                size="large"
                                                style={{ borderRadius: 8 }}
                                                value={dateRange}
                                                onChange={dates => {
                                                    setDateRange(dates);
                                                    if (dates) fetchShiftHistory(activeTab === 'approved' ? 'APPROVED' : 'REJECTED');
                                                }}
                                            />
                                            <Button
                                                icon={<ReloadOutlined />}
                                                size="large"
                                                onClick={() => fetchShiftHistory(activeTab === 'approved' ? 'APPROVED' : 'REJECTED')}
                                            >
                                                Refresh
                                            </Button>
                                        </div>
                                    </Col>
                                </Row>

                                {/* History Table */}
                                <Table
                                    columns={[
                                        ...historyColumns.filter(c => c.key !== 'status'),
                                        {
                                            title: 'Status',
                                            key: 'status',
                                            width: 120,
                                            render: (_, r) => renderStatusBadge(r.status)
                                        }
                                    ]}
                                    dataSource={getFilteredHistory()}
                                    rowKey="id"
                                    pagination={{
                                        ...historyPagination,
                                        onChange: (page, pageSize) => {
                                            setHistoryPagination(prev => ({ ...prev, page, pageSize }));
                                            fetchShiftHistory(activeTab === 'approved' ? 'APPROVED' : 'REJECTED', page, pageSize);
                                        }
                                    }}
                                    loading={historyLoading}
                                    rowClassName="hover-row"
                                />
                            </>
                        )}
                    </div>
                </Card>
            </div>

            {/* RESTORED: Detail Modal */}
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
                                            <Text strong>{selectedApproval.name || selectedApproval.driverName}</Text>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Phone">
                                            {selectedApproval.phone || selectedApproval.driverPhone}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="License No">
                                            {selectedApproval.licenseNumber || selectedApproval.licenseNo}
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
                                            <Text strong>{selectedApproval.vehicleNumber || selectedApproval.vehicleNo || 'Not Assigned'}</Text>
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
                                            {selectedApproval.requestedShiftStart || selectedApproval.startTime}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="End Time">
                                            {selectedApproval.requestedShiftEnd || selectedApproval.endTime}
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

            {/* Modal for Pending List */}
            <Modal
                title={<Title level={4} style={{ margin: 0 }}>All Pending Requests</Title>}
                open={isPendingListModalVisible}
                onCancel={() => setIsPendingListModalVisible(false)}
                width={1000}
                footer={null}
                bodyStyle={{ padding: 0 }}
            >
                <Table
                    dataSource={pendingApprovals}
                    rowKey="shiftId"
                    pagination={{ pageSize: 8 }}
                    columns={[
                        {
                            title: 'Driver Details',
                            key: 'driver',
                            render: (_, r) => (
                                <div>
                                    <Text strong style={{ color: '#111827' }}>{r.name || r.driverName}</Text>
                                    <div style={{ color: '#6B7280', fontSize: 12 }}>{r.licenseNumber || r.licenseNo}</div>
                                </div>
                            )
                        },
                        {
                            title: 'Vehicle',
                            key: 'vehicle',
                            render: (_, r) => (
                                <Tag bordered={false} style={{ background: '#F3F4F6', color: '#374151' }}>
                                    {r.vehicleNumber || r.vehicleNo}
                                </Tag>
                            )
                        },
                        {
                            title: 'Shift',
                            key: 'shift',
                            render: (_, r) => (
                                <div>
                                    <div style={{ fontWeight: 500 }}>{moment(r.shiftDate).format('MMM D, YYYY')}</div>
                                    <div style={{ color: '#6B7280', fontSize: 12 }}>
                                        {r.requestedShiftStart} - {r.requestedShiftEnd} ({r.preferredShift})
                                    </div>
                                </div>
                            )
                        },
                        {
                            title: 'Actions',
                            key: 'actions',
                            render: (_, r) => (
                                <Space>
                                    <Tooltip title="View Details">
                                        <Button
                                            icon={<EyeOutlined />}
                                            size="small"
                                            onClick={() => {
                                                setIsPendingListModalVisible(false); // Close list modal
                                                handleViewDetails(r); // Open details modal
                                            }}
                                        />
                                    </Tooltip>
                                    <Tooltip title="Approve">
                                        <Button
                                            type="text"
                                            icon={<CheckCircleOutlined style={{ color: '#10B981', fontSize: 18 }} />}
                                            onClick={() => {
                                                setIsPendingListModalVisible(false);
                                                handleApprove(r.shiftId);
                                            }}
                                        />
                                    </Tooltip>
                                    <Tooltip title="Reject">
                                        <Button
                                            type="text"
                                            icon={<CloseCircleOutlined style={{ color: '#EF4444', fontSize: 18 }} />}
                                            onClick={() => {
                                                setSelectedApproval(r);
                                                setIsPendingListModalVisible(false);
                                                setIsRejectModalVisible(true);
                                            }}
                                        />
                                    </Tooltip>
                                </Space>
                            )
                        }
                    ]}
                />
            </Modal>

            {/* Reject Modal */}
            <Modal
                title="Reject Shift Request"
                open={isRejectModalVisible}
                onCancel={() => setIsRejectModalVisible(false)}
                onOk={handleReject}
                okText="Confirm Reject"
                okButtonProps={{ danger: true, loading: actionLoading }}
            >
                <p>Please provide a reason for rejecting this request:</p>
                <TextArea
                    rows={4}
                    value={rejectReason}
                    onChange={e => setRejectReason(e.target.value)}
                    placeholder="e.g. Invalid license, Training incomplete..."
                />
            </Modal>

            {/* Bulk Approve Modal */}
            <Modal
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                        <div style={{
                            width: 48,
                            height: 48,
                            borderRadius: 12,
                            background: bulkApprovalPeriod === 'week'
                                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                : 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#fff',
                            fontSize: 24
                        }}>
                            {bulkApprovalPeriod === 'week' ? <CheckCircleOutlined /> : <CalendarOutlined />}
                        </div>
                        <div>
                            <Title level={4} style={{ margin: 0, color: '#111827' }}>
                                Bulk Approve {bulkApprovalPeriod === 'week' ? 'Week' : 'Month'} Shifts
                            </Title>
                            <Text style={{ color: '#6B7280', fontSize: 14 }}>
                                {bulkApprovalPeriod === 'week'
                                    ? `${weekStart.format('MMM D')} - ${weekStart.clone().add(6, 'days').format('MMM D, YYYY')}`
                                    : `${moment().startOf('month').format('MMM D')} - ${moment().endOf('month').format('MMM D, YYYY')}`
                                }
                            </Text>
                        </div>
                    </div>
                }
                open={isBulkApproveModalVisible}
                onCancel={() => setIsBulkApproveModalVisible(false)}
                width={600}
                footer={[
                    <Button
                        key="cancel"
                        onClick={() => setIsBulkApproveModalVisible(false)}
                        size="large"
                    >
                        Cancel
                    </Button>,
                    <Button
                        key="approve"
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={handleBulkApprove}
                        loading={isBulkApproveLoading}
                        size="large"
                        style={{
                            background: bulkApprovalPeriod === 'week'
                                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                                : 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                            borderColor: 'transparent',
                            fontWeight: 600,
                            minWidth: 140,
                            boxShadow: bulkApprovalPeriod === 'week'
                                ? '0 4px 12px rgba(102, 126, 234, 0.4)'
                                : '0 4px 12px rgba(240, 147, 251, 0.4)'
                        }}
                    >
                        Confirm Approval
                    </Button>
                ]}
            >
                <div style={{ padding: '24px 0' }}>
                    {/* Info Card */}
                    <Card
                        style={{
                            background: 'linear-gradient(135deg, #667eea15 0%, #764ba215 100%)',
                            border: '1px solid #E0E7FF',
                            borderRadius: 12,
                            marginBottom: 24
                        }}
                        bodyStyle={{ padding: 16 }}
                    >
                        <Space direction="vertical" size={8} style={{ width: '100%' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <ExclamationCircleOutlined style={{ color: '#667eea', fontSize: 18 }} />
                                <Text strong style={{ color: '#4C51BF', fontSize: 15 }}>
                                    Bulk Approval Information
                                </Text>
                            </div>
                            <Text style={{ color: '#6B7280', fontSize: 14, display: 'block', marginLeft: 26 }}>
                                This action will approve all pending shifts for the selected period and driver(s).
                                You can choose to approve shifts for all drivers or a specific driver.
                            </Text>
                        </Space>
                    </Card>

                    {/* Driver Selection */}
                    <div style={{ marginBottom: 24 }}>
                        <Text strong style={{ display: 'block', marginBottom: 12, color: '#111827', fontSize: 15 }}>
                            <UserOutlined style={{ marginRight: 8, color: '#667eea' }} />
                            Select Driver
                        </Text>
                        <Select
                            size="large"
                            style={{ width: '100%' }}
                            placeholder="Choose a driver or approve all"
                            value={selectedDriverForBulk}
                            onChange={setSelectedDriverForBulk}
                            allowClear
                            showSearch
                            filterOption={(input, option) =>
                                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                            }
                        >
                            <Select.Option value={null}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <CheckCircleOutlined style={{ color: '#10B981', fontSize: 16 }} />
                                    <span style={{ fontWeight: 600, color: '#10B981' }}>All Drivers</span>
                                    <Tag color="success" style={{ marginLeft: 'auto' }}>Recommended</Tag>
                                </div>
                            </Select.Option>
                            <Select.OptGroup label="Individual Drivers">
                                {[...new Map(pendingApprovals.map(item => [
                                    item.driverId || item.driver_id,
                                    { id: item.driverId || item.driver_id, name: item.name || item.driverName, vehicle: item.vehicleNumber || item.vehicleNo }
                                ])).values()].map(driver => (
                                    <Select.Option key={driver.id} value={driver.id} label={driver.name}>
                                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                                            <Text strong style={{ color: '#111827' }}>{driver.name}</Text>
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                <CarOutlined /> {driver.vehicle || 'No vehicle'}
                                            </Text>
                                        </div>
                                    </Select.Option>
                                ))}
                            </Select.OptGroup>
                        </Select>
                    </div>

                    <Divider style={{ margin: '16px 0' }} />

                    {/* Summary */}
                    <div style={{
                        background: '#F9FAFB',
                        padding: 16,
                        borderRadius: 8,
                        border: '1px solid #E5E7EB'
                    }}>
                        <Row gutter={16}>
                            <Col span={12}>
                                <div style={{ textAlign: 'center' }}>
                                    <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                                        Period
                                    </Text>
                                    <Text strong style={{ fontSize: 16, color: '#111827' }}>
                                        {bulkApprovalPeriod === 'week' ? 'This Week' : 'This Month'}
                                    </Text>
                                </div>
                            </Col>
                            <Col span={12}>
                                <div style={{ textAlign: 'center' }}>
                                    <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>
                                        Target
                                    </Text>
                                    <Text strong style={{ fontSize: 16, color: '#111827' }}>
                                        {selectedDriverForBulk
                                            ? pendingApprovals.find(a => (a.driverId || a.driver_id) === selectedDriverForBulk)?.name || 'Selected Driver'
                                            : 'All Drivers'
                                        }
                                    </Text>
                                </div>
                            </Col>
                        </Row>
                    </div>
                </div>
            </Modal>
        </div>
    );
};

export default EICShiftApprovals;
