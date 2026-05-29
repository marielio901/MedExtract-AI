from io import BytesIO, StringIO

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, send_file, url_for

from app.models import MedicalRecord
from app.repositories import MedicalRecordRepository
from app.services import AuditService, ValidationService

crud_bp = Blueprint("crud", __name__)


@crud_bp.get("/records")
def list_records():
    filters = {
        "patient": request.args.get("patient"),
        "hospital": request.args.get("hospital"),
        "icd": request.args.get("icd"),
        "diagnosis": request.args.get("diagnosis"),
        "status": request.args.get("status"),
        "q": request.args.get("q"),
    }
    records = MedicalRecordRepository.list_all(filters)
    return render_template("documents.html", records=records, show_records=True)


@crud_bp.route("/records/<int:record_id>/edit", methods=["GET", "POST"])
def edit_record(record_id):
    record = MedicalRecordRepository.get_or_404(record_id)
    if request.method == "POST":
        payload = {field: request.form.get(field) for field in MedicalRecord.EDITABLE_FIELDS}
        payload.update(
            {
                "raw_ocr_text": record.raw_ocr_text,
                "source_file_name": record.source_file_name,
                "source_file_type": record.source_file_type,
            }
        )
        validated = ValidationService.validate_medical_record(payload)
        MedicalRecordRepository.update(record, **validated)
        AuditService.log("medical_record_updated", "medical_record", record.id, validated)
        flash("Registro medico atualizado.", "success")
        return redirect(url_for("document.detail", document_id=record.document_id))

    return render_template("edit_record.html", record=record)


@crud_bp.get("/records/export.csv")
def export_csv():
    records = MedicalRecordRepository.list_all(request.args)
    output = StringIO()
    pd.DataFrame([record.to_dict() for record in records]).to_csv(output, index=False)
    payload = BytesIO(output.getvalue().encode("utf-8"))
    return send_file(
        payload,
        mimetype="text/csv",
        as_attachment=True,
        download_name="medextract_records.csv",
    )


@crud_bp.get("/records/export.xlsx")
def export_xlsx():
    records = MedicalRecordRepository.list_all(request.args)
    payload = BytesIO()
    with pd.ExcelWriter(payload, engine="openpyxl") as writer:
        pd.DataFrame([record.to_dict() for record in records]).to_excel(
            writer, index=False, sheet_name="records"
        )
    payload.seek(0)
    return send_file(
        payload,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="medextract_records.xlsx",
    )
