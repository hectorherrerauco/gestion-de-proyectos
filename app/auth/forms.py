from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

from ..models import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    remember = BooleanField("Recordarme")
    submit = SubmitField("Iniciar sesión")


class RegisterForm(FlaskForm):
    name = StringField("Nombre completo", validators=[DataRequired(), Length(2, 120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Contraseña", validators=[DataRequired(), Length(min=8, message="Mínimo 8 caracteres.")])
    confirm = PasswordField("Confirmar contraseña", validators=[DataRequired(), EqualTo("password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Crear cuenta")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("Este email ya está registrado.")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Enviar enlace")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("Nueva contraseña", validators=[DataRequired(), Length(min=8, message="Mínimo 8 caracteres.")])
    confirm = PasswordField("Confirmar contraseña", validators=[DataRequired(), EqualTo("password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Restablecer contraseña")


class ProfileForm(FlaskForm):
    name = StringField("Nombre completo", validators=[DataRequired(), Length(2, 120)])
    submit = SubmitField("Guardar cambios")


class ChangePasswordForm(FlaskForm):
    current = PasswordField("Contraseña actual", validators=[DataRequired()])
    password = PasswordField("Nueva contraseña", validators=[DataRequired(), Length(min=8, message="Mínimo 8 caracteres.")])
    confirm = PasswordField("Confirmar contraseña", validators=[DataRequired(), EqualTo("password", "Las contraseñas no coinciden.")])
    submit = SubmitField("Cambiar contraseña")
