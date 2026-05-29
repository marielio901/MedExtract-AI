import json
import logging
from pathlib import Path

from flask import Flask, jsonify, render_template
from sqlalchemy import inspect, text

from app.config import config_by_name
from app.extensions import csrf, db, migrate
from app.routes import api_bp, crud_bp, dashboard_bp, document_bp, upload_bp


def create_app(config_name="development"):
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    _ensure_directories(app)
    _configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    csrf.exempt(api_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(document_bp)
    app.register_blueprint(crud_bp)
    app.register_blueprint(api_bp)

    register_error_handlers(app)
    register_cli(app)
    register_healthcheck(app)

    if not app.testing and app.config["ENABLE_BACKGROUND_WORKER"]:
        from app.services.batch_processing_service import BatchProcessingService
        BatchProcessingService.initialize(app)

    return app


def _ensure_directories(app):
    for key in ("UPLOAD_ORIGINAL_FOLDER",):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)


def _configure_logging(app):
    root = logging.getLogger()
    root.setLevel(getattr(logging, app.config["LOG_LEVEL"], logging.INFO))
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredLogFormatter())
        root.addHandler(handler)


class StructuredLogFormatter(logging.Formatter):
    RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    def format(self, record):
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
        }
        for key, value in record.__dict__.items():
            if key not in self.RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        if _wants_json():
            return jsonify({"error": "not_found", "message": "Recurso nao encontrado."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(error):
        if _wants_json():
            return jsonify({"error": "file_too_large", "message": "Arquivo muito grande."}), 413
        return render_template("errors/500.html", message="Arquivo muito grande."), 413

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if _wants_json():
            return jsonify({"error": "internal_error", "message": "Erro interno."}), 500
        return render_template("errors/500.html"), 500


def register_healthcheck(app):
    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"}), 200


def _wants_json():
    from flask import request

    return request.path.startswith("/api/") or (
        request.accept_mimetypes["application/json"]
        >= request.accept_mimetypes["text/html"]
    )


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        db.create_all()
        _sync_sqlite_schema()
        print("Banco SQLite inicializado.")


def _sync_sqlite_schema():
    if db.engine.url.get_backend_name() != "sqlite":
        return

    inspector = inspect(db.engine)
    if "medical_records" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("medical_records")
    }
    columns = {
        "document_type": "VARCHAR(80)",
        "hospital_address": "VARCHAR(500)",
        "hospital_phone": "VARCHAR(80)",
        "hospital_npi": "VARCHAR(80)",
        "guarantor_no": "VARCHAR(120)",
        "statement_date": "VARCHAR(50)",
        "primary_insurance": "VARCHAR(255)",
        "group_no": "VARCHAR(120)",
        "primary_diagnosis": "TEXT",
        "billing_items": "JSON",
        "total_billed_charges": "FLOAT",
        "insurance_adjustments": "FLOAT",
        "patient_amount_due": "FLOAT",
        "barcode_value": "VARCHAR(255)",
    }

    for name, definition in columns.items():
        if name not in existing_columns:
            db.session.execute(
                text(f"ALTER TABLE medical_records ADD COLUMN {name} {definition}")
            )
    _backfill_billing_statement_records()
    db.session.commit()


def _backfill_billing_statement_records():
    db.session.execute(
        text(
            "UPDATE medical_records SET document_type = 'billing_statement' "
            "WHERE billing_items IS NOT NULL OR patient_amount_due IS NOT NULL"
        )
    )
    db.session.execute(
        text(
            """
            UPDATE medical_records
            SET patient_amount_due = ROUND(total_billed_charges + insurance_adjustments, 2)
            WHERE document_type = 'billing_statement'
              AND patient_amount_due IS NULL
              AND total_billed_charges IS NOT NULL
              AND insurance_adjustments IS NOT NULL
            """
        )
    )
    db.session.execute(
        text(
            """
            UPDATE medical_records
            SET extraction_confidence = CASE
                    WHEN COALESCE(extraction_confidence, 0) < 1.0 THEN 1.0
                    ELSE extraction_confidence
                END,
                extraction_status = 'validated'
            WHERE document_type = 'billing_statement'
              AND hospital_name IS NOT NULL
              AND patient_name IS NOT NULL
              AND guarantor_no IS NOT NULL
              AND statement_date IS NOT NULL
              AND primary_insurance IS NOT NULL
              AND (primary_diagnosis IS NOT NULL OR admission_diagnosis IS NOT NULL)
              AND icd10_code IS NOT NULL
              AND billing_items IS NOT NULL
              AND total_billed_charges IS NOT NULL
              AND patient_amount_due IS NOT NULL
            """
        )
    )
    db.session.execute(
        text(
            """
            UPDATE documents
            SET extraction_confidence = (
                    SELECT medical_records.extraction_confidence
                    FROM medical_records
                    WHERE medical_records.document_id = documents.id
                ),
                status = CASE
                    WHEN (
                        SELECT medical_records.extraction_status
                        FROM medical_records
                        WHERE medical_records.document_id = documents.id
                    ) = 'validated' THEN 'processed'
                    ELSE status
                END
            WHERE EXISTS (
                SELECT 1
                FROM medical_records
                WHERE medical_records.document_id = documents.id
                  AND medical_records.document_type = 'billing_statement'
            )
            """
        )
    )
