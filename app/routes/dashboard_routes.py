from flask import Blueprint, render_template

from app.services import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
@dashboard_bp.get("/dashboard")
def dashboard():
    return render_template(
        "dashboard.html",
        summary=DashboardService.summary(),
        charts=DashboardService.charts(),
        recent_activity=DashboardService.recent_activity(),
    )
