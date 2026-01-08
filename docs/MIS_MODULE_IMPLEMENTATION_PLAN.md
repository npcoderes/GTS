# MIS Module Implementation Plan
## Management Information System with Advanced Reporting

**Date:** January 8, 2026  
**Version:** 1.0

---

## Table of Contents

1. [Overview](#overview)
2. [Report Types](#report-types)
3. [Role-Based Access Control](#role-based-access-control)
4. [Report Builder Features](#report-builder-features)
5. [Database Schema](#database-schema)
6. [Backend Architecture](#backend-architecture)
7. [Frontend Architecture](#frontend-architecture)
8. [Implementation Steps](#implementation-steps)

---

## Overview

The MIS Module provides a powerful, flexible reporting system similar to Crystal Reports, allowing users to generate customized reports with various combinations of filters, groupings, and data points.

### Key Features:
- **Dynamic Report Builder**: Create reports with any combination of filters
- **Role-Based Data Access**: Automatic data filtering based on user role
- **Multiple Export Formats**: PDF, Excel, CSV
- **Saved Report Templates**: Save and reuse report configurations
- **Scheduled Reports**: Auto-generate and email reports
- **Visual Analytics**: Charts and graphs for data visualization
- **Drill-Down Capability**: Click to see detailed data

---

## Report Types

### 1. Trip Reports
- **Trip Summary Report**
  - Total trips by status
  - Distance covered
  - Fuel consumption
  - Revenue generated
  
- **Trip Detail Report**
  - Complete trip lifecycle
  - Filling details (MS station, quantity, time)
  - Decanting details (DBS station, quantity, time)
  - Driver and vehicle information
  - Duration and delays

- **Trip Performance Report**
  - On-time delivery percentage
  - Average trip duration
  - Variance analysis (planned vs actual)
  - Efficiency metrics

### 2. Driver Reports
- **Driver Performance Report**
  - Trips completed
  - Distance covered
  - Fuel efficiency
  - On-time percentage
  - Incidents/violations

- **Driver Utilization Report**
  - Active hours
  - Idle time
  - Shift compliance
  - Availability

### 3. Vehicle Reports
- **Vehicle Utilization Report**
  - Total trips
  - Distance covered
  - Fuel consumption
  - Maintenance history
  - Downtime analysis

- **Vehicle Performance Report**
  - Fuel efficiency trends
  - Trip completion rate
  - Average load capacity utilization

### 4. Station Reports
- **MS Station Report**
  - Total filling operations
  - Quantity dispensed
  - Average filling time
  - Peak hours analysis
  - Bay utilization

- **DBS Station Report**
  - Total decanting operations
  - Quantity received
  - Average decanting time
  - Stock levels
  - Variance analysis

### 5. Customer Reports
- **Customer Delivery Report**
  - Orders fulfilled
  - On-time delivery rate
  - Quantity delivered
  - Pending orders

- **End-to-End Customer Journey**
  - Order placement to delivery
  - All touchpoints
  - Time at each stage
  - Delays and reasons

### 6. Variance Reports
- **Quantity Variance Report**
  - Filled vs Decanted quantity
  - Loss/gain analysis
  - Variance by driver/vehicle/route
  - Trend analysis

- **Time Variance Report**
  - Planned vs actual time
  - Delay analysis
  - Bottleneck identification

### 7. Financial Reports
- **Revenue Report**
  - Revenue by customer
  - Revenue by route
  - Revenue trends

- **Cost Analysis Report**
  - Fuel costs
  - Maintenance costs
  - Driver costs
  - Total trip costs

---

## Role-Based Access Control

### Super Admin
- **Access**: All data across all stations
- **Permissions**: 
  - View all reports
  - Create/edit/delete report templates
  - Schedule reports
  - Export in all formats
  - Access financial data

### Admin
- **Access**: All data across all stations
- **Permissions**: 
  - View all reports
  - Create/edit report templates
  - Schedule reports
  - Export in all formats
  - Limited financial data access

### EIC (Engineer In-Charge)
- **Access**: Only assigned stations
- **Data Filtering**: 
  - Trips involving assigned MS/DBS stations
  - Drivers assigned to their stations
  - Vehicles operating in their stations
- **Permissions**:
  - View operational reports
  - Create personal report templates
  - Export to PDF/Excel
  - No financial data access

### Transport Admin
- **Access**: Own vendor's data
- **Data Filtering**:
  - Only their drivers
  - Only their vehicles
  - Trips assigned to their resources
- **Permissions**:
  - View operational reports
  - Basic export functionality

### Vendor
- **Access**: Own vendor's data only
- **Data Filtering**: Same as Transport Admin
- **Permissions**: View-only reports

---

## Report Builder Features

### 1. Filter Options

#### Date Filters
- Date range (from - to)
- Predefined ranges:
  - Today
  - Yesterday
  - This Week
  - Last Week
  - This Month
  - Last Month
  - This Quarter
  - Last Quarter
  - This Year
  - Custom Range

#### Entity Filters
- **Driver**: Multi-select dropdown
- **Vehicle**: Multi-select dropdown
- **MS Station**: Multi-select dropdown
- **DBS Station**: Multi-select dropdown
- **Customer**: Multi-select dropdown
- **Route**: Multi-select dropdown
- **Vendor**: Multi-select dropdown (admin only)

#### Status Filters
- Trip Status: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
- Shift Status: PENDING, APPROVED, REJECTED
- Token Status: ALLOCATED, ACTIVE, COMPLETED

#### Metric Filters
- Quantity range (min - max)
- Distance range
- Duration range
- Variance threshold

### 2. Grouping Options
- Group by Driver
- Group by Vehicle
- Group by MS Station
- Group by DBS Station
- Group by Customer
- Group by Date (Daily, Weekly, Monthly)
- Group by Shift Type
- Group by Route

### 3. Sorting Options
- Sort by Date (Asc/Desc)
- Sort by Quantity
- Sort by Distance
- Sort by Duration
- Sort by Variance
- Sort by Revenue

### 4. Column Selection
Users can choose which columns to display:
- Trip ID
- Date/Time
- Driver Name
- Vehicle Number
- MS Station
- DBS Station
- Customer
- Filled Quantity
- Decanted Quantity
- Variance
- Distance
- Duration
- Status
- Revenue
- Cost

### 5. Aggregations
- Sum
- Average
- Count
- Min/Max
- Percentage
- Variance

---

## Database Schema

### New Tables

#### 1. ReportTemplate
```python
class ReportTemplate(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    report_type = models.CharField(max_length=50)  # TRIP, DRIVER, VEHICLE, etc.
    created_by = models.ForeignKey(User)
    is_public = models.BooleanField(default=False)  # Shared with all users
    configuration = models.JSONField()  # Stores filters, columns, grouping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

#### 2. ScheduledReport
```python
class ScheduledReport(models.Model):
    template = models.ForeignKey(ReportTemplate)
    schedule_type = models.CharField(max_length=20)  # DAILY, WEEKLY, MONTHLY
    schedule_time = models.TimeField()
    recipients = models.JSONField()  # List of email addresses
    format = models.CharField(max_length=10)  # PDF, EXCEL, CSV
    is_active = models.BooleanField(default=True)
    last_run = models.DateTimeField(null=True)
    next_run = models.DateTimeField()
```

#### 3. ReportExecution
```python
class ReportExecution(models.Model):
    template = models.ForeignKey(ReportTemplate, null=True)
    executed_by = models.ForeignKey(User)
    parameters = models.JSONField()  # Filters used
    execution_time = models.DateTimeField(auto_now_add=True)
    duration = models.FloatField()  # Seconds
    row_count = models.IntegerField()
    file_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20)  # SUCCESS, FAILED
```

---

## Backend Architecture

### API Endpoints

#### Report Templates
```
GET    /api/mis/templates/              # List all templates
POST   /api/mis/templates/              # Create template
GET    /api/mis/templates/{id}/         # Get template details
PUT    /api/mis/templates/{id}/         # Update template
DELETE /api/mis/templates/{id}/         # Delete template
POST   /api/mis/templates/{id}/clone/   # Clone template
```

#### Report Generation
```
POST   /api/mis/reports/generate/       # Generate report
POST   /api/mis/reports/preview/        # Preview report (first 100 rows)
POST   /api/mis/reports/export/         # Export report (PDF/Excel/CSV)
GET    /api/mis/reports/history/        # Execution history
```

#### Report Scheduling
```
GET    /api/mis/schedules/              # List scheduled reports
POST   /api/mis/schedules/              # Create schedule
PUT    /api/mis/schedules/{id}/         # Update schedule
DELETE /api/mis/schedules/{id}/         # Delete schedule
POST   /api/mis/schedules/{id}/run/     # Run immediately
```

#### Metadata
```
GET    /api/mis/metadata/columns/       # Available columns
GET    /api/mis/metadata/filters/       # Available filters
GET    /api/mis/metadata/drivers/       # Drivers for filter
GET    /api/mis/metadata/vehicles/      # Vehicles for filter
GET    /api/mis/metadata/stations/      # Stations for filter
```

### Report Generation Engine

```python
class ReportEngine:
    def __init__(self, user, config):
        self.user = user
        self.config = config
        self.query = None
        
    def build_query(self):
        """Build Django ORM query based on configuration"""
        # Start with base queryset
        # Apply role-based filtering
        # Apply user filters
        # Apply grouping
        # Apply sorting
        
    def apply_role_filter(self, queryset):
        """Filter data based on user role"""
        if self.user.role == 'EIC':
            # Filter by assigned stations
            assigned_stations = self.user.eic_stations.all()
            queryset = queryset.filter(
                Q(ms_station__in=assigned_stations) |
                Q(dbs_station__in=assigned_stations)
            )
        elif self.user.role == 'TRANSPORT_ADMIN':
            # Filter by vendor
            queryset = queryset.filter(driver__vendor=self.user.vendor)
        return queryset
        
    def execute(self):
        """Execute query and return results"""
        
    def export_pdf(self, data):
        """Export to PDF using ReportLab"""
        
    def export_excel(self, data):
        """Export to Excel using openpyxl"""
        
    def export_csv(self, data):
        """Export to CSV"""
```

---

## Frontend Architecture

### Page Structure

```
/dashboard/mis/
├── /reports              # Report builder page
├── /templates            # Saved templates
├── /schedules            # Scheduled reports
├── /history              # Execution history
└── /analytics            # Visual analytics dashboard
```

### Report Builder UI Components

#### 1. Filter Panel (Left Sidebar)
- Date range picker
- Entity filters (dropdowns)
- Status filters (checkboxes)
- Metric filters (range sliders)
- "Apply Filters" button
- "Reset" button
- "Save as Template" button

#### 2. Configuration Panel (Top Bar)
- Report type selector
- Column selector (multi-select)
- Group by selector
- Sort by selector
- Aggregation options

#### 3. Preview Panel (Center)
- Data table with results
- Pagination
- Row count indicator
- Loading state
- Empty state

#### 4. Action Panel (Right Sidebar)
- Export buttons (PDF, Excel, CSV)
- Save template
- Schedule report
- Share report
- Print preview

### Visual Analytics Dashboard

#### Charts & Graphs
- **Line Chart**: Trends over time
- **Bar Chart**: Comparisons
- **Pie Chart**: Distribution
- **Heat Map**: Performance matrix
- **Gauge Chart**: KPIs
- **Table**: Detailed data

---

## Implementation Steps

### Phase 1: Backend Foundation (Week 1)
1. Create database models
2. Create migrations
3. Implement role-based query filtering
4. Create basic API endpoints
5. Implement report generation engine

### Phase 2: Core Reporting (Week 2)
1. Implement trip reports
2. Implement driver reports
3. Implement vehicle reports
4. Add export functionality (PDF, Excel, CSV)
5. Add report template CRUD

### Phase 3: Frontend UI (Week 3)
1. Create MIS module layout
2. Build report builder interface
3. Implement filter panel
4. Implement preview panel
5. Add export functionality

### Phase 4: Advanced Features (Week 4)
1. Add station reports
2. Add customer reports
3. Add variance reports
4. Implement visual analytics
5. Add drill-down capability

### Phase 5: Scheduling & Automation (Week 5)
1. Implement report scheduling
2. Add email delivery
3. Create scheduled job runner
4. Add execution history
5. Implement report caching

### Phase 6: Testing & Optimization (Week 6)
1. Performance testing
2. Role-based access testing
3. Export format testing
4. UI/UX refinement
5. Documentation

---

## Technical Stack

### Backend
- **Django ORM**: Query building
- **Pandas**: Data manipulation
- **ReportLab**: PDF generation
- **openpyxl**: Excel generation
- **Celery**: Scheduled reports
- **Redis**: Caching

### Frontend
- **React**: UI framework
- **Ant Design**: Component library
- **Recharts**: Data visualization
- **Moment.js**: Date handling
- **FileSaver.js**: File downloads

---

## Security Considerations

1. **Data Access Control**: Strict role-based filtering
2. **SQL Injection Prevention**: Use Django ORM, no raw SQL
3. **File Access Control**: Secure file storage and access
4. **Audit Trail**: Log all report executions
5. **Rate Limiting**: Prevent report generation abuse
6. **Data Encryption**: Encrypt sensitive data in exports

---

## Performance Optimization

1. **Query Optimization**: Use select_related, prefetch_related
2. **Indexing**: Add indexes on frequently filtered columns
3. **Caching**: Cache report results for common queries
4. **Pagination**: Limit result sets
5. **Async Processing**: Use Celery for large reports
6. **Database Views**: Create materialized views for complex aggregations

---

## Success Metrics

1. **Report Generation Time**: < 5 seconds for standard reports
2. **Export Time**: < 10 seconds for Excel/PDF
3. **User Adoption**: 80% of users create at least one report per week
4. **Template Reuse**: Average 5 executions per template
5. **Scheduled Reports**: 90% success rate

---

## Future Enhancements

1. **AI-Powered Insights**: Automatic anomaly detection
2. **Natural Language Queries**: "Show me top 10 drivers this month"
3. **Mobile App**: View reports on mobile
4. **Real-time Dashboards**: Live updating metrics
5. **Custom Calculations**: User-defined formulas
6. **Report Sharing**: Share reports with external stakeholders

---

## Conclusion

This MIS Module will provide a comprehensive, flexible reporting system that empowers users to generate insights from their data while maintaining strict role-based access control. The Crystal Report-like functionality ensures users can create any combination of reports they need without developer intervention.
