import React, { useState, useEffect, useCallback } from 'react';
import {
    Card, Table, Button, Modal, Form, Select, message, DatePicker, TimePicker,
    Tag, Space, Typography, Tooltip, Row, Col, Spin, Badge, Popconfirm, Input, Empty,
    Checkbox, Dropdown
} from 'antd';
import {
    PlusOutlined, LeftOutlined, RightOutlined, CopyOutlined,
    CheckCircleOutlined, CloseCircleOutlined, ClockCircleOutlined,
    CalendarOutlined, UserOutlined, CarOutlined, EditOutlined, DeleteOutlined,
    ReloadOutlined, ScheduleOutlined, ClearOutlined, DownOutlined, SettingOutlined,
    BgColorsOutlined, SaveOutlined
} from '@ant-design/icons';
import apiClient from '../services/api';
import moment from 'moment';
import { useAuth } from '../context/AuthContext';

const { Title, Text } = Typography;
const { Option } = Select;

// Color palette for shift types
const SHIFT_COLORS = {
    MORNING: { bg: '#e6f7ff', border: '#1890ff', text: '#0050b3' },
    AFTERNOON: { bg: '#fff7e6', border: '#fa8c16', text: '#ad4e00' },
    NIGHT: { bg: '#f9f0ff', border: '#722ed1', text: '#391085' },
    CUSTOM: { bg: '#f6ffed', border: '#52c41a', text: '#135200' },
    PENDING: { bg: '#fffbe6', border: '#faad14', text: '#ad6800' },
    APPROVED: { bg: '#f6ffed', border: '#52c41a', text: '#135200' },
    REJECTED: { bg: '#fff1f0', border: '#ff4d4f', text: '#a8071a' },
};

