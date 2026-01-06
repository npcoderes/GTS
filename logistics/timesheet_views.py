"""
Timesheet Views for GTS
Handles weekly calendar view, shift assignment, and bulk operations.
"""

from rest_framework import views, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import re

from .models import Driver, Vehicle, Shift, ShiftTemplate
from .serializers import ShiftTemplateSerializer
from core.models import User


def check_transport_permission(user):
    """Check if user has transport vendor/admin permissions."""
    role_codes = list(user.user_roles.filter(active=True).values_list('role__code', flat=True))
    allowed_roles = ['SUPER_ADMIN', 'EIC', 'TRANSPORT_ADMIN', 'SGL_TRANSPORT_VENDOR', 'VENDOR']
    return any(role in allowed_roles for role in role_codes)


def check_eic_permission(user):
    """Check if user has EIC/SuperAdmin permissions."""
    role_codes = list(user.user_roles.filter(active=True).values_list('role__code', flat=True))
    return 'SUPER_ADMIN' in role_codes or 'EIC' in role_codes


class TimesheetView(views.APIView):
    """
    GET /api/timesheet/
    Returns weekly calendar data with drivers and their shifts.
    
    Query params:
    - start_date: YYYY-MM-DD (defaults to start of current week)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        # Parse start_date or default to current week start
        start_date_str = request.query_params.get('start_date')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = timezone.now().date() - timedelta(days=timezone.now().weekday())
        else:
            start_date = timezone.now().date() - timedelta(days=timezone.now().weekday())
        
        end_date = start_date + timedelta(days=6)
        
        # Get drivers based on role
        role_codes = list(request.user.user_roles.filter(active=True).values_list('role__code', flat=True))
        
        if 'SUPER_ADMIN' in role_codes or 'EIC' in role_codes:
            drivers = Driver.objects.all().select_related('assigned_vehicle')
        elif 'SGL_TRANSPORT_VENDOR' in role_codes or 'VENDOR' in role_codes:
            # Vendor sees only their drivers
            drivers = Driver.objects.filter(vendor=request.user).select_related('assigned_vehicle')
        else:
            drivers = Driver.objects.all().select_related('assigned_vehicle')
        
        # Get shifts for the week
        shifts = Shift.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date,
            driver__in=drivers
        ).select_related('driver', 'vehicle', 'shift_template', 'created_by')
        
        # Build shifts lookup: {driver_id: {date_str: shift_data}}
        shifts_by_driver = {}
        for shift in shifts:
            driver_id = shift.driver_id
            shift_date = shift.start_time.date().isoformat()
            
            if driver_id not in shifts_by_driver:
                shifts_by_driver[driver_id] = {}
            
            shifts_by_driver[driver_id][shift_date] = {
                'id': shift.id,
                'start_time': shift.start_time.isoformat(),
                'end_time': shift.end_time.isoformat(),
                'status': shift.status,
                'shift_template': shift.shift_template_id,
                'template_name': shift.shift_template.name if shift.shift_template else None,
                'vehicle': shift.vehicle_id,
                'notes': shift.notes or '',
                'created_by': shift.created_by.full_name if shift.created_by else 'System',
            }
        
        # Build driver list
        driver_list = []
        for driver in drivers:
            dates_dict = {}
            for i in range(7):
                date_str = (start_date + timedelta(days=i)).isoformat()
                dates_dict[date_str] = shifts_by_driver.get(driver.id, {}).get(date_str, None)
            
            driver_list.append({
                'id': driver.id,
                'name': driver.full_name,
                'vehicle': driver.assigned_vehicle.registration_no if driver.assigned_vehicle else None,
                'vehicle_id': driver.assigned_vehicle_id,
                'shifts': dates_dict,
            })
        
        # Get active templates
        templates = ShiftTemplate.objects.filter(is_active=True).order_by('start_time')
        template_list = [
            {
                'id': t.id,
                'name': t.name,
                'code': t.code,
                'start_time': t.start_time.strftime('%H:%M:%S'),
                'end_time': t.end_time.strftime('%H:%M:%S'),
                'color': t.color,
            }
            for t in templates
        ]
        
        # Generate dates list
        dates = [(start_date + timedelta(days=i)).isoformat() for i in range(7)]
        
        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'dates': dates,
            'drivers': driver_list,
            'templates': template_list,
        })


class TimesheetAssignView(views.APIView):
    """
    POST /api/timesheet/assign/
    Create a new shift assignment.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        driver_id = request.data.get('driver_id')
        vehicle_id = request.data.get('vehicle_id')
        date_str = request.data.get('date')  # YYYY-MM-DD
        template_id = request.data.get('template_id')
        start_time_str = request.data.get('start_time')  # HH:MM
        end_time_str = request.data.get('end_time')  # HH:MM
        notes = request.data.get('notes', '')
        
        if not driver_id or not date_str:
            return Response({'error': 'driver_id and date are required'}, status=400)
        
        try:
            driver = Driver.objects.get(id=driver_id)
        except Driver.DoesNotExist:
            return Response({'error': 'Driver not found'}, status=404)
        
        # Determine vehicle
        if vehicle_id:
            try:
                vehicle = Vehicle.objects.get(id=vehicle_id)
            except Vehicle.DoesNotExist:
                return Response({'error': 'Vehicle not found'}, status=404)
        elif driver.assigned_vehicle:
            vehicle = driver.assigned_vehicle
        else:
            return Response({'error': 'No vehicle assigned to driver'}, status=400)
        
        # Parse date
        try:
            shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
        
        # Determine times from template or custom
        template = None
        if template_id:
            try:
                template = ShiftTemplate.objects.get(id=template_id, is_active=True)
                start_time = datetime.combine(shift_date, template.start_time)
                end_time = datetime.combine(shift_date, template.end_time)
                # Handle overnight shifts
                if template.end_time < template.start_time:
                    end_time += timedelta(days=1)
            except ShiftTemplate.DoesNotExist:
                return Response({'error': 'Template not found'}, status=404)
        elif start_time_str and end_time_str:
            try:
                start_time = datetime.combine(shift_date, datetime.strptime(start_time_str, '%H:%M').time())
                end_time = datetime.combine(shift_date, datetime.strptime(end_time_str, '%H:%M').time())
                if end_time <= start_time:
                    end_time += timedelta(days=1)
            except ValueError:
                return Response({'error': 'Invalid time format'}, status=400)
        else:
            return Response({'error': 'template_id or start_time/end_time required'}, status=400)
        
        # Make aware
        start_time = timezone.make_aware(start_time)
        end_time = timezone.make_aware(end_time)
        
        # Check for existing shift on this date
        existing = Shift.objects.filter(
            driver=driver,
            start_time__date=shift_date
        ).first()
        
        if existing:
            return Response({
                'error': 'Shift already exists for this driver on this date',
                'existing_shift_id': existing.id
            }, status=409)
        
        # Create shift
        shift = Shift.objects.create(
            driver=driver,
            vehicle=vehicle,
            start_time=start_time,
            end_time=end_time,
            status='PENDING',
            shift_template=template,
            notes=notes,
            created_by=request.user,
        )
        
        return Response({
            'message': 'Shift created successfully',
            'shift_id': shift.id,
            'status': 'PENDING'
        }, status=201)


