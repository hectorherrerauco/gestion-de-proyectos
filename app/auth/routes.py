from datetime import datetime, timezone
from urllib.parse import urlparse

from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from . import bp
from .email import send_reset_email
from .forms import (LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm,
                    ProfileForm, ChangePasswordForm)
from ..extensions import db
from ..models import User, Role


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        Role.seed()
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(),
                    role=Role.query.filter_by(name=Role.DEVELOPER).first())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Cuenta creada. Ya puedes iniciar sesión.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user is None or not user.check_password(form.password.data):
            flash("Email o contraseña incorrectos.", "danger")
        elif not user.is_active:
            flash("Tu cuenta está desactivada. Contacta al administrador.", "danger")
        else:
            login_user(user, remember=form.remember.data)
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            flash(f"¡Bienvenido, {user.name}!", "success")
            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc:
                next_page = url_for("main.dashboard")
            return redirect(next_page)
    return render_template("auth/login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_active:
            send_reset_email(user)
        # Mensaje genérico para no revelar qué emails existen
        flash("Si el email está registrado, recibirás un enlace para restablecer tu contraseña.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/forgot_password.html", form=form)


@bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    user = User.verify_reset_token(token)
    if user is None:
        flash("El enlace es inválido o ha expirado.", "danger")
        return redirect(url_for("auth.forgot_password"))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Contraseña actualizada. Inicia sesión.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)


@bp.route("/invite/<token>", methods=["GET", "POST"])
def accept_invite(token):
    if current_user.is_authenticated:
        logout_user()
    user = User.verify_reset_token(token, purpose="invite")
    if user is None or not user.is_active:
        flash("La invitación es inválida, ya fue usada o ha expirado. Pide al administrador que la reenvíe.", "danger")
        return redirect(url_for("auth.login"))
    form = ResetPasswordForm()
    form.submit.label.text = "Activar cuenta"
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        login_user(user)
        flash(f"¡Bienvenido, {user.name}! Tu cuenta está activa.", "success")
        return redirect(url_for("main.dashboard"))
    return render_template("auth/accept_invite.html", form=form, user=user)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(prefix="p", obj=current_user)
    pwd_form = ChangePasswordForm(prefix="c")
    if profile_form.submit.data and profile_form.validate_on_submit():
        current_user.name = profile_form.name.data.strip()
        db.session.commit()
        flash("Perfil actualizado.", "success")
        return redirect(url_for("auth.profile"))
    if pwd_form.submit.data and pwd_form.validate_on_submit():
        if not current_user.check_password(pwd_form.current.data):
            flash("La contraseña actual no es correcta.", "danger")
        else:
            current_user.set_password(pwd_form.password.data)
            db.session.commit()
            flash("Contraseña cambiada.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", profile_form=profile_form, pwd_form=pwd_form)
