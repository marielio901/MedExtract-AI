import logging

from pydantic import ValidationError

from app.schemas import MedicalRecordSchema

logger = logging.getLogger(__name__)


class ValidationService:
    @staticmethod
    def validate_medical_record(payload):
        try:
            schema = MedicalRecordSchema(**(payload or {}))
            if hasattr(schema, "model_dump"):
                return schema.model_dump()
            return schema.dict()
        except ValidationError as exc:
            logger.warning("medical_record_validation_failed", extra={"errors": exc.errors()})
            raise
