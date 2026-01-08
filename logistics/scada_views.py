"""
SCADA Integration Views for GTS
Handles SCADA meter reading fetch operations for MS and DBS stations.

These are placeholder implementations that return mock data.
When the client provides actual SCADA APIs, integrate them here.
"""

from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Trip
from core.models import Station
from core.permission_views import station_has_scada
from core.error_response import (
    validation_error_response, not_found_response, forbidden_response
)


class BaseSCADAView(views.APIView):
    """Base class for SCADA fetch views with common logic."""
    permission_classes = [IsAuthenticated]
    
    def get_station_from_trip(self, trip, station_type):
        """Get the relevant station based on type."""
        if station_type == 'MS':
            return trip.ms
        elif station_type == 'DBS':
            return trip.dbs
        return None
    
    def fetch_scada_reading(self, station, reading_type):
        """
        Fetch SCADA reading from external system.
        
        This is a placeholder implementation.
        When client provides actual SCADA API:
        1. Make HTTP request to client's SCADA endpoint
        2. Parse response and extract MFM reading
        3. Return the reading value
        
        Args:
            station: Station object
            reading_type: 'prefill' or 'postfill' / 'pre_decant' or 'post_decant'
            
        Returns:
            dict with 'mfm' reading or error
        """
        # TODO: Replace with actual SCADA API integration
        # Example future implementation:
        # 
        # scada_endpoint = settings.SCADA_API_BASE_URL
        # response = requests.post(
        #     f"{scada_endpoint}/readings",
        #     json={"station_id": station.sap_station_id, "type": reading_type},
        #     headers={"Authorization": f"Bearer {settings.SCADA_API_KEY}"}
        # )
        # if response.ok:
        #     return {"mfm": response.json().get("mfm")}
        # return {"error": "Failed to fetch SCADA reading"}
        
        # Placeholder: Return None indicating SCADA not available
        return {
            "mfm": None,
            "message": "SCADA integration pending - manual entry required"
        }


class MSSCADAPrefillView(BaseSCADAView):
    """
    API Path: POST /api/ms/scada/prefill
    Fetch pre-fill SCADA reading for MS filling operation.
    
    Payload: { "tripToken": "xxx" }
    Response: { "mfm": "12345.678" }
    """
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        
        if not token_val:
            return validation_error_response('tripToken is required')
        
        try:
            trip = get_object_or_404(Trip, token__token_no=token_val)
            
            # Check if the MS station has SCADA capability
            if not trip.ms:
                return validation_error_response('Trip has no associated MS station')
            
            # if not station_has_scada(trip.ms):
            #     return Response({
            #         'success': False,
            #         'scada_available': False,
            #         'message': 'SCADA not available at this station',
            #         'mfm': None
            #     })
            
            # # Fetch SCADA reading
            # reading = self.fetch_scada_reading(trip.ms, 'prefill')
            
            return Response({
                'success': True,
                'scada_available': True,
                # 'mfm': reading.get('mfm'),
                'mfm': 200,
                # 'message': reading.get('message')
            })
            
        except Trip.DoesNotExist:
            return not_found_response('Trip not found for this token')


class MSSCADAPostfillView(BaseSCADAView):
    """
    API Path: POST /api/ms/scada/postfill
    Fetch post-fill SCADA reading for MS filling operation.
    
    Payload: { "tripToken": "xxx" }
    Response: { "mfm": "12500.321" }
    """
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        
        if not token_val:
            return validation_error_response('tripToken is required')
        
        try:
            trip = get_object_or_404(Trip, token__token_no=token_val)
            
            # Check if the MS station has SCADA capability
            # if not trip.ms:
            #     return validation_error_response('Trip has no associated MS station')
            
            # if not station_has_scada(trip.ms):
            #     return Response({
            #         'success': False,
            #         'scada_available': False,
            #         'message': 'SCADA not available at this station',
            #         'mfm': None
            #     })
            
            # Fetch SCADA reading
            # reading = self.fetch_scada_reading(trip.ms, 'postfill')
            
            return Response({
                'success': True,
                'scada_available': True,
                # 'mfm': reading.get('mfm'),
                # 'message': reading.get('message')
                'mfm': 300,
                # 'message': 'SCADA not available at this station'
            })
            
        except Trip.DoesNotExist:
            return not_found_response('Trip not found for this token')


class DBSSCADAPrefillView(BaseSCADAView):
    """
    API Path: POST /api/dbs/scada/prefill
    Fetch pre-decant SCADA reading for DBS decanting operation.
    
    Payload: { "tripToken": "xxx" }
    Response: { "mfm": "12345.678" }
    """
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        
        if not token_val:
            return validation_error_response('tripToken is required')
        
        try:
            trip = get_object_or_404(Trip, token__token_no=token_val)
            
            # Check if the DBS station has SCADA capability
            if not trip.dbs:
                return validation_error_response('Trip has no associated DBS station')
            
            # if not station_has_scada(trip.dbs):
            #     return Response({
            #         'success': False,
            #         'scada_available': False,
            #         'message': 'SCADA not available at this station',
            #         'mfm': None
            #     })
            
            # Fetch SCADA reading
            # reading = self.fetch_scada_reading(trip.dbs, 'pre_decant')
            
            return Response({
                'success': True,
                'scada_available': True,
                'mfm': 400,
                # 'message': reading.get('message')
            })
            
        except Trip.DoesNotExist:
            return not_found_response('Trip not found for this token')


class DBSSCADAPostfillView(BaseSCADAView):
    """
    API Path: POST /api/dbs/scada/postfill
    Fetch post-decant SCADA reading for DBS decanting operation.
    
    Payload: { "tripToken": "xxx" }
    Response: { "mfm": "12500.321" }
    """
    
    def post(self, request):
        token_val = request.data.get('tripToken')
        
        if not token_val:
            return validation_error_response('tripToken is required')
        
        try:
            trip = get_object_or_404(Trip, token__token_no=token_val)
            
            # Check if the DBS station has SCADA capability
            if not trip.dbs:
                return validation_error_response('Trip has no associated DBS station')
            
            # if not station_has_scada(trip.dbs):
            #     return Response({
            #         'success': False,
            #         'scada_available': False,
            #         'message': 'SCADA not available at this station',
            #         'mfm': None
            #     })
            
            # Fetch SCADA reading
            # reading = self.fetch_scada_reading(trip.dbs, 'post_decant')
            
            return Response({
                'success': True,
                'scada_available': True,
                # 'mfm': reading.get('mfm'),
                'mfm': 500,
                # 'message': reading.get('message')
            })
            
        except Trip.DoesNotExist:
            return not_found_response('Trip not found for this token')
