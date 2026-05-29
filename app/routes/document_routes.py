import mimetypes
from io import BytesIO
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from app.repositories import DocumentRepository
from app.services import AuditService, ExtractionService, FileService

document_bp = Blueprint("document", __name__, url_prefix="/documents")


@document_bp.get("/")
def list_documents():
    documents = DocumentRepository.list_all(
        status=request.args.get("status"), query=request.args.get("q")
    )
    return render_template("documents.html", documents=documents)


@document_bp.get("/<int:document_id>")
def detail(document_id):
    document = DocumentRepository.get_or_404(document_id)
    return render_template("document_detail.html", document=document)


@document_bp.get("/<int:document_id>/preview")
def preview(document_id):
    document = DocumentRepository.get_or_404(document_id)
    file_path = Path(document.stored_file_path)
    if not file_path.exists() or not file_path.is_file():
        abort(404)

    if document.file_type == "pdf":
        return _send_pdf_preview(file_path)

    mimetype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    return send_file(file_path, mimetype=mimetype)


def _send_pdf_preview(file_path):
    try:
        import fitz

        document = fitz.open(file_path)
        if document.page_count == 0:
            abort(404)
        page = document.load_page(0)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        payload = pixmap.tobytes("png")
        document.close()
    except Exception:
        current_app.logger.exception("pdf_preview_failed")
        abort(404)

    return send_file(BytesIO(payload), mimetype="image/png")


@document_bp.post("/<int:document_id>/ai-correction")
def ai_correction(document_id):
    document = DocumentRepository.get_or_404(document_id)
    try:
        record = ExtractionService(current_app.config).correct_with_ai(document)
        flash(
            f"Correcao com IA concluida. Confianca atual: {record.extraction_confidence * 100:.0f}%.",
            "success",
        )
    except RuntimeError as exc:
        flash(str(exc), "warning")
    except Exception as exc:
        current_app.logger.exception("document_ai_correction_failed")
        flash(f"Falha na correcao com IA: {exc}", "warning")

    return redirect(request.referrer or url_for("document.list_documents"))


@document_bp.post("/<int:document_id>/delete")
def delete(document_id):
    document = DocumentRepository.get_or_404(document_id)
    source_file_name = document.source_file_name
    FileService.delete_file(document.stored_file_path)
    DocumentRepository.delete(document)
    AuditService.log("document_deleted", "document", document_id, {"file": source_file_name})
    flash("Documento excluido com sucesso.", "success")
    return redirect(url_for("document.list_documents"))
