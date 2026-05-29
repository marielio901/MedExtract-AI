import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MedicalRecordSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    document_type: str = "medical_record"
    hospital_name: str | None = None
    hospital_address: str | None = None
    hospital_phone: str | None = None
    hospital_npi: str | None = None
    patient_name: str | None = None
    mrn: str | None = None
    guarantor_no: str | None = None
    dob: str | None = None
    statement_date: str | None = None
    primary_insurance: str | None = None
    group_no: str | None = None
    chief_complaint: str | None = None
    admission_diagnosis: str | None = None
    primary_diagnosis: str | None = None
    icd10_code: str | None = None
    hospital_course: str | None = None
    labs_and_imaging: str | None = None
    discharge_medications: str | None = None
    discharge_instructions: str | None = None
    allergies: str | None = None
    code_status: str | None = None
    physician_name: str | None = None
    signed_datetime: str | None = None
    raw_ocr_text: str | None = None
    extraction_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    extraction_status: str = "pending"
    source_file_name: str | None = None
    source_file_type: str | None = None
    billing_items: list[dict[str, Any]] | None = None
    total_billed_charges: float | None = None
    insurance_adjustments: float | None = None
    patient_amount_due: float | None = None
    barcode_value: str | None = None

    @field_validator("extraction_confidence", mode="before")
    @classmethod
    def default_confidence(cls, value: Any):
        if value in (None, ""):
            return 0.0
        return value

    @field_validator(
        "total_billed_charges",
        "insurance_adjustments",
        "patient_amount_due",
        mode="before",
    )
    @classmethod
    def normalize_currency(cls, value: Any):
        if value in (None, ""):
            return None
        if isinstance(value, str):
            value = value.strip().replace("$", "").replace(",", "").replace(" ", "")
            if not value:
                return None
        return value

    @field_validator("billing_items", mode="before")
    @classmethod
    def normalize_billing_items(cls, value: Any):
        if value in (None, "", []):
            return None
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            normalized = []
            for item in value:
                if not isinstance(item, dict):
                    continue
                item = dict(item)
                charge = item.get("charges")
                if isinstance(charge, str):
                    charge = charge.strip().replace("$", "").replace(",", "")
                    item["charges"] = float(charge) if charge else None
                normalized.append(item)
            return normalized or None
        return value

    @field_validator("*", mode="before")
    @classmethod
    def normalize_empty_values(cls, value: Any):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("icd10_code")
    @classmethod
    def normalize_icd10(cls, value: str | None):
        if not value:
            return value
        value = value.upper()
        if re.match(r"^[1L][0-9]{2}(?:\..*)?$", value):
            return f"I{value[1:]}"
        return value
