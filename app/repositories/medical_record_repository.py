from sqlalchemy import func, or_

from app.extensions import db
from app.models import MedicalRecord


class MedicalRecordRepository:
    @staticmethod
    def create(**kwargs):
        record = MedicalRecord(**kwargs)
        db.session.add(record)
        db.session.commit()
        return record

    @staticmethod
    def get(record_id):
        return MedicalRecord.query.get(record_id)

    @staticmethod
    def get_or_404(record_id):
        return MedicalRecord.query.get_or_404(record_id)

    @staticmethod
    def list_all(filters=None):
        filters = filters or {}
        query = MedicalRecord.query

        patient = filters.get("patient")
        hospital = filters.get("hospital")
        icd = filters.get("icd")
        diagnosis = filters.get("diagnosis")
        status = filters.get("status")
        q = filters.get("q")

        if patient:
            query = query.filter(MedicalRecord.patient_name.ilike(f"%{patient}%"))
        if hospital:
            query = query.filter(MedicalRecord.hospital_name.ilike(f"%{hospital}%"))
        if icd:
            query = query.filter(MedicalRecord.icd10_code.ilike(f"%{icd}%"))
        if diagnosis:
            query = query.filter(
                or_(
                    MedicalRecord.admission_diagnosis.ilike(f"%{diagnosis}%"),
                    MedicalRecord.primary_diagnosis.ilike(f"%{diagnosis}%"),
                )
            )
        if status:
            query = query.filter(MedicalRecord.extraction_status == status)
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    MedicalRecord.patient_name.ilike(like),
                    MedicalRecord.hospital_name.ilike(like),
                    MedicalRecord.guarantor_no.ilike(like),
                    MedicalRecord.primary_insurance.ilike(like),
                    MedicalRecord.icd10_code.ilike(like),
                    MedicalRecord.admission_diagnosis.ilike(like),
                    MedicalRecord.primary_diagnosis.ilike(like),
                )
            )

        return query.order_by(MedicalRecord.created_at.desc()).all()

    @staticmethod
    def update(record, **kwargs):
        for key, value in kwargs.items():
            setattr(record, key, value)
        structured = record.to_dict()
        structured.pop("structured_json", None)
        record.structured_json = structured
        db.session.commit()
        return record

    @staticmethod
    def count_distinct(field_name):
        field = getattr(MedicalRecord, field_name)
        return db.session.query(func.count(func.distinct(field))).filter(
            field.isnot(None), field != ""
        ).scalar()

    @staticmethod
    def top_values(field_name, limit=8):
        field = getattr(MedicalRecord, field_name)
        rows = (
            db.session.query(field, func.count(MedicalRecord.id))
            .filter(field.isnot(None), field != "")
            .group_by(field)
            .order_by(func.count(MedicalRecord.id).desc())
            .limit(limit)
            .all()
        )
        return [{"label": value, "count": count} for value, count in rows]
