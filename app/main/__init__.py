from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from ..models import Role, User

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    stats = {}
    if current_user.is_admin:
        stats = {
            "total": User.query.count(),
            "active": User.query.filter_by(is_active_flag=True).count(),
            "by_role": {r.label: r.users.count() for r in Role.query.all()},
        }
    return render_template("main/dashboard.html", stats=stats)
