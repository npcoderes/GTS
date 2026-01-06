"""
Token Queue Service for GTS Backend

Manages vehicle token queue at Mother Stations.
Handles token generation, queue matching, and automatic trip allocation.
"""
import logging
from datetime import date
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .models import VehicleToken, StockRequest, Trip, Token, Driver, Vehicle, Shift
from .services import find_active_shift
from core.models import Station

logger = logging.getLogger(__name__)


class TokenQueueError(Exception):
    """Base exception for token queue operations."""
    pass


class NoActiveShiftError(TokenQueueError):
    """Driver has no active shift at this MS."""
    pass


class DriverAlreadyHasTokenError(TokenQueueError):
    """Driver already has a waiting token."""
    pass


class TokenQueueService:
    """
    Service for managing vehicle token queue and automatic trip allocation.
    
    Flow:
    1. Driver arrives at MS → requests token (requires active shift)
    2. System generates sequential token for today
    3. If approved stock request exists for MS's DBS → auto-allocate
    4. If no request available → driver waits in queue
    5. When EIC approves stock request → auto-allocate if waiting token exists
    """
    
    def request_token(self, driver: Driver, vehicle: Vehicle, ms: Station) -> VehicleToken:
        """
        Driver requests a queue token at Mother Station.
        
        Args:
            driver: The driver requesting token
            vehicle: Vehicle being used
            ms: Mother Station where driver is waiting
            
        Returns:
            VehicleToken in WAITING status
            
        Raises:
            NoActiveShiftError: If driver has no active shift
            DriverAlreadyHasTokenError: If driver already has waiting token
        """
        with transaction.atomic():
            # 1. Validate active shift
            active_shift = find_active_shift(driver)
            if not active_shift:
                raise NoActiveShiftError(
                    f"Driver {driver.full_name} has no active shift at this time"
                )
            
            # 2. Check driver doesn't already have a waiting token
            existing_token = VehicleToken.objects.filter(
                driver=driver,
                status='WAITING'
            ).first()
            
            if existing_token:
                raise DriverAlreadyHasTokenError(
                    f"Driver already has waiting token: {existing_token.token_no}"
                )
            
            # 3. Generate sequential token number
            today = timezone.localdate()
            sequence = self._get_next_sequence(ms, today)
            token_no = f"MS{ms.id}-{today.strftime('%Y%m%d')}-{sequence:04d}"
            
            # 4. Create token
            token = VehicleToken.objects.create(
                vehicle=vehicle,
                driver=driver,
                ms=ms,
                shift=active_shift,
                token_no=token_no,
                sequence_number=sequence,
                token_date=today,
                status='WAITING'
            )
            
            logger.info(
                f"Token {token_no} issued to driver {driver.full_name} "
                f"at MS {ms.name} (sequence #{sequence})"
            )
            
            # 5. Try auto-allocation
            self._try_auto_allocate(ms)
            
            # Refresh token status (may have been allocated)
            token.refresh_from_db()
            return token
    
    def _get_next_sequence(self, ms: Station, token_date: date) -> int:
        """
        Get next sequence number for MS on given date.
        Thread-safe with select_for_update.
        """
        # Lock the table for this MS and date
        max_seq = VehicleToken.objects.filter(
            ms=ms,
            token_date=token_date
        ).select_for_update().aggregate(
            max_seq=Max('sequence_number')
        )['max_seq']
        
        return (max_seq or 0) + 1
    
    def get_waiting_tokens(self, ms_id: int):
        """Get tokens in WAITING status for an MS, ordered by sequence."""
        return VehicleToken.objects.filter(
            ms_id=ms_id,
            status='WAITING',
            token_date=timezone.localdate()
        ).select_related('driver', 'vehicle').order_by('sequence_number')
    
    def get_driver_current_token(self, driver: Driver):
        """Get driver's current WAITING or ALLOCATED token."""
        return VehicleToken.objects.filter(
            driver=driver,
            status__in=['WAITING', 'ALLOCATED'],
            token_date=timezone.localdate()
        ).select_related('vehicle', 'ms', 'trip').first()
    
    def cancel_token(self, token: VehicleToken, reason: str = 'CANCELLED_BY_DRIVER'):
        """
        Cancel a waiting token (driver left queue).
        
        Args:
            token: The token to cancel
            reason: Reason for cancellation
        """
        if token.status != 'WAITING':
            raise TokenQueueError(f"Cannot cancel token in {token.status} status")
        
        token.status = 'EXPIRED'
        token.expired_at = timezone.now()
        token.expiry_reason = reason
        token.save(update_fields=['status', 'expired_at', 'expiry_reason'])
        
        logger.info(f"Token {token.token_no} cancelled: {reason}")
    
    def expire_shift_tokens(self, shift: Shift):
        """
        Expire all waiting tokens for a shift when shift ends.
        Called by shift expiry handler if needed.
        """
        expired_count = VehicleToken.objects.filter(
            shift=shift,
            status='WAITING'
        ).update(
            status='EXPIRED',
            expired_at=timezone.now(),
            expiry_reason='SHIFT_EXPIRED'
        )
        
        if expired_count:
            logger.info(f"Expired {expired_count} tokens for shift {shift.id}")
    
    def get_approved_requests_for_ms(self, ms: Station):
        """
        Get approved stock requests waiting allocation for this MS.
        Only includes requests where DBS's parent MS matches.
        """
        return StockRequest.objects.filter(
            status='APPROVED',
            dbs__parent_station=ms,  # DBS must be under this MS
            allocated_vehicle_token__isnull=True  # Not yet allocated
        ).select_related('dbs').order_by('approved_at')
    
    def _try_auto_allocate(self, ms: Station):
        """
        Try to match first waiting token with first approved request.
        Called after token request OR stock request approval.
        
        Uses FCFS logic - first token in queue gets first approved request.
        """
        with transaction.atomic():
            # Get first waiting token
            first_token = VehicleToken.objects.filter(
                ms=ms,
                status='WAITING',
                token_date=timezone.localdate()
            ).select_for_update().order_by('sequence_number').first()
            
            if not first_token:
                logger.debug(f"No waiting tokens at MS {ms.name}")
                return None
            
            # Get first approved request for this MS's DBSs
            first_request = StockRequest.objects.filter(
                status='APPROVED',
                dbs__parent_station=ms,
                allocated_vehicle_token__isnull=True
            ).select_for_update().order_by('approved_at').first()
            
            if not first_request:
                logger.debug(f"No approved requests waiting for MS {ms.name}")
                return None
            
            # Match found! Allocate token and create trip
            trip = self._allocate_token_to_request(first_token, first_request)
            
            logger.info(
                f"Auto-allocated: Token {first_token.token_no} → "
                f"Request #{first_request.id} (DBS: {first_request.dbs.name}) → "
                f"Trip #{trip.id}"
            )
            
            return trip
    
    def _allocate_token_to_request(self, token: VehicleToken, stock_request: StockRequest) -> Trip:
        """
        Match token to stock request and create trip.
        
        Args:
            token: VehicleToken in WAITING status
            stock_request: StockRequest in APPROVED status
            
        Returns:
            Created Trip instance
        """
        now = timezone.now()
        
        # 1. Create legacy Token for trip (backward compatibility)
        legacy_token = Token.objects.create(
            vehicle=token.vehicle,
            ms=token.ms
        )
        
        # 2. Create Trip
        trip = Trip.objects.create(
            stock_request=stock_request,
            token=legacy_token,
            vehicle=token.vehicle,
            driver=token.driver,
            ms=token.ms,
            dbs=stock_request.dbs,
            status='PENDING',
            started_at=now
        )
        
        # 3. Update VehicleToken
        token.status = 'ALLOCATED'
        token.allocated_at = now
        token.trip = trip
        token.save(update_fields=['status', 'allocated_at', 'trip'])
        
        # 4. Update StockRequest
        stock_request.status = 'ASSIGNED'
        stock_request.allocated_vehicle_token = token
        stock_request.target_driver = token.driver
        stock_request.assignment_started_at = now
        stock_request.save(update_fields=[
            'status', 'allocated_vehicle_token', 'target_driver', 'assignment_started_at'
        ])
        
        # 5. Send notification to driver
        self._notify_driver_allocation(token.driver, trip, stock_request)
        
        return trip
    
    def _notify_driver_allocation(self, driver: Driver, trip: Trip, stock_request: StockRequest):
        """Notify driver about trip allocation via FCM."""
        try:
            from core.notification_service import notification_service
            
            if driver.user:
                notification_service.notify_trip_assignment(
                    driver=driver,
                    trip=trip,
                    stock_request=stock_request
                )
        except Exception as e:
            logger.error(f"Failed to send allocation notification: {e}")
    
    def trigger_allocation_on_approval(self, stock_request: StockRequest):
        """
        Called when EIC approves a stock request.
        Sets approval fields and triggers auto-allocation.
        """
        ms = stock_request.dbs.parent_station
        if not ms:
            logger.error(f"StockRequest {stock_request.id}: DBS {stock_request.dbs.name} has no parent MS")
            return
        
        logger.info(f"Triggering auto-allocation for MS {ms.name} after approval")
        return self._try_auto_allocate(ms)
    
    def get_queue_status(self, ms_id: int) -> dict:
        """
        Get queue status for EIC dashboard.
        
        Returns:
            Dict with waiting_tokens and pending_requests counts and details
        """
        today = timezone.localdate()
        
        # Get MS
        try:
            ms = Station.objects.get(id=ms_id)
        except Station.DoesNotExist:
            return {'error': 'MS not found'}
        
        waiting_tokens = VehicleToken.objects.filter(
            ms_id=ms_id,
            status='WAITING',
            token_date=today
        ).select_related('driver', 'vehicle').order_by('sequence_number')
        
        pending_requests = StockRequest.objects.filter(
            status='APPROVED',
            dbs__parent_station_id=ms_id,
            allocated_vehicle_token__isnull=True
        ).select_related('dbs').order_by('approved_at')
        
        return {
            'ms_id': ms_id,
            'ms_name': ms.name,
            'date': today.isoformat(),
            'waiting_tokens': [
                {
                    'token_no': t.token_no,
                    'sequence': t.sequence_number,
                    'driver_id': t.driver_id,
                    'driver_name': t.driver.full_name,
                    'vehicle_reg': t.vehicle.registration_no,
                    'issued_at': t.issued_at.isoformat(),
                }
                for t in waiting_tokens
            ],
            'pending_requests': [
                {
                    'id': r.id,
                    'dbs_id': r.dbs_id,
                    'dbs_name': r.dbs.name,
                    'requested_qty': str(r.requested_qty_kg) if r.requested_qty_kg else None,
                    'approved_at': r.approved_at.isoformat() if r.approved_at else None,
                    'priority': r.priority_preview,
                }
                for r in pending_requests
            ],
            'waiting_count': waiting_tokens.count(),
            'pending_count': pending_requests.count(),
        }


# Singleton instance
token_queue_service = TokenQueueService()
