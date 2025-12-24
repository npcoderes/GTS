from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

class TokenExpiredException(AuthenticationFailed):
    status_code = 401
    default_detail = 'Token has expired.'
    default_code = 'TOKEN_EXPIRED'

class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Token authentication with expiration.
    Tokens expire after TOKEN_EXPIRY_HOURS (default: 24 hours).
    Returns unique error code 'TOKEN_EXPIRED' when token expires.
    """
    
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')

        # Check token expiration
        expiry_hours = getattr(settings, 'TOKEN_EXPIRY_HOURS', 24)
        token_age = timezone.now() - token.created
        
        if token_age > timedelta(hours=expiry_hours):
            token.delete()
            raise TokenExpiredException()

        return (token.user, token)
