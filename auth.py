from datetime import timedelta
from urllib.parse import urlparse

from flask import Blueprint, current_app, redirect, render_template, request, url_for, make_response

from models import db, HubUser, SsoLink
from sso import issue_token
import app_db

auth_bp = Blueprint("auth", __name__)


def _safe_next(target: str) -> str:
    """Dopuszcza tylko lokalne ścieżki jako 'next', żeby uniknąć open-redirect."""
    if not target:
        return "/"
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return "/"
    return target


def _try_migrate_password(user: HubUser, password: str) -> bool:
    """Jeśli HubUser nie ma jeszcze własnego hasła (password_hash is None), próbuje
    zweryfikować podane hasło względem hasha w KAŻDEJ połączonej appce. Przy trafieniu
    przyjmuje to hasło jako własne hasło w Hubie (haszując je po swojemu)."""
    if user.password_hash:
        return False  # już zmigrowany / ma własne hasło — nie nadpisujemy

    apps_config = current_app.config["APPS"]
    links = SsoLink.query.filter_by(hub_user_id=user.id).all()
    for link in links:
        stored_hash = app_db.fetch_password_hash(apps_config, link.app_slug, link.local_user_id)
        if app_db.verify_against_stored_hash(password, stored_hash):
            user.set_password(password)
            db.session.commit()
            return True
    return False


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    next_url = _safe_next(request.args.get("next") or request.form.get("next") or "/")

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = HubUser.query.filter_by(username=username).first()
        authenticated = False
        if user:
            if user.check_password(password):
                authenticated = True
            elif _try_migrate_password(user, password):
                authenticated = True

        if authenticated:
            token = issue_token(current_app.config["SSO_SECRET"], user.id, user.username)
            resp = make_response(redirect(next_url))
            resp.set_cookie(
                current_app.config["SSO_COOKIE_NAME"],
                token,
                max_age=int(timedelta(days=current_app.config["SSO_SESSION_DAYS"]).total_seconds()),
                path="/",
                httponly=True,
                secure=True,       # wymaga HTTPS (Tailscale Funnel to zapewnia)
                samesite="Lax",
            )
            return resp

        return render_template("login.html", error="Błędny login lub hasło", next=next_url)

    return render_template("login.html", error=None, next=next_url)


@auth_bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for("auth.login")))
    resp.delete_cookie(current_app.config["SSO_COOKIE_NAME"], path="/")
    return resp
