"""
SAP Integration Service for GTS Backend
Handles synchronization of user data with SAP system.
"""
import requests
import logging
from datetime import datetime
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class SAPIntegrationService:
    """
    Service for integrating with SAP REST API.
    Supports user data synchronization (CREATE and DISP operations).
    
    Configuration (in settings.py):
    - SAP_ENABLED: Enable/disable SAP integration
    - SAP_BASE_URL: Base URL for SAP REST adapter
    - SAP_USER_ENDPOINT: Endpoint for user operations (default: 'GTS1/')
    - SAP_TIMEOUT: Request timeout in seconds
    - SAP_RETRY_COUNT: Number of retry attempts
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self.enabled = getattr(settings, 'SAP_ENABLED', False)
            self.base_url = getattr(settings, 'SAP_BASE_URL', 'http://10.1.70.249:50000/RESTAdapter/')
            self.user_endpoint = getattr(settings, 'SAP_USER_ENDPOINT', 'GTS1/')
            self.station_endpoint = getattr(settings, 'SAP_STATION_ENDPOINT', 'GTS3/')
            self.trip_endpoint = getattr(settings, 'SAP_TRIP_ENDPOINT', 'GTS11/')
            self.timeout = getattr(settings, 'SAP_TIMEOUT', 30)
            self.retry_count = getattr(settings, 'SAP_RETRY_COUNT', 3)
            self.username = getattr(settings, 'SAP_USERNAME', '')
            self.password = getattr(settings, 'SAP_PASSWORD', '')
            self._initialized = True
            
            if self.enabled:
                logger.info(f"SAP Integration Service initialized. User: {self.get_user_url()}, Station: {self.get_station_url()}")
            else:
                logger.info("SAP Integration Service initialized in DISABLED mode")
    
    def get_user_url(self):
        """Get full URL for user operations."""
        return f"{self.base_url.rstrip('/')}/{self.user_endpoint.strip('/')}/"
    
    def get_station_url(self):
        """Get full URL for station operations."""
        return f"{self.base_url.rstrip('/')}/{self.station_endpoint.strip('/')}/"

    def get_trip_url(self):
        """Get full URL for trip operations."""
        return f"{self.base_url.rstrip('/')}/{self.trip_endpoint.strip('/')}/"
    
    def _format_date(self, date_value):
        """
        Format date to SAP format (DD.MM.YYYY).
        
        Args:
            date_value: datetime, date object, or None
            
        Returns:
            String in DD.MM.YYYY format, or '31.12.9999' if None
        """
        if date_value is None:
            return "31.12.9999"
        
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        
        return date_value.strftime("%d.%m.%Y")
    
    def _get_primary_user_role(self, user):
        """
        Get the primary active UserRole for a user.
        Returns the most recently created active role.
        
        Args:
            user: User model instance
            
        Returns:
            UserRole instance or None
        """
        from core.models import UserRole
        
        return UserRole.objects.filter(
            user=user,
            active=True
        ).select_related('role', 'station').order_by('-created_at').first()
    
    def _build_user_payload(self, user, operation='CREATE'):
        """
        Build SAP payload for user synchronization.
        
        Args:
            user: User model instance
            operation: 'CREATE' or 'DISP'
            
        Returns:
            Dictionary with SAP payload
        """
        payload = {
            "INPUT1": user.full_name or user.email.split('@')[0],  # Username
            "INPUT10": operation,  # Operation type
        }
        
        if operation == 'DISP':
            # For DISP, only username and operation are needed
            return payload
        
        # For CREATE/MODIFY, add all user details
        user_role = self._get_primary_user_role(user)
        
        # Get station SAP ID if available (use sap_station_id if exists, fallback to code)
        station_code = ""
        role_code = ""
        if user_role:
            if user_role.station:
                # Use SAP station ID if available, otherwise use code
                station_code = user_role.station.sap_station_id or user_role.station.code
            if user_role.role:
                role_code = user_role.role.code
        
        payload.update({
            "INPUT2": user.email,
            "INPUT3": station_code,
            "INPUT4": role_code,
            "INPUT5": "1" if user.is_active else "0",
            "INPUT6": self._format_date(user.role_in),
            "INPUT7": self._format_date(user.role_out),
            "INPUT8": "",
            "INPUT9": "",
        })
        
        return payload
    
    def sync_user_to_sap(self, user, operation='CREATE'):
        """
        Synchronize user data to SAP.
        
        Args:
            user: User model instance
            operation: 'CREATE' for create/update operations
            
        Returns:
            dict: {
                'success': bool,
                'response': dict or None,
                'error': str or None
            }
        """
        if not self.enabled:
            logger.info(f"SAP sync skipped (disabled) for user: {user.email}")
            return {'success': True, 'response': None, 'error': 'SAP integration disabled'}
        
        try:
            payload = self._build_user_payload(user, operation)
            url = self.get_user_url()
            
            logger.info(f"Syncing user {user.email} to SAP. Operation: {operation}")
            logger.debug(f"SAP Payload: {payload}")
            
            # Make request with retries
            last_error = None
            for attempt in range(1, self.retry_count + 1):
                try:
                    # Prepare auth
                    auth = None
                    if self.username and self.password:
                        from requests.auth import HTTPBasicAuth
                        auth = HTTPBasicAuth(self.username, self.password)
                    
                    response = requests.post(
                        url,
                        json=payload,
                        timeout=self.timeout,
                        headers={'Content-Type': 'application/json'},
                        auth=auth
                    )
                    
                    response.raise_for_status()
                    
                    result_data = response.json()
                    logger.info(f"SAP sync successful for user {user.email}")
                    logger.debug(f"SAP Response: {result_data}")
                    
                    return {
                        'success': True,
                        'response': result_data,
                        'error': None
                    }
                    
                except requests.exceptions.Timeout as e:
                    last_error = f"Timeout on attempt {attempt}/{self.retry_count}"
                    logger.warning(f"SAP request timeout for user {user.email} (attempt {attempt}/{self.retry_count})")
                    
                except requests.exceptions.RequestException as e:
                    last_error = str(e)
                    logger.warning(f"SAP request failed for user {user.email} (attempt {attempt}/{self.retry_count}): {e}")
                    
                    # Don't retry on 4xx errors (client errors)
                    if hasattr(e, 'response') and e.response is not None:
                        if 400 <= e.response.status_code < 500:
                            break
            
            # All retries failed
            error_msg = f"SAP sync failed after {self.retry_count} attempts: {last_error}"
            logger.error(f"SAP sync failed for user {user.email}: {error_msg}")
            
            return {
                'success': False,
                'response': None,
                'error': error_msg
            }
            
        except Exception as e:
            error_msg = f"Unexpected error during SAP sync: {str(e)}"
            logger.error(f"SAP sync error for user {user.email}: {error_msg}", exc_info=True)
            
            return {
                'success': False,
                'response': None,
                'error': error_msg
            }
    
    def get_user_from_sap(self, username):
        """
        Retrieve user data from SAP using DISP operation.
        
        Args:
            username: Username to retrieve
            
        Returns:
            dict: {
                'success': bool,
                'data': dict or None,
                'error': str or None
            }
        """
        if not self.enabled:
            logger.info(f"SAP DISP skipped (disabled) for user: {username}")
            return {'success': True, 'data': None, 'error': 'SAP integration disabled'}
        
        try:
            payload = {
                "INPUT1": username,
                "INPUT10": "DISP",
                "INPUT2": "",
                "INPUT3": "",
                "INPUT4": "",
                "INPUT5": "",
                "INPUT6": "",
                "INPUT7": "",
                "INPUT8": "",
                "INPUT9": "",
            }
            
            url = self.get_user_url()
            logger.info(f"Retrieving user {username} from SAP (DISP)")
            
            # Prepare auth
            auth = None
            if self.username and self.password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(self.username, self.password)
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'},
                auth=auth
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            logger.info(f"SAP DISP successful for user {username}")
            logger.debug(f"SAP Response: {result_data}")
            
            return {
                'success': True,
                'data': result_data,
                'error': None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"SAP DISP failed: {str(e)}"
            logger.error(f"SAP DISP error for user {username}: {error_msg}")
            
            return {
                'success': False,
                'data': None,
                'error': error_msg
            }
    
    def _format_datetime_sap(self, dt):
        """
        Format datetime to SAP trip format: YYYYMMDD|HHMMSS
        """
        if not dt:
            return ""
        if isinstance(dt, str):
            # If it's already a string, try to parse it, or return empty if unknown format
            # But normally we expect datetime objects from Django models
            return ""
        
        # Convert to local time if it's aware, or assume local?
        # SAP usually expects local time.
        dt = timezone.localtime(dt)
        return dt.strftime("%Y%m%d|%H%M%S")

    def sync_trip_to_sap(self, trip):
        """
        Synchronize completed trip data to SAP (GTS11).
        
        Args:
            trip: Trip model instance (should be completed with filings/decantings)
            
        Returns:
            dict: Success/Failure response
        """
        if not self.enabled:
            logger.info(f"SAP trip sync skipped (disabled) for trip: {trip.id}")
            return {'success': True, 'response': None, 'error': 'SAP integration disabled'}

        try:
            # Gather related data
            ms_filling = trip.ms_fillings.first()
            dbs_decanting = trip.dbs_decantings.first()
            
            # Map Fields
            ms_id = ""
            if trip.ms:
                ms_id = trip.ms.sap_station_id or trip.ms.code
            
            dbs_id = ""
            if trip.dbs:
                dbs_id = trip.dbs.sap_station_id or trip.dbs.code
            
            route_id = trip.route.code if trip.route else "" # Assuming route has code or name
            
            # Quantities
            ms_fill_qty = float(ms_filling.filled_qty_kg) if ms_filling and ms_filling.filled_qty_kg else 0
            dbs_del_qty = float(dbs_decanting.delivered_qty_kg) if dbs_decanting and dbs_decanting.delivered_qty_kg else 0
            diff = ms_fill_qty - dbs_del_qty
            variance = 0
            if ms_fill_qty > 0:
                variance = (diff / ms_fill_qty) * 100
                
            payload = {
                "TRIPID": str(trip.id),
                "VH_NO": trip.vehicle.registration_no if trip.vehicle else "",
                "MS_ID": ms_id,
                "DBS_ID": dbs_id,
                "ROUTE_ID": route_id,
                "RTKM": str(trip.rtkm_km) if trip.rtkm_km else "0",
                
                # MS Times & Readings
                "MS_ST_TM": self._format_datetime_sap(ms_filling.start_time) if ms_filling else "",
                "MS_ED_TM": self._format_datetime_sap(ms_filling.end_time) if ms_filling else "",
                "MS_OPEN": str(ms_filling.prefill_mfm) if ms_filling and ms_filling.prefill_mfm else "",
                "MS_CLOSE": str(ms_filling.postfill_mfm) if ms_filling and ms_filling.postfill_mfm else "",
                
                # DBS Times & Readings
                "DBS_ST_TM": self._format_datetime_sap(dbs_decanting.start_time) if dbs_decanting else "",
                "DBS_END_TM": self._format_datetime_sap(dbs_decanting.end_time) if dbs_decanting else "",
                # Assuming DBS readings correspond to Open/Close. 
                # Note: Logic usually maps Pre -> Open, Post -> Close
                "DBS_OPEN": str(dbs_decanting.pre_dec_reading) if dbs_decanting and dbs_decanting.pre_dec_reading else "",
                "DBS_CLOSE": str(dbs_decanting.post_dec_reading) if dbs_decanting and dbs_decanting.post_dec_reading else "",
                
                # Quantities
                "MS_FILL_QTY": str(ms_fill_qty),
                "DBS_DEL_QTY": str(dbs_del_qty),
                "DIFF": f"{diff:.2f}",
                "VARIANCE": f"{variance:.2f}",
                
                "STATUS": "COMPLETED",
                
                # Trip Times
                "TR_ST_TM": self._format_datetime_sap(trip.started_at),
                "TR_ED_TM": self._format_datetime_sap(trip.completed_at or timezone.now())
            }
            
            url = self.get_trip_url()
            logger.info(f"Syncing trip {trip.id} to SAP")
            logger.debug(f"SAP Trip Payload: {payload}")
            
            # Auth
            auth = None
            if self.username and self.password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(self.username, self.password)
                
            # Request
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'},
                auth=auth
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            logger.info(f"SAP trip sync successful for trip {trip.id}")
            return {'success': True, 'response': result_data, 'error': None}
            
        except Exception as e:
            error_msg = f"SAP trip sync failed: {str(e)}"
            logger.error(f"SAP trip sync error for trip {trip.id}: {error_msg}", exc_info=True)
            return {'success': False, 'response': None, 'error': error_msg}
        
        except Exception as e:
            error_msg = f"Unexpected error during SAP DISP: {str(e)}"
            logger.error(f"SAP DISP error for user {username}: {error_msg}", exc_info=True)
            
            return {
                'success': False,
                'data': None,
                'error': error_msg
            }
    
    def get_stations_from_sap(self, station_id=None, station_type=None):
        """
        Retrieve station data from SAP using GTS3 endpoint.
        
        Logic:
        - If station_type = 'DB':
            - If station_id provided: Get specific DB station
            - Else: Get all DB stations
        - Else (station_type = 'MS' or None):
            - If station_id provided: Get specific MS with its DBs
            - Else: Get all MS and their respective DB data
        
        Args:
            station_id: Station ID (optional) - INPUT1
            station_type: 'MS' or 'DB' (optional) - INPUT10
            
        Returns:
            dict: {
                'success': bool,
                'stations': list of dicts or None,
                'error': str or None
            }
        """
        if not self.enabled:
            logger.info(f"SAP station retrieval skipped (disabled)")
            return {'success': True, 'stations': [], 'error': 'SAP integration disabled'}
        
        try:
            # Build payload
            payload = {
                "INPUT1": str(station_id) if station_id else "",
                "INPUT2": "",  # Station name (not used for filter)
                "INPUT3": "",
                "INPUT4": "",
                "INPUT5": "",
                "INPUT6": "",
                "INPUT7": "",
                "INPUT8": "",
                "INPUT9": "",
                "INPUT10": station_type if station_type else "",
            }
            
            url = self.get_station_url()
            logger.info(f"Retrieving stations from SAP. Type: {station_type or 'ALL'}, ID: {station_id or 'ALL'}")
            logger.debug(f"SAP Station Payload: {payload}")
            
            # Prepare auth
            auth = None
            if self.username and self.password:
                from requests.auth import HTTPBasicAuth
                auth = HTTPBasicAuth(self.username, self.password)
            
            response = requests.post(
                url,
                json=payload,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'},
                auth=auth
            )
            
            response.raise_for_status()
            result_data = response.json()
            
            logger.info(f"SAP station retrieval successful")
            logger.debug(f"SAP Response: {result_data}")
            
            # Parse response
            stations = []
            try:
                items = result_data.get('ZSD_GTS3.Response', {}).get('IT_DATA', {}).get('item', [])
                
                # Handle single item response (not in array)
                if isinstance(items, dict):
                    items = [items]
                
                for item in items:
                    station_data = {
                        'id': str(item.get('INPUT1', '')),
                        'code': str(item.get('INPUT1', '')),
                        'name': item.get('INPUT2', ''),
                        'city': item.get('INPUT4', ''),
                        'phone': item.get('INPUT5', ''),
                        'type': item.get('INPUT6', ''),  # 'MS' or 'DB'
                        'parent_ms_id': str(item.get('INPUT7', '')) if item.get('INPUT7') else None,
                        'raw_data': item
                    }
                    stations.append(station_data)
                
                logger.info(f"Parsed {len(stations)} station(s) from SAP")
                
            except Exception as parse_error:
                logger.warning(f"Error parsing SAP station response: {parse_error}")
                # Return raw response if parsing fails
                return {
                    'success': True,
                    'stations': [],
                    'raw_response': result_data,
                    'error': f'Parsing error: {str(parse_error)}'
                }
            
            return {
                'success': True,
                'stations': stations,
                'error': None
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"SAP station retrieval failed: {str(e)}"
            logger.error(f"SAP station error: {error_msg}")
            
            return {
                'success': False,
                'stations': None,
                'error': error_msg
            }
        
        except Exception as e:
            error_msg = f"Unexpected error during SAP station retrieval: {str(e)}"
            logger.error(f"SAP station error: {error_msg}", exc_info=True)
            
            return {
                'success': False,
                'stations': None,
                'error': error_msg
            }


# Singleton instance
sap_service = SAPIntegrationService()
