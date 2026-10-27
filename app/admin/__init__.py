import secrets

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, ValidationError

from ..auth.email import send_invite_email
from ..decorators import role_required
from ..extensions import db
from ..models import Role, User

bp = Blueprint("admin", __name__)


class InviteUserForm(FlaskForm):
    name = StringField("Nombre completo", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    role_id = SelectField("Rol", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Enviar invitación")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Este email ya está registrado.")


def _flash_invite(user, link):
    if current_app.config.get("MAIL_SERVER"):
        flash(f"Invitación enviada a {user.email}.", "success")
    else:
        # Sin SMTP: mostramos el enlace al admin para que lo comparta manualmente
        flash(f"Invitación creada para {user.email}. Sin servidor de correo, comparte este enlace: {link}", "info")


@bp.route("/users")
@role_required(Role.ADMIN)
def users():
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.name.ilike(like), User.email.ilike(like)))
    return render_template("admin/users.html", users=query.order_by(User.created_at.desc()).all(),
                           roles=Role.query.all(), q=q)


@bp.route("/users/new", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def new_user():
    form = InviteUserForm()
    form.role_id.choices = [(r.id, r.label) for r in Role.query.all()]
    if request.method == "GET":
        dev = Role.query.filter_by(name=Role.DEVELOPER).first()
        form.role_id.data = dev.id if dev else None
    if form.validate_on_submit():
        user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(),
                    role=db.session.get(Role, form.role_id.data))
        user.set_password(secrets.token_urlsafe(32))  # contraseña aleatoria inutilizable hasta aceptar
        db.session.add(user)
        db.session.commit()
        _flash_invite(user, send_invite_email(user, current_user))
        return redirect(url_for("admin.users"))
    return render_template("admin/new_user.html", form=form)


@bp.route("/users/<int:user_id>/resend", methods=["POST"])
@role_required(Role.ADMIN)
def resend_invite(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.last_login:
        flash(f"{user.name} ya activó su cuenta.", "warning")
    else:
        _flash_invite(user, send_invite_email(user, current_user))
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@role_required(Role.ADMIN)
def change_role(user_id):
    user = db.session.get(User, user_id) or abort(404)
    role = db.session.get(Role, request.form.get("role_id", type=int)) or abort(400)
    if user.id == current_user.id and role.name != Role.ADMIN:
        flash("No puedes quitarte tu propio rol de administrador.", "warning")
    else:
        user.role = role
        db.session.commit()
        flash(f"Rol de {user.name} cambiado a {role.label}.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@role_required(Role.ADMIN)
def toggle_active(user_id):
    user = db.session.get(User, user_id) or abort(404)
    if user.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta.", "warning")
    else:
        user.is_active_flag = not user.is_active_flag
        db.session.commit()
        flash(f"{user.name} {'activado' if user.is_active_flag else 'desactivado'}.", "success")
    return redirect(url_for("admin.users"))
