import pytest
from pydantic import ValidationError

from app.schemas import MedicalRecordSchema


def test_medical_record_schema_normalizes_empty_strings():
    schema = MedicalRecordSchema(
        patient_name=" Jane Doe ",
        hospital_name="",
        extraction_confidence=0.8,
    )

    assert schema.patient_name == "Jane Doe"
    assert schema.hospital_name is None


def test_medical_record_schema_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        MedicalRecordSchema(patient_name="Jane Doe", extraction_confidence=1.5)


def test_medical_record_schema_normalizes_common_icd_ocr_confusion():
    schema = MedicalRecordSchema(icd10_code="110")

    assert schema.icd10_code == "I10"
