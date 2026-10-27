from datetime import datetime, timezone

from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


class Role(db.Model):
    __tablename__ = "roles"

    ADMIN = "admin"
    DEVELOPER = "developer"
    CLIENT = "client"

    DEFAULTS = {
        ADMIN: ("Project Manager", "Gestiona proyectos, asigna presupuestos y miembros."),
        DEVELOPER: ("Desarrollador", "Gestiona tareas y reporta horas/avances."),
        CLIENT: ("Cliente / Stakeholder", "Visualiza informes, métricas y estado del proyecto."),
    }

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False)
    label = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255))
    users = db.relationship("User", back_populates="role", lazy="dynamic")

    @classmethod
    def seed(cls):
        for name, (label, desc) in cls.DEFAULTS.items():
            if not cls.query.filter_by(name=name).first():
                db.session.add(cls(name=name, label=label, description=desc))
        db.session.commit()

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    is_active_flag = db.Column("is_active", db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    role = db.relationship("Role", back_populates="users")

    # --- Flask-Login ---
    @property
    def is_active(self):
        return self.is_active_flag

    # --- Contraseña ---
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- Roles ---
    def has_role(self, *names):
        return self.role is not None and self.role.name in names

    @property
    def is_admin(self):
        return self.has_role(Role.ADMIN)

    @property
    def initials(self):
        parts = self.name.split()
        return "".join(p[0] for p in parts[:2]).upper()

    # --- Tokens de recuperación / invitación ---
    TOKEN_EXPIRY = {"reset": "PASSWORD_RESET_EXPIRES", "invite": "INVITE_EXPIRES"}

    @staticmethod
    def _serializer(purpose):
        return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=f"password-{purpose}")

    def get_reset_token(self, purpose="reset"):
        # Incluye parte del hash: el token queda invalidado al cambiar la contraseña
        return self._serializer(purpose).dumps({"uid": self.id, "h": self.password_hash[-12:]})

    @classmethod
    def verify_reset_token(cls, token, purpose="reset"):
        try:
            max_age = current_app.config[cls.TOKEN_EXPIRY[purpose]]
            data = cls._serializer(purpose).loads(token, max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        user = db.session.get(cls, data.get("uid"))
        if user and user.password_hash[-12:] == data.get("h"):
            return user
        return None

    def __repr__(self):
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
