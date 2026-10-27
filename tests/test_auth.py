import pytest

from app import create_app
from app.extensions import db
from app.models import Role, User
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        Role.seed()
        for name, email, role in [("Ana Admin", "admin@x.com", Role.ADMIN),
                                  ("Dev Uno", "dev@x.com", Role.DEVELOPER),
                                  ("Cli Ente", "cli@x.com", Role.CLIENT)]:
            u = User(name=name, email=email, role=Role.query.filter_by(name=role).first())
            u.set_password("password123")
            db.session.add(u)
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email, pwd="password123"):
    return client.post("/auth/login", data={"email": email, "password": pwd}, follow_redirects=True)


def test_register_creates_developer(client, app):
    r = client.post("/auth/register", data={"name": "Nuevo User", "email": "new@x.com",
                                            "password": "secret123", "confirm": "secret123"}, follow_redirects=True)
    assert "Cuenta creada" in r.get_data(as_text=True)
    assert User.query.filter_by(email="new@x.com").first().role.name == Role.DEVELOPER


def test_register_duplicate_email(client):
    r = client.post("/auth/register", data={"name": "X", "email": "dev@x.com",
                                            "password": "secret123", "confirm": "secret123"})
    assert "ya está registrado" in r.get_data(as_text=True)


def test_login_logout(client):
    assert "Bienvenido" in login(client, "dev@x.com").get_data(as_text=True)
    assert "Sesión cerrada" in client.get("/auth/logout", follow_redirects=True).get_data(as_text=True)


def test_login_wrong_password(client):
    assert "incorrectos" in login(client, "dev@x.com", "bad").get_data(as_text=True)


def test_inactive_user_cannot_login(client, app):
    u = User.query.filter_by(email="dev@x.com").first()
    u.is_active_flag = False
    db.session.commit()
    assert "desactivada" in login(client, "dev@x.com").get_data(as_text=True)


def test_dashboard_requires_login(client):
    r = client.get("/dashboard")
    assert r.status_code == 302 and "/auth/login" in r.location


@pytest.mark.parametrize("email,code", [("admin@x.com", 200), ("dev@x.com", 403), ("cli@x.com", 403)])
def test_rbac_admin_users(client, email, code):
    login(client, email)
    assert client.get("/admin/users").status_code == code


def test_admin_changes_role(client):
    login(client, "admin@x.com")
    dev = User.query.filter_by(email="dev@x.com").first()
    client_role = Role.query.filter_by(name=Role.CLIENT).first()
    client.post(f"/admin/users/{dev.id}/role", data={"role_id": client_role.id})
    assert db.session.get(User, dev.id).role.name == Role.CLIENT


def test_password_reset_flow(client):
    user = User.query.filter_by(email="dev@x.com").first()
    token = user.get_reset_token()
    r = client.post(f"/auth/reset-password/{token}", data={"password": "newpass123", "confirm": "newpass123"},
                    follow_redirects=True)
    assert "Contraseña actualizada" in r.get_data(as_text=True)
    assert "Bienvenido" in login(client, "dev@x.com", "newpass123").get_data(as_text=True)
    # El token queda invalidado tras usarse
    client.get("/auth/logout")
    r = client.get(f"/auth/reset-password/{token}", follow_redirects=True)
    assert "inválido" in r.get_data(as_text=True)


def test_forgot_password_generic_message(client):
    r = client.post("/auth/forgot-password", data={"email": "nobody@x.com"}, follow_redirects=True)
    assert "Si el email está registrado" in r.get_data(as_text=True)


def test_admin_invites_user_and_user_activates(client):
    login(client, "admin@x.com")
    role = Role.query.filter_by(name=Role.CLIENT).first()
    r = client.post("/admin/users/new", data={"name": "Invitado Uno", "email": "inv@x.com", "role_id": role.id},
                    follow_redirects=True)
    assert "/auth/invite/" in r.get_data(as_text=True)
    user = User.query.filter_by(email="inv@x.com").first()
    assert user.role.name == Role.CLIENT and user.last_login is None
    token = user.get_reset_token("invite")
    client.get("/auth/logout")
    r = client.post(f"/auth/invite/{token}", data={"password": "clave12345", "confirm": "clave12345"},
                    follow_redirects=True)
    assert "Tu cuenta está activa" in r.get_data(as_text=True)
    # Token de un solo uso
    client.get("/auth/logout")
    assert "inválida" in client.get(f"/auth/invite/{token}", follow_redirects=True).get_data(as_text=True)
    assert "Bienvenido" in login(client, "inv@x.com", "clave12345").get_data(as_text=True)


def test_reset_token_not_valid_as_invite(client):
    user = User.query.filter_by(email="dev@x.com").first()
    r = client.get(f"/auth/invite/{user.get_reset_token('reset')}", follow_redirects=True)
    assert "inválida" in r.get_data(as_text=True)


def test_non_admin_cannot_invite(client):
    login(client, "dev@x.com")
    assert client.get("/admin/users/new").status_code == 403
