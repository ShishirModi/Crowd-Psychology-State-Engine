from rest_framework.authentication import SessionAuthentication


class CsrfExemptSessionAuthentication(SessionAuthentication):
    """Session auth without CSRF enforcement — CORS headers provide the protection."""

    def enforce_csrf(self, request):
        return
