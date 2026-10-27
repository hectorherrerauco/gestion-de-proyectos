import os

import click
from flask import Flask, render_template

from config import Config
from .extensions import db, migrate, login_manager, mail, csrf


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registra modelos)
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .admin import bp as admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    register_error_handlers(app)
    register_cli(app)
    return app


def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404


def register_cli(app):
    from .models import Role, User

    @app.cli.command("seed-roles")
    def seed_roles():
        """Crea los roles por defecto."""
        Role.seed()
        click.echo("Roles creados.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Nombre")
    @click.option("--email", prompt="Email")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Crea un usuario Project Manager / Administrador."""
        Role.seed()
        email = email.strip().lower()
        if User.query.filter_by(email=email).first():
            click.echo("Ya existe un usuario con ese email.")
            return
        user = User(name=name, email=email, role=Role.query.filter_by(name=Role.ADMIN).first())
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrador {email} creado.")
