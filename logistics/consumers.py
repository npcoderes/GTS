import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class DriverConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Authenticate User (Driver)
        # Expected URL: ws/driver/updates/?token=XYZ
        try:
             # Basic Token Auth for Websocket
             query_string = self.scope['query_string'].decode()
             params = dict(x.split('=') for x in query_string.split('&') if '=' in x)
             token = params.get('token', None)
             
             if not token:
                 await self.close()
                 return
                 
             user = await self.get_user_from_token(token)
             if not user:
                 await self.close()
                 return
                 
             self.user = user
             self.driver_id = await self.get_driver_id(user)
             
             if not self.driver_id:
                 await self.close()
                 return
                 
             # Join group unique to this driver
             self.group_name = f"driver_{self.driver_id}"
             
             await self.channel_layer.group_add(
                 self.group_name,
                 self.channel_name
             )
             
             await self.accept()
             print(f"Driver {self.driver_id} connected to {self.group_name}")
             
             # Send welcome message
             await self.send(text_data=json.dumps({
                 'type': 'connection_established',
                 'message': 'Real-time updates active'
             }))
             
        except Exception as e:
            print(f"WebSocket Connection Error: {e}")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # We generally push TO client, but valid if client sends ack
        pass

    async def driver_update(self, event):
        """
        Handler for messages sent to the group.
        event = {
            'type': 'driver.update',
            'data': { ... }
        }
        """
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        from rest_framework.authtoken.models import Token
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def get_driver_id(self, user):
        if hasattr(user, 'driver_profile'):
            return user.driver_profile.id
        return None


class UserConsumer(AsyncWebsocketConsumer):
    """
    Generic consumer for all authenticated users.
    Used for permission change notifications and other user-specific events.
    """
    async def connect(self):
        # Authenticate User
        # Expected URL: ws/user/updates/?token=XYZ
        try:
            # Basic Token Auth for Websocket
            query_string = self.scope['query_string'].decode()
            params = dict(x.split('=') for x in query_string.split('&') if '=' in x)
            token = params.get('token', None)

            if not token:
                await self.close()
                return

            user = await self.get_user_from_token(token)
            if not user:
                await self.close()
                return

            self.user = user
            self.user_id = user.id

            # Join group unique to this user
            self.group_name = f"user_{self.user_id}"

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.accept()
            print(f"User {self.user_id} connected to {self.group_name}")

            # Send welcome message
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'User notifications active'
            }))

        except Exception as e:
            print(f"WebSocket Connection Error: {e}")
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        # Client messages can be handled here if needed
        pass

    async def permission_update(self, event):
        """
        Handler for permission change notifications.
        event = {
            'type': 'permission.update',
            'data': {
                'event_type': 'permissions_changed',
                'message': 'Your permissions have been updated'
            }
        }
        """
        await self.send(text_data=json.dumps(event['data']))

    async def user_notification(self, event):
        """
        Generic handler for any user notification.
        event = {
            'type': 'user.notification',
            'data': { ... }
        }
        """
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def get_user_from_token(self, token_key):
        from rest_framework.authtoken.models import Token
        try:
            return Token.objects.get(key=token_key).user
        except Token.DoesNotExist:
            return None
