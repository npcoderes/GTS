"""
API views for SAP sync operations
"""
import logging
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.management import call_command
from django.utils import timezone
from io import StringIO
import sys

logger = logging.getLogger(__name__)


class SAPStationSyncView(views.APIView):
    """
    API endpoint for syncing stations from SAP
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Sync stations from SAP to local database
        
        POST /api/sap/sync-stations/
        Query Parameters:
        - station_type: 'MS' or 'DB' (optional)
        - update_existing: 'true' to update existing stations
        """
        # Check if user has admin permissions
        try:
            user_roles = list(request.user.user_roles.filter(active=True).values_list('role__code', flat=True))
            logger.info(f"User {request.user.email} has roles: {user_roles}")
            if not any(role in ['SUPER_ADMIN', 'EIC'] for role in user_roles):
                return Response({
                    'error': f'Insufficient permissions. User {request.user.email} has roles: {user_roles}'
                }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error checking user roles: {e}")
            return Response({
                'error': 'Error checking permissions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        station_type = request.query_params.get('station_type')
        update_existing = request.query_params.get('update_existing') == 'true'
        
        try:
            # Capture command output
            out = StringIO()
            
            # Build command arguments
            args = []
            if station_type:
                args.extend(['--station-type', station_type])
            if update_existing:
                args.append('--update-existing')
            
            # Execute management command
            call_command('import_stations_from_sap', *args, stdout=out)
            
            output = out.getvalue()
            
            # Parse output for summary
            import re
            # Remove ANSI color codes
            clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
            lines = clean_output.split('\n')
            created = updated = skipped = 0
            for line in lines:
                if '✓ Created:' in line:
                    try:
                        created = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '✓ Updated:' in line:
                    try:
                        updated = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '⊘ Skipped:' in line:
                    try:
                        skipped = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
            
            summary_parts = []
            if created > 0: summary_parts.append(f"{created} created")
            if updated > 0: summary_parts.append(f"{updated} updated")
            if skipped > 0: summary_parts.append(f"{skipped} skipped")
            summary = ', '.join(summary_parts) if summary_parts else 'No changes'
            
            return Response({
                'success': True,
                'message': 'Station sync completed successfully',
                'summary': summary,
                'output': output
            })
            
        except Exception as e:
            logger.error(f"Station sync error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SAPUserSyncView(views.APIView):
    """
    API endpoint for syncing users to SAP
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Sync users from local database to SAP
        
        POST /api/sap/sync-users/
        Query Parameters:
        - active_only: 'true' to sync only active users
        """
        # Check if user has admin permissions
        try:
            user_roles = list(request.user.user_roles.filter(active=True).values_list('role__code', flat=True))
            logger.info(f"User {request.user.email} has roles: {user_roles}")
            if not any(role in ['SUPER_ADMIN', 'EIC'] for role in user_roles):
                return Response({
                    'error': f'Insufficient permissions. User {request.user.email} has roles: {user_roles}'
                }, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            logger.error(f"Error checking user roles: {e}")
            return Response({
                'error': 'Error checking permissions'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        active_only = request.query_params.get('active_only') == 'true'
        force_sync = request.query_params.get('force') == 'true'
        
        try:
            # Capture command output
            out = StringIO()
            
            # Build command arguments
            args = ['--all']
            if active_only:
                args.append('--active-only')
            if force_sync:
                args.append('--force')
            
            # Execute management command
            call_command('sync_users_to_sap', *args, stdout=out)
            
            output = out.getvalue()
            
            # Parse output for summary
            import re
            # Remove ANSI color codes
            clean_output = re.sub(r'\x1b\[[0-9;]*m', '', output)
            lines = clean_output.split('\n')
            successful = failed = 0
            for line in lines:
                if '✓ Successful:' in line:
                    try:
                        successful = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif '✗ Failed:' in line:
                    try:
                        failed = int(line.split(':')[1].strip())
                    except (ValueError, IndexError):
                        pass
            
            summary_parts = []
            if successful > 0: summary_parts.append(f"{successful} synced")
            if failed > 0: summary_parts.append(f"{failed} failed")
            summary = ', '.join(summary_parts) if summary_parts else 'No users processed'
            
            return Response({
                'success': True,
                'message': 'User sync completed successfully',
                'summary': summary,
                'output': output
            })
            
        except Exception as e:
            logger.error(f"User sync error: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)