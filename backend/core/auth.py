from ninja.security import HttpBearer

from core.services.auth import get_user_from_token
from core.services.presence import touch_user_activity


class JWTAuth(HttpBearer):
    def authenticate(self, request, token):
        try:
            user = get_user_from_token(token)
        except ValueError:
            return None
        touch_user_activity(user)
        request.auth_user = user
        return user


jwt_auth = JWTAuth()
