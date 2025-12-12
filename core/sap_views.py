"""
API views for SAP station operations
"""
import logging
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.sap_integration import sap_service

logger = logging.getLogger(__name__)


class SAPStationView(views.APIView):
    """
    API endpoint for retrieving stations from SAP.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Retrieve stations from SAP.
        
        GET /api/sap/stations/
        GET /api/sap/stations/?station_id=1000000524
        GET /api/sap/stations/?station_type=DB
        GET /api/sap/stations/?station_id=1000000401&station_type=MS
        
        Query Parameters:
        - station_id: Filter by specific station ID (optional)
        - station_type: Filter by type 'MS' or 'DB' (optional)
        
        Logic:
        - If station_type = 'DB':
            - If station_id provided: Get specific DB station
            - Else: Get all DB stations
        - Else (station_type = 'MS' or None):
            - If station_id provided: Get specific MS with its DBs
            - Else: Get all MS and their respective DB data
        """
        station_id = request.query_params.get('station_id')
        station_type = request.query_params.get('station_type')
        
        # Validate station_type
        if station_type and station_type not in ['MS', 'DB']:
            return Response({
                'error': 'Invalid station_type. Must be "MS" or "DB"'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            sap_result = sap_service.get_stations_from_sap(
                station_id=station_id,
                station_type=station_type
            )
            
            if sap_result['success']:
                return Response({
                    'message': 'Stations retrieved from SAP successfully',
                    'count': len(sap_result.get('stations', [])),
                    'stations': sap_result.get('stations', [])
                })
            else:
                return Response({
                    'message': 'Failed to retrieve stations from SAP',
                    'error': sap_result.get('error')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"SAP station retrieval error: {str(e)}", exc_info=True)
            return Response({
                'message': 'Unexpected error during SAP retrieval',
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
