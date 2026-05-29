from datetime import datetime, timezone

from app.extensions import db


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    source_file_name = db.Column(db.String(255), nullable=False, index=True)
    stored_file_path = db.Column(db.String(500), nullable=False)
    file_type = db.Column(db.String(20), nullable=False, index=True)
    file_size = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="pending", index=True)
    raw_ocr_text = db.Column(db.Text)
    error_message = db.Column(db.Text)
    extraction_confidence = db.Column(db.Float, default=0.0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    processed_at = db.Column(db.DateTime(timezone=True))

    medical_record = db.relationship(
        "MedicalRecord",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def to_dict(self, include_record=False):
        data = {
            "id": self.id,
            "source_file_name": self.source_file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "status": self.status,
            "raw_ocr_text": self.raw_ocr_text,
            "error_message": self.error_message,
            "extraction_confidence": self.extraction_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }
        if include_record:
            data["medical_record"] = (
                self.medical_record.to_dict() if self.medical_record else None
            )
        return data
