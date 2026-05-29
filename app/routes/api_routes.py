from flask import Blueprint, current_app, jsonify, request

from app.models import MedicalRecord
from app.repositories import DocumentRepository, MedicalRecordRepository
from app.services import AuditService, DashboardService, ExtractionService, FileService
from app.services.validation_service import ValidationService

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/upload")
def api_upload():
    file = request.files.get("file") or request.files.get("document")
    if not file:
        return jsonify({"error": "missing_file", "message": "Envie o campo file."}), 400

    try:
        file_info = FileService(current_app.config).save_upload(file)
    except ValueError as exc:
        return jsonify({"error": "invalid_file", "message": str(exc)}), 400
    document = DocumentRepository.create(status="pending", **file_info)
    AuditService.log("api_document_uploaded", "document", document.id, file_info)

    try:
        ExtractionService(current_app.config).process_document(document)
    except Exception as exc:
        return jsonify({"document": document.to_dict(include_record=True), "error": str(exc)}), 202

    return jsonify({"document": document.to_dict(include_record=True)}), 201


@api_bp.get("/documents")
def api_documents():
    documents = DocumentRepository.list_all(
        status=request.args.get("status"), query=request.args.get("q")
    )
    return jsonify([document.to_dict(include_record=True) for document in documents])


@api_bp.get("/documents/<int:document_id>")
def api_document_detail(document_id):
    document = DocumentRepository.get_or_404(document_id)
    return jsonify(document.to_dict(include_record=True))


@api_bp.delete("/documents/<int:document_id>")
def api_delete_document(document_id):
    document = DocumentRepository.get_or_404(document_id)
    FileService.delete_file(document.stored_file_path)
    DocumentRepository.delete(document)
    AuditService.log("api_document_deleted", "document", document_id)
    return jsonify({"status": "deleted", "document_id": document_id})


@api_bp.get("/records")
def api_records():
    records = MedicalRecordRepository.list_all(request.args)
    return jsonify([record.to_dict() for record in records])


@api_bp.get("/records/<int:record_id>")
def api_record_detail(record_id):
    record = MedicalRecordRepository.get_or_404(record_id)
    return jsonify(record.to_dict())


@api_bp.put("/records/<int:record_id>")
def api_update_record(record_id):
    record = MedicalRecordRepository.get_or_404(record_id)
    incoming = request.get_json(silent=True) or {}
    current = record.to_dict()
    for field in MedicalRecord.EDITABLE_FIELDS:
        if field in incoming:
            current[field] = incoming[field]
    validated = ValidationService.validate_medical_record(current)
    MedicalRecordRepository.update(record, **validated)
    AuditService.log("api_medical_record_updated", "medical_record", record.id, incoming)
    return jsonify(record.to_dict())


@api_bp.get("/dashboard/summary")
def api_dashboard_summary():
    return jsonify({"summary": DashboardService.summary(), "charts": DashboardService.charts()})