class TimesheetUpdateView(views.APIView):
    """
    PUT /api/timesheet/update/
    Update an existing shift.
    """
    permission_classes = [IsAuthenticated]
    
    def put(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        shift_id = request.data.get('shift_id')
        if not shift_id:
            return Response({'error': 'shift_id is required'}, status=400)
        
        try:
            shift = Shift.objects.get(id=shift_id)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found'}, status=404)
        
        # Only allow editing PENDING shifts (unless EIC/SuperAdmin)
        if shift.status != 'PENDING' and not check_eic_permission(request.user):
            return Response({'error': 'Only PENDING shifts can be edited'}, status=400)
        
        # Update fields if provided
        vehicle_id = request.data.get('vehicle_id')
        template_id = request.data.get('template_id')
        start_time_str = request.data.get('start_time')
        end_time_str = request.data.get('end_time')
        notes = request.data.get('notes')
        
        if vehicle_id:
            try:
                shift.vehicle = Vehicle.objects.get(id=vehicle_id)
            except Vehicle.DoesNotExist:
                return Response({'error': 'Vehicle not found'}, status=404)
        
        shift_date = shift.start_time.date()
        
        if template_id:
            try:
                template = ShiftTemplate.objects.get(id=template_id, is_active=True)
                shift.shift_template = template
                shift.start_time = timezone.make_aware(datetime.combine(shift_date, template.start_time))
                shift.end_time = timezone.make_aware(datetime.combine(shift_date, template.end_time))
                if template.end_time < template.start_time:
                    shift.end_time += timedelta(days=1)
            except ShiftTemplate.DoesNotExist:
                return Response({'error': 'Template not found'}, status=404)
        elif start_time_str and end_time_str:
            try:
                shift.start_time = timezone.make_aware(
                    datetime.combine(shift_date, datetime.strptime(start_time_str, '%H:%M').time())
                )
                shift.end_time = timezone.make_aware(
                    datetime.combine(shift_date, datetime.strptime(end_time_str, '%H:%M').time())
                )
                if shift.end_time <= shift.start_time:
                    shift.end_time += timedelta(days=1)
                shift.shift_template = None
            except ValueError:
                return Response({'error': 'Invalid time format'}, status=400)
        
        if notes is not None:
            shift.notes = notes
        
        shift.save()
        
        return Response({'message': 'Shift updated successfully'})


class TimesheetDeleteView(views.APIView):
    """
    POST /api/timesheet/delete/
    Delete a shift.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        shift_id = request.data.get('shift_id')
        if not shift_id:
            return Response({'error': 'shift_id is required'}, status=400)
        
        try:
            shift = Shift.objects.get(id=shift_id)
        except Shift.DoesNotExist:
            return Response({'error': 'Shift not found'}, status=404)
        
        # Only allow deleting PENDING shifts (unless EIC/SuperAdmin)
        if shift.status != 'PENDING' and not check_eic_permission(request.user):
            return Response({'error': 'Only PENDING shifts can be deleted'}, status=400)
        
        shift.delete()
        
        return Response({'message': 'Shift deleted successfully'})


class TimesheetCopyWeekView(views.APIView):
    """
    POST /api/timesheet/copy-week/
    Copy all shifts from source week to target week.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        # Support both old and new param names for compatibility
        source_start = request.data.get('source_start_date') or request.data.get('source_start')  # YYYY-MM-DD
        target_start = request.data.get('target_start_date') or request.data.get('target_start')  # YYYY-MM-DD
        
        if not source_start or not target_start:
            return Response({'error': 'source_start_date and target_start_date required'}, status=400)
        
        try:
            source_date = datetime.strptime(source_start, '%Y-%m-%d').date()
            target_date = datetime.strptime(target_start, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
        
        source_end = source_date + timedelta(days=6)
        day_diff = (target_date - source_date).days
        
        # Get source shifts
        source_shifts = Shift.objects.filter(
            start_time__date__gte=source_date,
            start_time__date__lte=source_end
        ).select_related('driver', 'vehicle', 'shift_template')
        
        created_count = 0
        skipped_count = 0
        
        for shift in source_shifts:
            new_start = shift.start_time + timedelta(days=day_diff)
            new_end = shift.end_time + timedelta(days=day_diff)
            
            # Check if shift already exists
            existing = Shift.objects.filter(
                driver=shift.driver,
                start_time__date=new_start.date()
            ).exists()
            
            if existing:
                skipped_count += 1
                continue
            
            Shift.objects.create(
                driver=shift.driver,
                vehicle=shift.vehicle,
                start_time=new_start,
                end_time=new_end,
                status='PENDING',
                shift_template=shift.shift_template,
                notes=shift.notes,
                created_by=request.user,
            )
            created_count += 1
        
        return Response({
            'message': f'Copied {created_count} shifts, skipped {skipped_count} (already exist)',
            'created': created_count,
            'skipped': skipped_count
        })


class TimesheetFillWeekView(views.APIView):
    """
    POST /api/timesheet/fill-week/
    Fill entire week with a template for selected drivers.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        driver_ids = request.data.get('driver_ids', [])
        template_id = request.data.get('template_id')
        # Support both old and new param names
        week_start = request.data.get('start_date') or request.data.get('week_start')  # YYYY-MM-DD
        skip_existing = request.data.get('skip_existing', True)
        
        if not driver_ids or not template_id or not week_start:
            return Response({'error': 'driver_ids, template_id, and start_date required'}, status=400)
        
        try:
            template = ShiftTemplate.objects.get(id=template_id, is_active=True)
            start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        except ShiftTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=404)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
        
        drivers = Driver.objects.filter(id__in=driver_ids).select_related('assigned_vehicle')
        
        created_count = 0
        skipped_count = 0
        
        for driver in drivers:
            vehicle = driver.assigned_vehicle
            if not vehicle:
                skipped_count += 7
                continue
            
            for i in range(7):
                shift_date = start_date + timedelta(days=i)
                
                # Check existing and skip if skip_existing is True
                existing = Shift.objects.filter(
                    driver=driver,
                    start_time__date=shift_date
                ).exists()
                
                if existing and skip_existing:
                    skipped_count += 1
                    continue
                
                start_time = timezone.make_aware(datetime.combine(shift_date, template.start_time))
                end_time = timezone.make_aware(datetime.combine(shift_date, template.end_time))
                if template.end_time < template.start_time:
                    end_time += timedelta(days=1)
                
                Shift.objects.create(
                    driver=driver,
                    vehicle=vehicle,
                    start_time=start_time,
                    end_time=end_time,
                    status='PENDING',
                    shift_template=template,
                    created_by=request.user,
                )
                created_count += 1
        
        return Response({
            'message': f'Created {created_count} shifts, skipped {skipped_count}',
            'created': created_count,
            'skipped': skipped_count
        })


class TimesheetFillMonthView(views.APIView):
    """
    POST /api/timesheet/fill-month/
    Fill entire month with a template for selected drivers.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        driver_ids = request.data.get('driver_ids', [])
        template_id = request.data.get('template_id')
        # Support year/month params OR month_start date string
        year = request.data.get('year')
        month = request.data.get('month')
        month_start = request.data.get('month_start')  # YYYY-MM-DD (first day of month)
        include_weekends = request.data.get('include_weekends', True)
        skip_existing = request.data.get('skip_existing', True)
        
        # Build month_start from year/month if provided
        if year and month and not month_start:
            month_start = f"{year}-{str(month).zfill(2)}-01"
        
        if not driver_ids or not template_id or not month_start:
            return Response({'error': 'driver_ids, template_id, and year/month required'}, status=400)
        
        try:
            template = ShiftTemplate.objects.get(id=template_id, is_active=True)
            start_date = datetime.strptime(month_start, '%Y-%m-%d').date()
        except ShiftTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=404)
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
        
        # Calculate end of month
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - timedelta(days=1)
        
        days_in_month = (end_date - start_date).days + 1
        
        drivers = Driver.objects.filter(id__in=driver_ids).select_related('assigned_vehicle')
        
        created_count = 0
        skipped_count = 0
        
        for driver in drivers:
            vehicle = driver.assigned_vehicle
            if not vehicle:
                skipped_count += days_in_month
                continue
            
            for i in range(days_in_month):
                shift_date = start_date + timedelta(days=i)
                
                # Skip weekends if include_weekends is False
                if not include_weekends and shift_date.weekday() >= 5:  # 5=Sat, 6=Sun
                    skipped_count += 1
                    continue
                
                # Skip if existing shift found and skip_existing is True
                existing = Shift.objects.filter(
                    driver=driver,
                    start_time__date=shift_date
                ).exists()
                
                if existing and skip_existing:
                    skipped_count += 1
                    continue
                
                start_time = timezone.make_aware(datetime.combine(shift_date, template.start_time))
                end_time = timezone.make_aware(datetime.combine(shift_date, template.end_time))
                if template.end_time < template.start_time:
                    end_time += timedelta(days=1)
                
                Shift.objects.create(
                    driver=driver,
                    vehicle=vehicle,
                    start_time=start_time,
                    end_time=end_time,
                    status='PENDING',
                    shift_template=template,
                    created_by=request.user,
                )
                created_count += 1
        
        return Response({
            'message': f'Created {created_count} shifts for month, skipped {skipped_count}',
            'created': created_count,
            'skipped': skipped_count
        })


class TimesheetClearWeekView(views.APIView):
    """
    POST /api/timesheet/clear-week/
    Clear all shifts from a week.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not check_transport_permission(request.user):
            return Response({'error': 'Permission denied'}, status=403)
        
        # Support both old and new param names
        week_start = request.data.get('start_date') or request.data.get('week_start')  # YYYY-MM-DD
        pending_only = request.data.get('only_pending') or request.data.get('pending_only', False)
        
        if not week_start:
            return Response({'error': 'start_date required'}, status=400)
        
        try:
            start_date = datetime.strptime(week_start, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Invalid date format'}, status=400)
        
        end_date = start_date + timedelta(days=6)
        
        queryset = Shift.objects.filter(
            start_time__date__gte=start_date,
            start_time__date__lte=end_date
        )
        
        if pending_only:
            queryset = queryset.filter(status='PENDING')
        elif not check_eic_permission(request.user):
            # Non-EIC can only delete PENDING shifts
            queryset = queryset.filter(status='PENDING')
        
        count = queryset.count()
        queryset.delete()
        
        return Response({
            'message': f'Deleted {count} shifts',
            'deleted': count
        })


class ShiftTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ShiftTemplate CRUD operations.
    """
    queryset = ShiftTemplate.objects.filter(is_active=True).order_by('start_time')
    serializer_class = ShiftTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        # Auto-generate code from name if not provided
        name = serializer.validated_data.get('name', '')
        code = serializer.validated_data.get('code', '')
        
        if not code:
            code = re.sub(r'[^A-Za-z0-9]+', '_', name.upper()).strip('_')
            # Ensure unique
            base_code = code
            counter = 1
            while ShiftTemplate.objects.filter(code=code).exists():
                code = f"{base_code}_{counter}"
                counter += 1
            serializer.validated_data['code'] = code
        
        serializer.save(created_by=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_active = False
        instance.save()
