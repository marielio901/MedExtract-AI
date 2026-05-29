from app.extensions import db
from app.models import AuditLog


class AuditService:
    @staticmethod
    def log(action, entity_type, entity_id=None, details=None):
        audit = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details or {},
        )
        db.session.add(audit)
        db.session.commit()
        return audit
