"""
Wewnętrzne API wołane przez sso_middleware.py każdej appki.
Nie jest (i nie powinno być) wystawione publicznie przez Funnel — appki wołają je
albo po localhoście (systemd), albo przez sieć sso_net po nazwie kontenera Huba (docker).
Zabezpieczone współdzielonym sekretem SSO_SECRET w nagłówku, żeby ktokolwiek z
zewnątrz sieci lokalnej/dockerowej nie mógł wyciągać mapowań kont.
"""
from flask import Blueprint, current_app, jsonify, request

from models import db, HubUser, SsoLink

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _check_api_secret():
    provided = request.headers.get("X-SSO-Api-Key", "")
    return provided and provided == current_app.config["SSO_SECRET"]


@api_bp.route("/resolve")
def resolve():
    if not _check_api_secret():
        return jsonify({"error": "unauthorized"}), 401

    app_slug = request.args.get("app_slug")
    hub_user_id = request.args.get("hub_user_id", type=int)
    if not app_slug or not hub_user_id:
        return jsonify({"error": "missing app_slug or hub_user_id"}), 400

    link = SsoLink.query.filter_by(app_slug=app_slug, hub_user_id=hub_user_id).first()
    if not link:
        return jsonify({"linked": False}), 404

    return jsonify({
        "linked": True,
        "local_user_id": link.local_user_id,
        "local_username": link.local_username,
    })


@api_bp.route("/link", methods=["POST"])
def link():
    """Appka woła to sama, gdy dla zalogowanego przez SSO (ale jeszcze niepodłączonego)
    hub_user_id założyła u siebie nowe lokalne konto — Hub zapisuje mapowanie, żeby
    kolejne wizyty (i panel /admin) już je widziały. Appka NIC nie musi wiedzieć poza
    tym, że ma nowy lokalny user_id do zgłoszenia."""
    if not _check_api_secret():
        return jsonify({"error": "unauthorized"}), 401

    payload = request.get_json(silent=True) or request.form
    app_slug = payload.get("app_slug")
    hub_user_id = payload.get("hub_user_id")
    local_user_id = payload.get("local_user_id")
    local_username = payload.get("local_username")

    try:
        hub_user_id = int(hub_user_id)
        local_user_id = int(local_user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "missing/invalid hub_user_id or local_user_id"}), 400

    apps_config = current_app.config["APPS"]
    if not app_slug or app_slug not in apps_config:
        return jsonify({"error": "nieznana appka"}), 400

    if not HubUser.query.get(hub_user_id):
        return jsonify({"error": "nieznany hub_user_id"}), 404

    # Ktoś mógł już połączyć to konto w międzyczasie (np. równoległy request albo
    # admin ręcznie w panelu) — nie nadpisujemy istniejącego mapowania samym API,
    # appka i tak już ma swoje lokalne konto założone, więc po prostu odsyłamy to,
    # co Hub faktycznie ma zapisane.
    existing = SsoLink.query.filter_by(app_slug=app_slug, hub_user_id=hub_user_id).first()
    if existing:
        return jsonify({
            "linked": True,
            "local_user_id": existing.local_user_id,
            "local_username": existing.local_username,
            "created": False,
        })

    # ten sam lokalny user_id nie może być podpięty pod dwa różne konta Huba w tej appce
    clash = SsoLink.query.filter_by(app_slug=app_slug, local_user_id=local_user_id).first()
    if clash:
        return jsonify({"error": "local_user_id już połączony z innym kontem Huba"}), 409

    db.session.add(SsoLink(
        hub_user_id=hub_user_id,
        app_slug=app_slug,
        local_user_id=local_user_id,
        local_username=local_username,
    ))
    db.session.commit()

    return jsonify({
        "linked": True,
        "local_user_id": local_user_id,
        "local_username": local_username,
        "created": True,
    }), 201
