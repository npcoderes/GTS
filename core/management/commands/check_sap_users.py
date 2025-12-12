"""
Django management command to fetch and display users from SAP (for verification only).
Does NOT import users into Django database.
"""
from django.core.management.base import BaseCommand
from core.sap_integration import sap_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Fetch and display users from SAP (verification only - does not import)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Fetch specific user by username',
        )

    def handle(self, *args, **options):
        username = options.get('username')

        if username:
            self.stdout.write(f"Fetching user '{username}' from SAP...")
        else:
            self.stdout.write("Note: SAP GTS1 endpoint requires username for DISP operation")
            self.stdout.write("Usage: python manage.py check_sap_users --username <username>")
            return

        try:
            # Fetch user from SAP using DISP operation
            sap_result = sap_service.get_user_from_sap(username)
            
            if not sap_result['success']:
                self.stdout.write(self.style.ERROR(f"Failed to fetch from SAP: {sap_result.get('error')}"))
                return

            user_data = sap_result.get('data', {})
            
            if not user_data:
                self.stdout.write(self.style.WARNING(f'No data returned for user: {username}'))
                return

            # Display SAP response
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS(f"✅ SAP User Data for: {username}"))
            self.stdout.write("=" * 60)
            
            # Pretty print the response
            import json
            self.stdout.write(json.dumps(user_data, indent=2))
            
            # Try to parse if it's in the expected format
            try:
                response_data = user_data.get('ZSD_GTS1.Response', {})
                it_data = response_data.get('IT_DATA', {})
                item = it_data.get('item', {})
                
                if item:
                    self.stdout.write("\n" + "=" * 60)
                    self.stdout.write(self.style.SUCCESS("📊 Parsed User Information:"))
                    self.stdout.write("=" * 60)
                    self.stdout.write(f"Username: {item.get('INPUT1', 'N/A')}")
                    self.stdout.write(f"Email: {item.get('INPUT2', 'N/A')}")
                    self.stdout.write(f"Station ID: {item.get('INPUT3', 'N/A')}")
                    self.stdout.write(f"Role Code: {item.get('INPUT4', 'N/A')}")
                    self.stdout.write(f"Active Status: {'Active' if item.get('INPUT5') == '1' else 'Inactive'}")
                    self.stdout.write(f"Role In Date: {item.get('INPUT6', 'N/A')}")
                    self.stdout.write(f"Role Out Date: {item.get('INPUT7', 'N/A')}")
            except Exception as parse_error:
                self.stdout.write(self.style.WARNING(f"\nNote: Could not parse structured data: {parse_error}"))
            
            self.stdout.write("\n" + "=" * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching from SAP: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
