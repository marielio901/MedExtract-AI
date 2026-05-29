from app.routes.api_routes import api_bp
from app.routes.crud_routes import crud_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.document_routes import document_bp
from app.routes.upload_routes import upload_bp

__all__ = ["api_bp", "crud_bp", "dashboard_bp", "document_bp", "upload_bp"]
