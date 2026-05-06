from drf_spectacular.extensions import OpenApiAuthenticationExtension


class JWTCookieAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = 'accounts.jwt_cookie_auth.JWTCookieAuthentication'
    name = 'JWTCookieAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'access_token',
            'description': 'JWT access token stored in an HttpOnly cookie.',
        }


class CookieTokenAuthenticationExtension(OpenApiAuthenticationExtension):
    target_class = 'accounts.cookie_auth.CookieTokenAuthentication'
    name = 'CookieTokenAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'apiKey',
            'in': 'cookie',
            'name': 'auth_token',
            'description': 'DRF Token stored in an HttpOnly cookie.',
        }
