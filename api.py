"""
Wewnętrzne API wołane przez sso_middleware.py każdej appki.
Nie jest (i nie powinno być) wystawione publicznie przez Funnel — appki wołają je
albo po localhoście (systemd), albo przez sieć sso_net po nazwie kontenera Huba (docker).
Zabezpieczone współdzielonym sekretem SSO_SECRET w nagłówku, żeby ktokolwiek z
zewnątrz sieci lokalnej/dockerowej nie mógł wyciągać mapowań kont.
"""
from flask import Blueprint, current_app, jsonify, request

from models import SsoLink

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
