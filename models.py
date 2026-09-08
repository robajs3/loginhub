from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class HubUser(db.Model):
    __tablename__ = "hub_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    display_name = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    links = db.relationship("SsoLink", backref="hub_user", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, raw_password)


class SsoLink(db.Model):
    """Mapowanie: konto Huba <-> lokalny user_id w konkretnej appce."""
    __tablename__ = "sso_links"
    __table_args__ = (
        db.UniqueConstraint("hub_user_id", "app_slug", name="uq_hub_user_app"),
    )

    id = db.Column(db.Integer, primary_key=True)
    hub_user_id = db.Column(db.Integer, db.ForeignKey("hub_users.id"), nullable=False)
    app_slug = db.Column(db.String(50), nullable=False)
    local_user_id = db.Column(db.Integer, nullable=False)
    local_username = db.Column(db.String(120), nullable=True)  # tylko do wyświetlania w panelu
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
