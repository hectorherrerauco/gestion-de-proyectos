from flask import current_app, url_for
from flask_mail import Message

from ..extensions import mail


def _deliver(user, subject, body, link, kind):
    if not current_app.config.get("MAIL_SERVER"):
        current_app.logger.warning("[DEV] Enlace de %s para %s: %s", kind, user.email, link)
        print(f"\n[DEV] Enlace de {kind} para {user.email}:\n{link}\n", flush=True)
        return link
    mail.send(Message(subject, recipients=[user.email], body=body))
    return link


def send_reset_email(user):
    link = url_for("auth.reset_password", token=user.get_reset_token(), _external=True)
    body = (
        f"Hola {user.name},\n\n"
        f"Para restablecer tu contraseña en DevProject Manager visita:\n{link}\n\n"
        "El enlace expira en 30 minutos. Si no lo solicitaste, ignora este correo."
    )
    return _deliver(user, "Recupera tu contraseña — DevProject Manager", body, link, "recuperación")


def send_invite_email(user, invited_by):
    link = url_for("auth.accept_invite", token=user.get_reset_token("invite"), _external=True)
    body = (
        f"Hola {user.name},\n\n"
        f"{invited_by.name} te ha invitado a DevProject Manager como {user.role.label}.\n"
        f"Activa tu cuenta y define tu contraseña aquí:\n{link}\n\n"
        "El enlace expira en 72 horas."
    )
    return _deliver(user, "Invitación a DevProject Manager", body, link, "invitación")
