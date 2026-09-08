from flask import Flask

from config import Config
from models import db


class PrefixMiddleware:
    """Tailscale Funnel (--set-path=/auth) ZDEJMUJE prefiks /auth zanim przekaże
    request dalej — backend widzi już "gołą" ścieżkę (np. /admin/ zamiast
    /auth/admin/). Żeby url_for()/redirecty mimo to generowały poprawne, publiczne
    adresy z /auth z powrotem, ustawiamy WSGI SCRIPT_NAME. Działa też bezpiecznie,
    gdy ktoś odpytuje appkę bezpośrednio (bez proxy) — wtedy PATH_INFO i tak
    zwykle nie zaczyna się od prefiksu, więc nic nie jest ucinane podwójnie."""
    def __init__(self, wsgi_app, prefix=""):
        self.wsgi_app = wsgi_app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = self.prefix
        path_info = environ.get("PATH_INFO", "")
        if self.prefix and path_info.startswith(self.prefix):
            environ["PATH_INFO"] = path_info[len(self.prefix):]
        return self.wsgi_app(environ, start_response)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    import os
    PREFIX = os.environ.get("URL_PREFIX", "/auth").rstrip("/")
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix=PREFIX)

    from auth import auth_bp
    from admin import admin_bp
    from api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    with app.app_context():
        db.create_all()
        _ensure_bootstrap_admin(app)

    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("admin.dashboard"))

    return app


def _ensure_bootstrap_admin(app):
    """Jeśli w Hubie nie ma jeszcze żadnego konta, tworzy pierwsze admin/admin
    z wymuszoną zmianą przy pierwszym logowaniu byłoby lepsze, ale dla prostoty:
    tworzy konto z hasłem z env BOOTSTRAP_ADMIN_PASSWORD (albo losowym, wypisanym w logach)."""
    import os
    import secrets
    from models import HubUser

    if HubUser.query.count() > 0:
        return

    username = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD") or secrets.token_urlsafe(12)

    user = HubUser(username=username, display_name="Administrator", is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    app.logger.warning(
        "=== HUB: utworzono pierwsze konto administratora ===\n"
        f"    login: {username}\n"
        f"    hasło: {password}\n"
        "    ZMIEŃ HASŁO / usuń to konto i utwórz własne po pierwszym zalogowaniu, "
        "jeśli nie ustawiłeś BOOTSTRAP_ADMIN_PASSWORD w .env."
    )


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=8000, debug=True)
