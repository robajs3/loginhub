import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://hub:hub@localhost:5432/hub"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SSO_SECRET = os.environ.get("SSO_SECRET", "dev-sso-secret-change-me")
    SSO_COOKIE_NAME = os.environ.get("SSO_COOKIE_NAME", "sso_session")
    SSO_SESSION_DAYS = int(os.environ.get("SSO_SESSION_DAYS", "30"))

    # Samodzielna rejestracja pod /auth/register. Hub jest wystawiony publicznie
    # przez Tailscale Funnel, więc domyślnie WŁĄCZONE, ale jeśli chcesz, żeby konta
    # zakładał tylko admin (panel /admin -> "Nowe konto"), ustaw w .env:
    #   ALLOW_REGISTRATION=false
    ALLOW_REGISTRATION = os.environ.get("ALLOW_REGISTRATION", "true").strip().lower() in ("1", "true", "yes")

    # Rejestr appek widocznych w panelu admina — slug musi być identyczny z tym,
    # którego appka używa w sso_middleware.py (APP_SLUG w jej configu).
    # display_column = kolumna pokazywana w panelu jako "login" (różni się między appkami!).
    APPS = {
        "filevault":    {"label": "FileVault",    "db_url_env": "FILEVAULT_DB_URL",    "users_table": "users", "display_column": "username"},
        "koloseum":     {"label": "Koloseum",      "db_url_env": "KOLOSEUM_DB_URL",     "users_table": "users", "display_column": "username"},
        "zflix":        {"label": "zFlix",         "db_url_env": "ZFLIX_DB_URL",        "users_table": "users", "display_column": "username"},
        "easyconv":     {"label": "EasyConv",      "db_url_env": "EASYCONV_DB_URL",     "users_table": "users", "display_column": "username"},
        "homelibrary":  {"label": "Home Library",  "db_url_env": "HOMELIBRARY_DB_URL",  "users_table": "users", "display_column": "email"},
        "notemaster":   {"label": "NoteMaster",    "db_url_env": "NOTEMASTER_DB_URL",   "users_table": "users", "display_column": "username"},
        "gameplan":     {"label": "GamePlan",      "db_url_env": "GAMEPLAN_DB_URL",     "users_table": "user",  "display_column": "username"},
        "planowiec":    {"label": "Planowiec",     "db_url_env": "PLANOWIEC_DB_URL",    "users_table": "users", "display_column": "username"},
    }
