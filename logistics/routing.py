from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/driver/updates/$', consumers.DriverConsumer.as_asgi()),
    re_path(r'ws/user/updates/$', consumers.UserConsumer.as_asgi()),
]