const TimesheetManagement = () => {
    const { user } = useAuth();
    const roleCode = (user?.role || '').toUpperCase();
    const canApproveReject = roleCode === 'EIC' || roleCode === 'SUPER_ADMIN';

    // State
    const [loading, setLoading] = useState(false);
    const [timesheetData, setTimesheetData] = useState({ dates: [], drivers: [], templates: [] });
    const [weekStart, setWeekStart] = useState(moment().startOf('week'));
    const [isAssignModalVisible, setIsAssignModalVisible] = useState(false);
    const [isCopyWeekModalVisible, setIsCopyWeekModalVisible] = useState(false);
    const [selectedCell, setSelectedCell] = useState(null); // { driverId, date, existingShift }
    const [templates, setTemplates] = useState([]);
    const [vehicles, setVehicles] = useState([]);
    const [form] = Form.useForm();
    const [copyForm] = Form.useForm();
    const [fillWeekForm] = Form.useForm();
    const [fillMonthForm] = Form.useForm();
    const [rejectModalVisible, setRejectModalVisible] = useState(false);
    const [rejectReason, setRejectReason] = useState('');
    const [rejectTarget, setRejectTarget] = useState(null);
    const [isFillWeekModalVisible, setIsFillWeekModalVisible] = useState(false);
    const [isFillMonthModalVisible, setIsFillMonthModalVisible] = useState(false);
    const [drivers, setDrivers] = useState([]);
    // Template Management
    const [isTemplateModalVisible, setIsTemplateModalVisible] = useState(false);
    const [templateForm] = Form.useForm();
    const [editingTemplate, setEditingTemplate] = useState(null);
    const [templateLoading, setTemplateLoading] = useState(false);

    // Fetch timesheet data
    const fetchTimesheet = useCallback(async () => {
        setLoading(true);
        try {
            const startDate = weekStart.format('YYYY-MM-DD');
            const endDate = weekStart.clone().add(6, 'days').format('YYYY-MM-DD');

            const response = await apiClient.get('/timesheet/', {
                params: { start_date: startDate, end_date: endDate }
            });

            setTimesheetData(response.data);
            setTemplates(response.data.templates || []);
            setDrivers(response.data.drivers || []);
        } catch (error) {
            console.error('Failed to fetch timesheet:', error);
            message.error('Failed to load timesheet data');
        } finally {
            setLoading(false);
        }
    }, [weekStart]);

    // Fetch vehicles for assignment
    const fetchVehicles = async () => {
        try {
            const response = await apiClient.get('/vehicles/');
            setVehicles(response.data.results || response.data);
        } catch (error) {
            console.error('Failed to fetch vehicles:', error);
        }
    };

    useEffect(() => {
        fetchTimesheet();
        fetchVehicles();
    }, [fetchTimesheet]);

    // Navigation
    const goToPreviousWeek = () => {
        setWeekStart(prev => prev.clone().subtract(1, 'week'));
    };

    const goToNextWeek = () => {
        setWeekStart(prev => prev.clone().add(1, 'week'));
    };

    const goToCurrentWeek = () => {
        setWeekStart(moment().startOf('week'));
    };

    // Cell click handler
    const handleCellClick = (driver, date) => {
        const existingShift = driver.shifts[date];
        setSelectedCell({
            driverId: driver.id,
            driverName: driver.name,
            vehicleId: driver.vehicle_id,
            date,
            existingShift
        });

        if (existingShift) {
            // Edit mode
            form.setFieldsValue({
                vehicle: existingShift.vehicle,
                template: existingShift.shift_template || null,
                start_time: existingShift.start_time ? moment(existingShift.start_time) : null,
                end_time: existingShift.end_time ? moment(existingShift.end_time) : null,
                notes: existingShift.notes || ''
            });
        } else {
            // New assignment
            form.resetFields();
            if (driver.vehicle_id) {
                form.setFieldsValue({ vehicle: driver.vehicle_id });
            }
        }

        setIsAssignModalVisible(true);
    };

    // Submit assignment
    const handleAssignSubmit = async () => {
        try {
            const values = await form.validateFields();

            const payload = {
                driver_id: selectedCell.driverId,
                vehicle_id: values.vehicle,
                shift_date: selectedCell.date,
                notes: values.notes || ''
            };

            if (values.template) {
                payload.template_id = values.template;
            } else if (values.start_time && values.end_time) {
                payload.start_time = values.start_time.format('HH:mm');
                payload.end_time = values.end_time.format('HH:mm');
                payload.shift_type = 'CUSTOM';
            } else {
                message.error('Please select a template or specify start/end times');
                return;
            }

            if (selectedCell.existingShift) {
                // Update existing
                await apiClient.put('/timesheet/update/', {
                    shift_id: selectedCell.existingShift.id,
                    ...payload
                });
                message.success('Shift updated successfully');
            } else {
                // Create new
                await apiClient.post('/timesheet/assign/', payload);
                message.success('Shift assigned successfully');
            }

            setIsAssignModalVisible(false);
            fetchTimesheet();
        } catch (error) {
            console.error('Assignment failed:', error);
            message.error(error.response?.data?.message || 'Failed to save shift');
        }
    };

    // Delete shift
    const handleDeleteShift = async (shiftId) => {
        try {
            await apiClient.post('/timesheet/delete/', { shift_id: shiftId });
            message.success('Shift deleted');
            setIsAssignModalVisible(false);
            fetchTimesheet();
        } catch (error) {
            message.error('Failed to delete shift');
        }
    };

    // Approve shift
    const handleApprove = async (shiftId) => {
        try {
            await apiClient.post(`/shifts/${shiftId}/approve/`);
            message.success('Shift approved');
            fetchTimesheet();
        } catch (error) {
            message.error('Failed to approve shift');
        }
    };

    // Reject shift
    const openRejectModal = (shiftId) => {
        setRejectTarget(shiftId);
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
            fetchTimesheet();
        } catch (error) {
            message.error('Failed to reject shift');
        }
    };

    // Copy week
    const handleCopyWeek = async () => {
        try {
            const values = await copyForm.validateFields();
            const targetDate = values.target_week;
            // Get Monday of the target week
            const targetMonday = targetDate.clone().startOf('week');

            await apiClient.post('/timesheet/copy-week/', {
                source_start_date: weekStart.format('YYYY-MM-DD'),
                target_start_date: targetMonday.format('YYYY-MM-DD')
            });
            message.success('Week copied successfully');
            setIsCopyWeekModalVisible(false);
            copyForm.resetFields();
            // Navigate to the new week
            setWeekStart(targetMonday);
        } catch (error) {
            console.error('Copy week failed:', error);
            message.error(error.response?.data?.message || 'Failed to copy week');
        }
    };

    // Fill Week - assign same template to all drivers for entire week
    const handleFillWeek = async () => {
        try {
            const values = await fillWeekForm.validateFields();

            await apiClient.post('/timesheet/fill-week/', {
                driver_ids: values.driver_ids,
                start_date: weekStart.format('YYYY-MM-DD'),
                template_id: values.template_id,
                skip_existing: values.skip_existing !== false
            });
            message.success('Week filled successfully');
            setIsFillWeekModalVisible(false);
            fillWeekForm.resetFields();
            fetchTimesheet();
        } catch (error) {
            console.error('Fill week failed:', error);
            message.error(error.response?.data?.message || 'Failed to fill week');
        }
    };

    // Fill Month - assign same template to drivers for entire month
    const handleFillMonth = async () => {
        try {
            const values = await fillMonthForm.validateFields();
            const targetMonth = values.target_month;

            await apiClient.post('/timesheet/fill-month/', {
                driver_ids: values.driver_ids,
                year: targetMonth.year(),
                month: targetMonth.month() + 1, // moment months are 0-indexed
                template_id: values.template_id,
                include_weekends: values.include_weekends !== false,
                skip_existing: values.skip_existing !== false
            });
            message.success('Month filled successfully');
            setIsFillMonthModalVisible(false);
            fillMonthForm.resetFields();
            fetchTimesheet();
        } catch (error) {
            console.error('Fill month failed:', error);
            message.error(error.response?.data?.message || 'Failed to fill month');
        }
    };

    // Clear Week - delete all shifts for current week
    const handleClearWeek = async (onlyPending = false) => {
        try {
            await apiClient.post('/timesheet/clear-week/', {
                start_date: weekStart.format('YYYY-MM-DD'),
                only_pending: onlyPending
            });
            message.success('Week cleared successfully');
            fetchTimesheet();
        } catch (error) {
            console.error('Clear week failed:', error);
            message.error(error.response?.data?.message || 'Failed to clear week');
        }
    };

    // ===========================================
    // Template Management Functions
    // ===========================================

    // Fetch templates (refresh)
    const fetchTemplates = async () => {
        try {
            const response = await apiClient.get('/shift-templates/');
            const templatesData = response.data.results || response.data;
            setTemplates(templatesData);
        } catch (error) {
            console.error('Failed to fetch templates:', error);
        }
    };

    // Open template modal for creating new template
    const openCreateTemplate = () => {
        setEditingTemplate(null);
        templateForm.resetFields();
        templateForm.setFieldsValue({
            color: '#1890ff'
        });
        setIsTemplateModalVisible(true);
    };

    // Open template modal for editing
    const openEditTemplate = (template) => {
        setEditingTemplate(template);
        templateForm.setFieldsValue({
            name: template.name,
            start_time: template.start_time ? moment(template.start_time, 'HH:mm:ss') : null,
            end_time: template.end_time ? moment(template.end_time, 'HH:mm:ss') : null,
            color: template.color || '#1890ff'
        });
        setIsTemplateModalVisible(true);
    };

    // Submit template (create or update)
    const handleTemplateSubmit = async () => {
        try {
            const values = await templateForm.validateFields();
            setTemplateLoading(true);

            // Auto-generate code from name: "Morning Shift" -> "MORNING_SHIFT"
            const autoCode = values.name
                .toUpperCase()
                .replace(/[^A-Z0-9]+/g, '_')
                .replace(/^_|_$/g, '')
                .substring(0, 20);

            const payload = {
                name: values.name,
                code: editingTemplate?.id ? editingTemplate.code : autoCode, // Keep existing code for edits
                start_time: values.start_time.format('HH:mm:ss'),
                end_time: values.end_time.format('HH:mm:ss'),
                color: values.color || '#1890ff',
                is_active: true
            };

            if (editingTemplate?.id) {
                await apiClient.put(`/shift-templates/${editingTemplate.id}/`, payload);
                message.success('Template updated successfully');
            } else {
                await apiClient.post('/shift-templates/', payload);
                message.success('Template created successfully');
            }

            setIsTemplateModalVisible(false);
            templateForm.resetFields();
            setEditingTemplate(null);
            fetchTemplates();
            fetchTimesheet();
        } catch (error) {
            console.error('Template save failed:', error);
            if (error.response?.data?.code) {
                message.error('Template code already exists');
            } else {
                message.error(error.response?.data?.message || 'Failed to save template');
            }
        } finally {
            setTemplateLoading(false);
        }
    };

    // Delete template
    const handleDeleteTemplate = async (templateId) => {
        try {
            await apiClient.delete(`/shift-templates/${templateId}/`);
            message.success('Template deleted');
            fetchTemplates();
        } catch (error) {
            console.error('Delete template failed:', error);
            message.error(error.response?.data?.message || 'Failed to delete template');
        }
    };

    // Predefined colors for templates
    const TEMPLATE_COLORS = [
        '#1890ff', '#52c41a', '#fa8c16', '#722ed1', '#eb2f96',
        '#faad14', '#13c2c2', '#2f54eb', '#a0d911', '#f5222d'
    ];

    // Render shift cell
    const renderShiftCell = (driver, date) => {
        const shift = driver.shifts[date];
        const isToday = moment(date).isSame(moment(), 'day');

        if (!shift) {
            return (
                <div
                    className="timesheet-cell empty"
                    onClick={() => handleCellClick(driver, date)}
                    style={{
                        minHeight: 60,
                        padding: 8,
                        cursor: 'pointer',
                        border: isToday ? '2px solid #1890ff' : '1px dashed #d9d9d9',
                        borderRadius: 6,
                        background: isToday ? '#e6f7ff' : '#fafafa',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#f0f5ff';
                        e.currentTarget.style.borderColor = '#1890ff';
                    }}
                    onMouseLeave={(e) => {
                        e.currentTarget.style.background = isToday ? '#e6f7ff' : '#fafafa';
                        e.currentTarget.style.borderColor = isToday ? '#1890ff' : '#d9d9d9';
                    }}
                >
                    <PlusOutlined style={{ color: '#bfbfbf', fontSize: 16 }} />
                </div>
            );
        }

        const shiftType = shift.shift_type || 'CUSTOM';
        const status = shift.status || 'PENDING';
        const colors = SHIFT_COLORS[shiftType] || SHIFT_COLORS.CUSTOM;
        const statusColors = SHIFT_COLORS[status];

        return (
            <div
                className="timesheet-cell filled"
                onClick={() => handleCellClick(driver, date)}
                style={{
                    minHeight: 60,
                    padding: 8,
                    cursor: 'pointer',
                    border: `2px solid ${statusColors.border}`,
                    borderRadius: 6,
                    background: colors.bg,
                    transition: 'all 0.2s'
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <Tag
                        color={statusColors.border}
                        style={{
                            fontSize: 10,
                            padding: '0 4px',
                            borderRadius: 4,
                            margin: 0
                        }}
                    >
                        {status}
                    </Tag>
                    {canApproveReject && status === 'PENDING' && (
                        <Space size={2}>
                            <Tooltip title="Approve">
                                <Button
                                    type="text"
                                    size="small"
                                    icon={<CheckCircleOutlined style={{ color: '#52c41a', fontSize: 14 }} />}
                                    onClick={(e) => { e.stopPropagation(); handleApprove(shift.id); }}
                                    style={{ padding: 0, height: 'auto' }}
                                />
                            </Tooltip>
                            <Tooltip title="Reject">
                                <Button
                                    type="text"
                                    size="small"
                                    icon={<CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 14 }} />}
                                    onClick={(e) => { e.stopPropagation(); openRejectModal(shift.id); }}
                                    style={{ padding: 0, height: 'auto' }}
                                />
                            </Tooltip>
                        </Space>
                    )}
                </div>
                <div style={{ fontSize: 11, fontWeight: 600, color: colors.text }}>
                    {shiftType}
                </div>
                <div style={{ fontSize: 10, color: '#666', marginTop: 2 }}>
                    <ClockCircleOutlined style={{ marginRight: 4 }} />
                    {moment(shift.start_time).format('HH:mm')} - {moment(shift.end_time).format('HH:mm')}
                </div>
                {shift.vehicle_details && (
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>
                        <CarOutlined style={{ marginRight: 4 }} />
                        {shift.vehicle_details.registration_no}
                    </div>
                )}
            </div>
        );
    };

    // Build table columns
    const columns = [
        {
            title: (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <UserOutlined />
                    <span>Driver</span>
                </div>
            ),
            dataIndex: 'name',
            key: 'driver',
            fixed: 'left',
            width: 180,
            render: (name, record) => (
                <div>
                    <Text strong style={{ display: 'block' }}>{name}</Text>
                    {record.vehicle && (
                        <Text type="secondary" style={{ fontSize: 12 }}>
                            <CarOutlined style={{ marginRight: 4 }} />
                            {record.vehicle}
                        </Text>
                    )}
                </div>
            )
        },
        ...timesheetData.dates.map(date => {
            const momentDate = moment(date);
            const isToday = momentDate.isSame(moment(), 'day');
            const isWeekend = momentDate.day() === 0 || momentDate.day() === 6;

            return {
                title: (
                    <div style={{
                        textAlign: 'center',
                        background: isToday ? '#e6f7ff' : isWeekend ? '#f5f5f5' : 'transparent',
                        padding: '4px 8px',
                        borderRadius: 4
                    }}>
                        <div style={{ fontWeight: isToday ? 700 : 500, color: isToday ? '#1890ff' : '#333' }}>
                            {momentDate.format('ddd')}
                        </div>
                        <div style={{
                            fontSize: 18,
                            fontWeight: 600,
                            color: isToday ? '#1890ff' : '#333'
                        }}>
                            {momentDate.format('D')}
                        </div>
                        <div style={{ fontSize: 11, color: '#888' }}>
                            {momentDate.format('MMM')}
                        </div>
                    </div>
                ),
                dataIndex: date,
                key: date,
                width: 130,
                render: (_, record) => renderShiftCell(record, date)
            };
        })
    ];

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
                            <CalendarOutlined style={{ marginRight: 12 }} />
                            Shift Timeline
                        </Title>
                        <Text type="secondary">
                            Assign and manage driver shifts in calendar view
                        </Text>
                    </div>

                    <Space size="middle" wrap>
                        <Button
                            icon={<SettingOutlined />}
                            onClick={openCreateTemplate}
                            style={{ borderColor: '#722ed1', color: '#722ed1' }}
                        >
                            Manage Templates
                        </Button>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={fetchTimesheet}
                            loading={loading}
                        >
                            Refresh
                        </Button>
                        <Button
                            type="primary"
                            icon={<ScheduleOutlined />}
                            onClick={() => setIsFillWeekModalVisible(true)}
                        >
                            Fill Week
                        </Button>
                        <Button
                            icon={<CalendarOutlined />}
                            onClick={() => setIsFillMonthModalVisible(true)}
                        >
                            Fill Month
                        </Button>
                        <Button
                            icon={<CopyOutlined />}
                            onClick={() => setIsCopyWeekModalVisible(true)}
                        >
                            Copy Week
                        </Button>
                        <Dropdown
                            menu={{
                                items: [
                                    {
                                        key: 'pending',
                                        label: 'Clear Pending Only',
                                        icon: <ClearOutlined />,
                                        onClick: () => handleClearWeek(true)
                                    },
                                    {
                                        key: 'all',
                                        label: 'Clear All Shifts',
                                        icon: <DeleteOutlined />,
                                        danger: true,
                                        onClick: () => {
                                            Modal.confirm({
                                                title: 'Clear All Shifts',
                                                content: `Are you sure you want to delete ALL shifts for this week (${weekStart.format('MMM D')} - ${weekStart.clone().add(6, 'days').format('MMM D')})?`,
                                                okText: 'Clear All',
                                                okButtonProps: { danger: true },
                                                onOk: () => handleClearWeek(false)
                                            });
                                        }
                                    }
                                ]
                            }}
                        >
                            <Button danger icon={<ClearOutlined />}>
                                Clear Week <DownOutlined />
                            </Button>
                        </Dropdown>
                    </Space>
                </div>

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
                    <Button
                        icon={<LeftOutlined />}
                        onClick={goToPreviousWeek}
                        size="large"
                    />
                    <div style={{ textAlign: 'center', minWidth: 200 }}>
                        <Text strong style={{ fontSize: 16 }}>
                            {weekStart.format('MMM D')} - {weekStart.clone().add(6, 'days').format('MMM D, YYYY')}
                        </Text>
                    </div>
                    <Button
                        icon={<RightOutlined />}
                        onClick={goToNextWeek}
                        size="large"
                    />
                    <Button
                        type="primary"
                        onClick={goToCurrentWeek}
                        style={{ marginLeft: 16 }}
                    >
                        Today
                    </Button>
                </div>

                {/* Legend */}
                <div style={{
                    display: 'flex',
                    gap: 16,
                    marginBottom: 16,
                    flexWrap: 'wrap'
                }}>
                    <Text type="secondary">Status:</Text>
                    <Badge color="#faad14" text="Pending" />
                    <Badge color="#52c41a" text="Approved" />
                    <Badge color="#ff4d4f" text="Rejected" />
                </div>

                {/* Timesheet Grid */}
                <Spin spinning={loading}>
                    {timesheetData.drivers.length > 0 ? (
                        <Table
                            columns={columns}
                            dataSource={timesheetData.drivers}
                            rowKey="id"
                            pagination={false}
                            scroll={{ x: 'max-content' }}
                            bordered
                            size="middle"
                            style={{
                                background: '#fff',
                                borderRadius: 8,
                                overflow: 'hidden'
                            }}
                        />
                    ) : (
                        <Empty
                            description="No drivers found"
                            style={{ padding: 60 }}
                        />
                    )}
                </Spin>
            </Card>

            {/* Assignment Modal */}
            <Modal
                title={
                    <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 12 }}>
                        <Title level={4} style={{ margin: 0 }}>
                            {selectedCell?.existingShift ? 'Edit Shift' : 'Assign Shift'}
                        </Title>
                        <Text type="secondary">
                            {selectedCell?.driverName} - {selectedCell?.date && moment(selectedCell.date).format('dddd, MMM D, YYYY')}
                        </Text>
                    </div>
                }
                open={isAssignModalVisible}
                onOk={handleAssignSubmit}
                onCancel={() => setIsAssignModalVisible(false)}
                okText={selectedCell?.existingShift ? 'Update' : 'Assign'}
                width={480}
                footer={[
                    selectedCell?.existingShift && (
                        <Popconfirm
                            key="delete"
                            title="Delete this shift?"
                            onConfirm={() => handleDeleteShift(selectedCell.existingShift.id)}
                            okText="Delete"
                            cancelText="Cancel"
                        >
                            <Button danger icon={<DeleteOutlined />}>
                                Delete
                            </Button>
                        </Popconfirm>
                    ),
                    <Button key="cancel" onClick={() => setIsAssignModalVisible(false)}>
                        Cancel
                    </Button>,
                    <Button key="submit" type="primary" onClick={handleAssignSubmit}>
                        {selectedCell?.existingShift ? 'Update' : 'Assign'}
                    </Button>
                ]}
            >
                <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                    <Form.Item
                        name="vehicle"
                        label={<Text strong>Vehicle</Text>}
                        rules={[{ required: true, message: 'Please select a vehicle' }]}
                    >
                        <Select placeholder="Select Vehicle" size="large">
                            {vehicles.map(v => (
                                <Option key={v.id} value={v.id}>
                                    <CarOutlined style={{ marginRight: 8 }} />
                                    {v.registration_no}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="template"
                        label={<Text strong>Shift Template</Text>}
                    >
                        <Select
                            placeholder="Select a template (or use custom times below)"
                            size="large"
                            allowClear
                            onChange={(val) => {
                                if (val) {
                                    form.setFieldsValue({ start_time: null, end_time: null });
                                }
                            }}
                        >
                            {templates.map(t => (
                                <Option key={t.id} value={t.id}>
                                    <Tag color={t.color || 'blue'} style={{ marginRight: 8 }}>{t.code}</Tag>
                                    {t.name} ({t.display_time})
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item
                                name="start_time"
                                label={<Text strong>Start Time</Text>}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    size="large"
                                    style={{ width: '100%' }}
                                    placeholder="Start"
                                    onChange={() => form.setFieldsValue({ template: null })}
                                />
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item
                                name="end_time"
                                label={<Text strong>End Time</Text>}
                            >
                                <TimePicker
                                    format="HH:mm"
                                    size="large"
                                    style={{ width: '100%' }}
                                    placeholder="End"
                                    onChange={() => form.setFieldsValue({ template: null })}
                                />
                            </Form.Item>
                        </Col>
                    </Row>

                    <Form.Item
                        name="notes"
                        label={<Text strong>Notes (Optional)</Text>}
                    >
                        <Input.TextArea
                            rows={2}
                            placeholder="Add any notes about this shift..."
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Copy Week Modal */}
            <Modal
                title="Copy Week Schedule"
                open={isCopyWeekModalVisible}
                onOk={handleCopyWeek}
                onCancel={() => setIsCopyWeekModalVisible(false)}
                okText="Copy"
            >
                <Form form={copyForm} layout="vertical">
                    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                        Copy all shifts from current week ({weekStart.format('MMM D')} - {weekStart.clone().add(6, 'days').format('MMM D')}) to another week.
                    </Text>
                    <Form.Item
                        name="target_week"
                        label="Target Week (select any day in the target week)"
                        rules={[{ required: true, message: 'Please select target week' }]}
                    >
                        <DatePicker
                            size="large"
                            style={{ width: '100%' }}
                            picker="week"
                        />
                    </Form.Item>
                </Form>
            </Modal>

            {/* Fill Week Modal */}
            <Modal
                title={
                    <div>
                        <ScheduleOutlined style={{ marginRight: 8 }} />
                        Fill Week with Shifts
                    </div>
                }
                open={isFillWeekModalVisible}
                onOk={handleFillWeek}
                onCancel={() => { setIsFillWeekModalVisible(false); fillWeekForm.resetFields(); }}
                okText="Fill Week"
                width={500}
            >
                <Form form={fillWeekForm} layout="vertical" initialValues={{ skip_existing: true }}>
                    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                        Assign the same shift template to selected drivers for the entire week ({weekStart.format('MMM D')} - {weekStart.clone().add(6, 'days').format('MMM D')}).
                    </Text>

                    <Form.Item
                        name="driver_ids"
                        label={<Text strong>Select Drivers</Text>}
                        rules={[{ required: true, message: 'Please select at least one driver' }]}
                    >
                        <Select
                            mode="multiple"
                            placeholder="Select drivers"
                            size="large"
                            maxTagCount={3}
                            style={{ width: '100%' }}
                        >
                            {drivers.map(d => (
                                <Option key={d.id} value={d.id}>
                                    <UserOutlined style={{ marginRight: 8 }} />
                                    {d.name}
                                    {d.vehicle && <Text type="secondary"> - {d.vehicle}</Text>}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="template_id"
                        label={<Text strong>Shift Template</Text>}
                        rules={[{ required: true, message: 'Please select a template' }]}
                    >
                        <Select placeholder="Select shift template" size="large">
                            {templates.map(t => (
                                <Option key={t.id} value={t.id}>
                                    <Tag color={t.color || 'blue'} style={{ marginRight: 8 }}>{t.code}</Tag>
                                    {t.name} ({t.display_time})
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item name="skip_existing" valuePropName="checked">
                        <Checkbox>Skip days with existing shifts</Checkbox>
                    </Form.Item>
                </Form>
            </Modal>

            {/* Fill Month Modal */}
            <Modal
                title={
                    <div>
                        <CalendarOutlined style={{ marginRight: 8 }} />
                        Fill Month with Shifts
                    </div>
                }
                open={isFillMonthModalVisible}
                onOk={handleFillMonth}
                onCancel={() => { setIsFillMonthModalVisible(false); fillMonthForm.resetFields(); }}
                okText="Fill Month"
                width={500}
            >
                <Form form={fillMonthForm} layout="vertical" initialValues={{ skip_existing: true, include_weekends: true }}>
                    <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
                        Assign the same shift template to selected drivers for an entire month.
                    </Text>

                    <Form.Item
                        name="target_month"
                        label={<Text strong>Select Month</Text>}
                        rules={[{ required: true, message: 'Please select a month' }]}
                    >
                        <DatePicker
                            picker="month"
                            size="large"
                            style={{ width: '100%' }}
                            placeholder="Select month"
                        />
                    </Form.Item>

                    <Form.Item
                        name="driver_ids"
                        label={<Text strong>Select Drivers</Text>}
                        rules={[{ required: true, message: 'Please select at least one driver' }]}
                    >
                        <Select
                            mode="multiple"
                            placeholder="Select drivers"
                            size="large"
                            maxTagCount={3}
                            style={{ width: '100%' }}
                        >
                            {drivers.map(d => (
                                <Option key={d.id} value={d.id}>
                                    <UserOutlined style={{ marginRight: 8 }} />
                                    {d.name}
                                    {d.vehicle && <Text type="secondary"> - {d.vehicle}</Text>}
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="template_id"
                        label={<Text strong>Shift Template</Text>}
                        rules={[{ required: true, message: 'Please select a template' }]}
                    >
                        <Select placeholder="Select shift template" size="large">
                            {templates.map(t => (
                                <Option key={t.id} value={t.id}>
                                    <Tag color={t.color || 'blue'} style={{ marginRight: 8 }}>{t.code}</Tag>
                                    {t.name} ({t.display_time})
                                </Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Row gutter={16}>
                        <Col span={12}>
                            <Form.Item name="include_weekends" valuePropName="checked">
                                <Checkbox>Include weekends</Checkbox>
                            </Form.Item>
                        </Col>
                        <Col span={12}>
                            <Form.Item name="skip_existing" valuePropName="checked">
                                <Checkbox>Skip existing shifts</Checkbox>
                            </Form.Item>
                        </Col>
                    </Row>
                </Form>
            </Modal>

            {/* Reject Modal */}
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
                    placeholder="Enter rejection reason..."
                />
            </Modal>

            {/* Template Management Modal */}
            <Modal
                title={
                    <div style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 12 }}>
                        <Title level={4} style={{ margin: 0 }}>
                            <SettingOutlined style={{ marginRight: 8 }} />
                            {editingTemplate ? 'Edit Shift Template' : 'Manage Shift Templates'}
                        </Title>
                        <Text type="secondary">
                            {editingTemplate ? 'Modify template settings' : 'Create and manage reusable shift templates'}
                        </Text>
                    </div>
                }
                open={isTemplateModalVisible}
                onCancel={() => {
                    setIsTemplateModalVisible(false);
                    templateForm.resetFields();
                    setEditingTemplate(null);
                }}
                width={700}
                footer={editingTemplate ? [
                    <Button key="cancel" onClick={() => { setIsTemplateModalVisible(false); setEditingTemplate(null); templateForm.resetFields(); }}>
                        Cancel
                    </Button>,
                    <Button key="submit" type="primary" icon={<SaveOutlined />} loading={templateLoading} onClick={handleTemplateSubmit}>
                        Save Changes
                    </Button>
                ] : null}
            >
                {!editingTemplate ? (
                    // List View with Create Form
                    <div>
                        {/* Existing Templates */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                                <Text strong style={{ fontSize: 14 }}>Existing Templates</Text>
                                <Button type="primary" size="small" icon={<PlusOutlined />} onClick={() => setEditingTemplate({})}>
                                    Create New
                                </Button>
                            </div>
                            {templates.length > 0 ? (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {templates.map(template => (
                                        <div
                                            key={template.id}
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                alignItems: 'center',
                                                padding: '12px 16px',
                                                background: '#fafafa',
                                                borderRadius: 8,
                                                border: `2px solid ${template.color || '#1890ff'}`
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                                <div
                                                    style={{
                                                        width: 8,
                                                        height: 40,
                                                        borderRadius: 4,
                                                        background: template.color || '#1890ff'
                                                    }}
                                                />
                                                <div>
                                                    <div style={{ fontWeight: 600 }}>
                                                        <Tag color={template.color || 'blue'}>{template.code}</Tag>
                                                        {template.name}
                                                    </div>
                                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                                        <ClockCircleOutlined style={{ marginRight: 4 }} />
                                                        {template.display_time || `${template.start_time} - ${template.end_time}`}
                                                    </Text>
                                                </div>
                                            </div>
                                            <Space>
                                                <Tooltip title="Edit">
                                                    <Button
                                                        type="text"
                                                        icon={<EditOutlined />}
                                                        onClick={() => openEditTemplate(template)}
                                                    />
                                                </Tooltip>
                                                <Popconfirm
                                                    title="Delete this template?"
                                                    description="Shifts using this template will not be affected."
                                                    onConfirm={() => handleDeleteTemplate(template.id)}
                                                    okText="Delete"
                                                    cancelText="Cancel"
                                                    okButtonProps={{ danger: true }}
                                                >
                                                    <Tooltip title="Delete">
                                                        <Button
                                                            type="text"
                                                            danger
                                                            icon={<DeleteOutlined />}
                                                        />
                                                    </Tooltip>
                                                </Popconfirm>
                                            </Space>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <Empty
                                    description="No templates created yet"
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                    style={{ padding: 24, background: '#fafafa', borderRadius: 8 }}
                                >
                                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setEditingTemplate({})}>
                                        Create First Template
                                    </Button>
                                </Empty>
                            )}
                        </div>
                    </div>
                ) : (
                    // Create/Edit Form
                    <Form form={templateForm} layout="vertical" style={{ marginTop: 16 }}>
                        <Form.Item
                            name="name"
                            label={<Text strong>Template Name</Text>}
                            rules={[{ required: true, message: 'Please enter template name' }]}
                        >
                            <Input
                                placeholder="e.g., Morning Shift, Night Shift"
                                size="large"
                            />
                        </Form.Item>

                        <Row gutter={16}>
                            <Col span={12}>
                                <Form.Item
                                    name="start_time"
                                    label={<Text strong>Start Time</Text>}
                                    rules={[{ required: true, message: 'Please select start time' }]}
                                >
                                    <TimePicker
                                        format="HH:mm"
                                        size="large"
                                        style={{ width: '100%' }}
                                        placeholder="Select start time"
                                    />
                                </Form.Item>
                            </Col>
                            <Col span={12}>
                                <Form.Item
                                    name="end_time"
                                    label={<Text strong>End Time</Text>}
                                    rules={[{ required: true, message: 'Please select end time' }]}
                                >
                                    <TimePicker
                                        format="HH:mm"
                                        size="large"
                                        style={{ width: '100%' }}
                                        placeholder="Select end time"
                                    />
                                </Form.Item>
                            </Col>
                        </Row>

                        <Form.Item
                            name="color"
                            label={<Text strong><BgColorsOutlined style={{ marginRight: 4 }} />Color</Text>}
                        >
                            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {TEMPLATE_COLORS.map(color => (
                                    <Tooltip title={color} key={color}>
                                        <div
                                            onClick={() => templateForm.setFieldsValue({ color })}
                                            style={{
                                                width: 32,
                                                height: 32,
                                                borderRadius: 6,
                                                background: color,
                                                cursor: 'pointer',
                                                border: templateForm.getFieldValue('color') === color
                                                    ? '3px solid #000'
                                                    : '2px solid transparent',
                                                transition: 'all 0.2s'
                                            }}
                                        />
                                    </Tooltip>
                                ))}
                            </div>
                        </Form.Item>

                        {!editingTemplate?.id && (
                            <div style={{ textAlign: 'right', marginTop: 16 }}>
                                <Space>
                                    <Button onClick={() => { setEditingTemplate(null); templateForm.resetFields(); }}>
                                        Back to List
                                    </Button>
                                    <Button type="primary" icon={<SaveOutlined />} loading={templateLoading} onClick={handleTemplateSubmit}>
                                        Create Template
                                    </Button>
                                </Space>
                            </div>
                        )}
                    </Form>
                )}
            </Modal>

            <style>{`
                .timesheet-cell:hover {
                    transform: scale(1.02);
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
            `}</style>
        </div>
    );
};

export default TimesheetManagement;
