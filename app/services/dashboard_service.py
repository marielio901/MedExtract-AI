from sqlalchemy import func

from app.extensions import db
from app.models import Document, MedicalRecord
from app.repositories import MedicalRecordRepository


class DashboardService:
    @staticmethod
    def summary():
        total_documents = Document.query.count()
        processed_documents = Document.query.filter_by(status="processed").count()
        pending_documents = Document.query.filter_by(status="pending").count()
        error_documents = Document.query.filter_by(status="error").count()
        unique_patients = MedicalRecordRepository.count_distinct("patient_name") or 0
        hospitals_found = MedicalRecordRepository.count_distinct("hospital_name") or 0
        average_confidence = (
            db.session.query(func.avg(MedicalRecord.extraction_confidence)).scalar() or 0.0
        )

        return {
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "pending_documents": pending_documents,
            "error_documents": error_documents,
            "unique_patients": unique_patients,
            "hospitals_found": hospitals_found,
            "average_confidence": round(float(average_confidence), 3),
            "top_diagnoses": MedicalRecordRepository.top_values(
                "admission_diagnosis", limit=6
            ),
            "top_charges": DashboardService.top_charges(limit=8),
        }

    @staticmethod
    def charts():
        documents_by_month = (
            db.session.query(func.strftime("%Y-%m", Document.created_at), func.count(Document.id))
            .group_by(func.strftime("%Y-%m", Document.created_at))
            .order_by(func.strftime("%Y-%m", Document.created_at))
            .all()
        )
        documents_by_hospital = MedicalRecordRepository.top_values("hospital_name", limit=8)
        top_diagnoses = MedicalRecordRepository.top_values("admission_diagnosis", limit=8)
        top_charges = DashboardService.top_charges(limit=8)
        status_rows = (
            db.session.query(Document.status, func.count(Document.id))
            .group_by(Document.status)
            .all()
        )

        return {
            "documents_by_month": {
                "labels": [row[0] or "Sem data" for row in documents_by_month],
                "values": [row[1] for row in documents_by_month],
            },
            "documents_by_hospital": DashboardService._series(documents_by_hospital),
            "top_diagnoses": DashboardService._series(top_diagnoses),
            "top_medications": DashboardService._series(top_charges),
            "status": {
                "labels": [row[0] for row in status_rows],
                "values": [row[1] for row in status_rows],
            },
        }

    @staticmethod
    def recent_activity(limit=8):
        documents = Document.query.order_by(Document.created_at.desc()).limit(limit).all()
        return [
            {
                "title": document.source_file_name,
                "status": document.status,
                "created_at": document.created_at,
            }
            for document in documents
        ]

    @staticmethod
    def top_charges(limit=8):
        rows = MedicalRecord.query.with_entities(MedicalRecord.billing_items).all()
        totals = {}
        for (items,) in rows:
            for item in items or []:
                label = item.get("description") or item.get("cpt")
                if not label:
                    continue
                totals[label] = totals.get(label, 0) + 1
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [{"label": label, "count": count} for label, count in ranked]

    @staticmethod
    def _series(items):
        return {
            "labels": [item["label"] for item in items],
            "values": [item["count"] for item in items],
        }
