from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_wtf import FlaskForm
from wtforms import MultipleFileField, SubmitField

from app.repositories import DocumentRepository
from app.services import AuditService, FileService

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


class UploadForm(FlaskForm):
    document = MultipleFileField("Documentos medicos")
    submit = SubmitField("Processar documentos")


@upload_bp.route("/", methods=["GET", "POST"])
def upload_document():
    form = UploadForm()
    if form.validate_on_submit():
        files = request.files.getlist("document")
        files = [f for f in files if f and f.filename]

        if not files:
            flash("Por favor, selecione pelo menos um arquivo para upload.", "danger")
            return render_template("upload.html", form=form)

        file_service = FileService(current_app.config)
        success_count = 0
        error_count = 0

        from app.services.batch_processing_service import BatchProcessingService

        for file in files:
            try:
                file_info = file_service.save_upload(file)
                document = DocumentRepository.create(status="pending", **file_info)
                AuditService.log("document_uploaded", "document", document.id, file_info)

                if current_app.config["ENABLE_BACKGROUND_WORKER"]:
                    BatchProcessingService.queue_document(document.id)
                success_count += 1
            except Exception as exc:
                current_app.logger.exception(f"Falha ao salvar o upload de {file.filename}: {exc}")
                error_count += 1

        if success_count > 0:
            if error_count > 0:
                flash(
                    f"{success_count} documentos importados com sucesso para processamento em segundo plano. "
                    f"{error_count} arquivos falharam no upload.",
                    "warning",
                )
            else:
                flash(
                    f"{success_count} documentos importados com sucesso! O processamento está ocorrendo em segundo plano.",
                    "success",
                )
        elif error_count > 0:
            flash("Nenhum arquivo pôde ser importado. Verifique os formatos permitidos.", "danger")
            return render_template("upload.html", form=form)

        return redirect(url_for("document.list_documents"))

    return render_template("upload.html", form=form)
