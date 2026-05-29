from datetime import datetime, timezone

from app.extensions import db


class MedicalRecord(db.Model):
    __tablename__ = "medical_records"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(
        db.Integer, db.ForeignKey("documents.id", ondelete="CASCADE"), unique=True
    )
    document_type = db.Column(db.String(80), default="medical_record", index=True)
    hospital_name = db.Column(db.String(255), index=True)
    hospital_address = db.Column(db.String(500))
    hospital_phone = db.Column(db.String(80))
    hospital_npi = db.Column(db.String(80))
    patient_name = db.Column(db.String(255), index=True)
    mrn = db.Column(db.String(80), index=True)
    guarantor_no = db.Column(db.String(120), index=True)
    dob = db.Column(db.String(50))
    statement_date = db.Column(db.String(50))
    primary_insurance = db.Column(db.String(255), index=True)
    group_no = db.Column(db.String(120))
    chief_complaint = db.Column(db.Text)
    admission_diagnosis = db.Column(db.Text, index=True)
    primary_diagnosis = db.Column(db.Text, index=True)
    icd10_code = db.Column(db.String(40), index=True)
    hospital_course = db.Column(db.Text)
    labs_and_imaging = db.Column(db.Text)
    discharge_medications = db.Column(db.Text)
    discharge_instructions = db.Column(db.Text)
    allergies = db.Column(db.Text)
    code_status = db.Column(db.String(120))
    physician_name = db.Column(db.String(255))
    signed_datetime = db.Column(db.String(120))
    raw_ocr_text = db.Column(db.Text)
    extraction_confidence = db.Column(db.Float, default=0.0)
    extraction_status = db.Column(db.String(40), default="pending", index=True)
    source_file_name = db.Column(db.String(255))
    source_file_type = db.Column(db.String(20))
    billing_items = db.Column(db.JSON)
    total_billed_charges = db.Column(db.Float)
    insurance_adjustments = db.Column(db.Float)
    patient_amount_due = db.Column(db.Float)
    barcode_value = db.Column(db.String(255))
    structured_json = db.Column(db.JSON)
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

    document = db.relationship("Document", back_populates="medical_record")

    EDITABLE_FIELDS = [
        "document_type",
        "hospital_name",
        "hospital_address",
        "hospital_phone",
        "hospital_npi",
        "patient_name",
        "mrn",
        "guarantor_no",
        "dob",
        "statement_date",
        "primary_insurance",
        "group_no",
        "chief_complaint",
        "admission_diagnosis",
        "primary_diagnosis",
        "icd10_code",
        "hospital_course",
        "labs_and_imaging",
        "discharge_medications",
        "discharge_instructions",
        "allergies",
        "code_status",
        "physician_name",
        "signed_datetime",
        "total_billed_charges",
        "insurance_adjustments",
        "patient_amount_due",
        "barcode_value",
        "extraction_confidence",
        "extraction_status",
    ]

    def to_dict(self):
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "hospital_name": self.hospital_name,
            "hospital_address": self.hospital_address,
            "hospital_phone": self.hospital_phone,
            "hospital_npi": self.hospital_npi,
            "patient_name": self.patient_name,
            "mrn": self.mrn,
            "guarantor_no": self.guarantor_no,
            "dob": self.dob,
            "statement_date": self.statement_date,
            "primary_insurance": self.primary_insurance,
            "group_no": self.group_no,
            "chief_complaint": self.chief_complaint,
            "admission_diagnosis": self.admission_diagnosis,
            "primary_diagnosis": self.primary_diagnosis,
            "icd10_code": self.icd10_code,
            "hospital_course": self.hospital_course,
            "labs_and_imaging": self.labs_and_imaging,
            "discharge_medications": self.discharge_medications,
            "discharge_instructions": self.discharge_instructions,
            "allergies": self.allergies,
            "code_status": self.code_status,
            "physician_name": self.physician_name,
            "signed_datetime": self.signed_datetime,
            "raw_ocr_text": self.raw_ocr_text,
            "extraction_confidence": self.extraction_confidence,
            "extraction_status": self.extraction_status,
            "source_file_name": self.source_file_name,
            "source_file_type": self.source_file_type,
            "billing_items": self.billing_items,
            "total_billed_charges": self.total_billed_charges,
            "insurance_adjustments": self.insurance_adjustments,
            "patient_amount_due": self.patient_amount_due,
            "barcode_value": self.barcode_value,
            "structured_json": self.structured_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
