"""
Podpisywanie i weryfikacja tokenu SSO trzymanego w ciasteczku `sso_session`.

Token niesie WYŁĄCZNIE ogólną tożsamość Huba (hub_user_id, username) — NIE lokalne
ID użytkownika w konkretnej appce, bo jedno ciasteczko jest wspólne dla wszystkich
8 appek na tym samym hoście. Każda appka sama dopytuje Huba (endpoint /api/resolve)
o swoje lokalne ID, gdy zobaczy ważny token bez lokalnej sesji.
"""
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SALT = "sso-hub-v1"


def make_serializer(secret: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(secret, salt=SALT)


def issue_token(secret: str, hub_user_id: int, username: str) -> str:
    s = make_serializer(secret)
    return s.dumps({"hub_user_id": hub_user_id, "username": username})


def verify_token(secret: str, token: str, max_age_seconds: int):
    """Zwraca dict {hub_user_id, username} albo None jeśli token nieważny/wygasły."""
    s = make_serializer(secret)
    try:
        return s.loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return None
