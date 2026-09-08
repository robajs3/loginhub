from functools import wraps

from flask import Blueprint, current_app, redirect, render_template, request, url_for, flash

from models import db, HubUser, SsoLink
from sso import verify_token
import app_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _current_hub_user():
    token = request.cookies.get(current_app.config["SSO_COOKIE_NAME"])
    if not token:
        return None
    max_age = current_app.config["SSO_SESSION_DAYS"] * 86400
    data = verify_token(current_app.config["SSO_SECRET"], token, max_age)
    if not data:
        return None
    return HubUser.query.get(data["hub_user_id"])


def require_admin(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = _current_hub_user()
        if not user:
            external_path = request.script_root + request.path
            return redirect(url_for("auth.login", next=external_path))
        if not user.is_admin:
            return "Brak uprawnień administratora.", 403
        request.hub_user = user
        return view(*args, **kwargs)
    return wrapped


def fetch_app_users(app_slug: str):
    return app_db.fetch_app_users(current_app.config["APPS"], app_slug)


@admin_bp.route("/")
@require_admin
def dashboard():
    users = HubUser.query.order_by(HubUser.username).all()
    links = SsoLink.query.all()
    links_by_user = {}
    for link in links:
        links_by_user.setdefault(link.hub_user_id, []).append(link)
    apps = current_app.config["APPS"]
    return render_template(
        "admin/dashboard.html",
        users=users,
        links_by_user=links_by_user,
        apps=apps,
        current_user=request.hub_user,
    )


@admin_bp.route("/users/new", methods=["POST"])
@require_admin
def new_user():
    username = (request.form.get("username") or "").strip()
    display_name = (request.form.get("display_name") or "").strip()
    password = request.form.get("password") or ""
    is_admin = bool(request.form.get("is_admin"))

    if not username:
        flash("Podaj login.", "error")
        return redirect(url_for("admin.dashboard"))

    if HubUser.query.filter_by(username=username).first():
        flash("Taki login już istnieje w LoginHub.", "error")
        return redirect(url_for("admin.dashboard"))

    user = HubUser(username=username, display_name=display_name or username, is_admin=is_admin)
    if password:
        user.set_password(password)
    # jeśli hasło puste: password_hash zostaje NULL — użytkownik "domigruje" je
    # sam przy pierwszym logowaniu swoim starym hasłem z połączonej appki
    db.session.add(user)
    db.session.commit()
    if password:
        flash(f"Utworzono konto: {username}", "ok")
    else:
        flash(f"Utworzono konto: {username} (bez hasła — połącz z appką, "
              f"a użytkownik zaloguje się swoim starym hasłem z niej za pierwszym razem)", "ok")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@require_admin
def delete_user(user_id):
    if user_id == request.hub_user.id:
        flash("Nie możesz usunąć własnego konta.", "error")
        return redirect(url_for("admin.dashboard"))
    user = HubUser.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f"Usunięto konto: {user.username}", "ok")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/clear-password", methods=["POST"])
@require_admin
def clear_password(user_id):
    user = HubUser.query.get_or_404(user_id)
    user.password_hash = None
    db.session.commit()
    flash(f"Wyczyszczono hasło dla {user.username} — przy następnym logowaniu "
          f"zostanie zmigrowane ze starego hasła z połączonej appki.", "ok")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/link/<int:user_id>/<app_slug>")
@require_admin
def link_form(user_id, app_slug):
    user = HubUser.query.get_or_404(user_id)
    apps = current_app.config["APPS"]
    if app_slug not in apps:
        return "Nieznana appka", 404

    app_users, error = fetch_app_users(app_slug)
    existing_link = SsoLink.query.filter_by(hub_user_id=user_id, app_slug=app_slug).first()

    return render_template(
        "admin/link.html",
        user=user,
        app_slug=app_slug,
        app_label=apps[app_slug]["label"],
        app_users=app_users,
        error=error,
        existing_link=existing_link,
    )


@admin_bp.route("/link", methods=["POST"])
@require_admin
def create_link():
    hub_user_id = int(request.form["hub_user_id"])
    app_slug = request.form["app_slug"]
    local_user_id = int(request.form["local_user_id"])
    local_username = request.form.get("local_username") or None

    apps = current_app.config["APPS"]
    if app_slug not in apps:
        flash("Nieznana appka.", "error")
        return redirect(url_for("admin.dashboard"))

    existing = SsoLink.query.filter_by(hub_user_id=hub_user_id, app_slug=app_slug).first()
    if existing:
        existing.local_user_id = local_user_id
        existing.local_username = local_username
    else:
        db.session.add(SsoLink(
            hub_user_id=hub_user_id,
            app_slug=app_slug,
            local_user_id=local_user_id,
            local_username=local_username,
        ))
    db.session.commit()
    flash(f"Połączono z {apps[app_slug]['label']} (lokalny user #{local_user_id}).", "ok")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/link/<int:link_id>/delete", methods=["POST"])
@require_admin
def delete_link(link_id):
    link = SsoLink.query.get_or_404(link_id)
    db.session.delete(link)
    db.session.commit()
    flash("Usunięto połączenie.", "ok")
    return redirect(url_for("admin.dashboard"))
