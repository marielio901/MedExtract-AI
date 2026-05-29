import logging
import re
import tempfile
from datetime import datetime, timezone

from pydantic import ValidationError

from app.extensions import db
from app.models import MedicalRecord
from app.repositories import DocumentRepository
from app.services.ai_model_service import AIModelService
from app.services.audit_service import AuditService
from app.services.billing_statement_cv_service import BillingStatementCVService
from app.services.image_preprocessing_service import ImagePreprocessingService
from app.services.ocr_service import OCRService
from app.services.pdf_service import PDFService
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)


class ExtractionService:
    CRITICAL_FIELDS = ["patient_name", "hospital_name", "admission_diagnosis"]
    BILLING_CRITICAL_FIELDS = [
        "hospital_name",
        "patient_name",
        "guarantor_no",
        "statement_date",
        "primary_insurance",
        "primary_diagnosis",
        "icd10_code",
        "billing_items",
        "total_billed_charges",
        "patient_amount_due",
    ]

    def __init__(self, config):
        self.config = config
        processed_folder = self._config_value("UPLOAD_PROCESSED_FOLDER")
        self.pdf_service = PDFService(processed_folder)
        self.preprocessing_service = ImagePreprocessingService(processed_folder)
        self.ocr_service = OCRService(
            lang=self._config_value("OCR_LANG"), use_gpu=self._config_value("OCR_USE_GPU")
        )
        self.cv_bill_service = BillingStatementCVService(
            processed_folder, self.ocr_service
        )
        self.ai_service = AIModelService(config)

    def _config_value(self, key):
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return self.config[key]

    def process_document(self, document):
        try:
            with tempfile.TemporaryDirectory(prefix="medextract-") as work_dir:
                image_paths = self._prepare_images(document, work_dir)
                cv_payload = self._extract_cv_bill_payload(image_paths, work_dir)
                if cv_payload:
                    raw_text = self._payload_to_raw_text(cv_payload)
                    ocr_confidence = 0.92
                    barcode_value = cv_payload.get("barcode_value")
                else:
                    processed_paths = [
                        self.preprocessing_service.preprocess(path, work_dir)
                        for path in image_paths
                    ]
                    raw_text, ocr_confidence = self.ocr_service.extract_text(processed_paths)
                    barcode_value = self._extract_barcode_value(processed_paths)
                payload = self.extract_structured_data(
                    raw_text=raw_text,
                    source_file_name=document.source_file_name,
                    source_file_type=document.file_type,
                    ocr_confidence=ocr_confidence,
                    barcode_value=barcode_value,
                    cv_payload=cv_payload,
                    image_paths=image_paths,
                )

            record = self._upsert_record(document, payload)
            DocumentRepository.update(
                document,
                status="processed",
                raw_ocr_text=raw_text,
                extraction_confidence=record.extraction_confidence,
                processed_at=datetime.now(timezone.utc),
                error_message=None,
            )
            AuditService.log(
                "document_processed",
                "document",
                document.id,
                {"record_id": record.id, "confidence": record.extraction_confidence},
            )
            return record
        except Exception as exc:
            logger.exception("document_processing_failed", extra={"document_id": document.id})
            DocumentRepository.update(document, status="error", error_message=str(exc))
            AuditService.log(
                "document_processing_failed",
                "document",
                document.id,
                {"error": str(exc)},
            )
            raise

    def correct_with_ai(self, document):
        if not self.ai_service.configured:
            raise RuntimeError(
                "IA nao configurada. Defina OPENROUTER_API_KEY para usar a correcao com IA."
            )

        with tempfile.TemporaryDirectory(prefix="medextract-ai-") as work_dir:
            image_paths = self._prepare_images(document, work_dir)
            raw_text, ocr_confidence, barcode_value, cv_payload = self._text_for_ai_correction(
                document, image_paths, work_dir
            )
            base_payload = self._regex_extract(raw_text)

            if document.medical_record:
                existing_payload = {
                    key: value
                    for key, value in document.medical_record.to_dict().items()
                    if key
                    not in {
                        "id",
                        "document_id",
                        "extraction_confidence",
                        "extraction_status",
                        "structured_json",
                        "created_at",
                        "updated_at",
                    }
                }
                base_payload = self._merge_payloads(base_payload, existing_payload)

            base_payload = self._merge_payloads(base_payload, cv_payload or {})
            if barcode_value and not base_payload.get("barcode_value"):
                base_payload["barcode_value"] = barcode_value

            ai_payload = self.ai_service.extract_json_from_images(
                raw_text,
                image_paths,
                source_file_name=document.source_file_name,
                source_file_type=document.file_type,
                force=True,
            )
            if not ai_payload:
                raise RuntimeError("A IA nao retornou dados para corrigir este documento.")

            payload = self._merge_payloads(base_payload, ai_payload)
            payload.update(
                {
                    "raw_ocr_text": raw_text,
                    "source_file_name": document.source_file_name,
                    "source_file_type": document.file_type,
                }
            )
            if barcode_value and not payload.get("barcode_value"):
                payload["barcode_value"] = barcode_value

            payload = self._normalize_payload(payload)
            payload["extraction_confidence"] = self._score_payload(
                payload, max(float(ocr_confidence or 0.0), 0.98)
            )
            payload["extraction_status"] = self._status_for_payload(payload)
            validated = ValidationService.validate_medical_record(payload)
        record = self._upsert_record(document, validated)
        DocumentRepository.update(
            document,
            status="processed",
            raw_ocr_text=raw_text,
            extraction_confidence=record.extraction_confidence,
            processed_at=datetime.now(timezone.utc),
            error_message=None,
        )
        AuditService.log(
            "document_ai_corrected",
            "document",
            document.id,
            {"record_id": record.id, "confidence": record.extraction_confidence},
        )
        return record

    def extract_structured_data(
        self,
        raw_text,
        source_file_name=None,
        source_file_type=None,
        ocr_confidence=0.0,
        barcode_value=None,
        cv_payload=None,
        image_paths=None,
    ):
        regex_payload = self._regex_extract(raw_text)
        regex_payload.update(
            {
                "raw_ocr_text": raw_text,
                "source_file_name": source_file_name,
                "source_file_type": source_file_type,
            }
        )
        if barcode_value:
            regex_payload["barcode_value"] = barcode_value
        regex_payload = self._merge_payloads(regex_payload, cv_payload or {})
        regex_payload["extraction_confidence"] = self._score_payload(
            regex_payload, ocr_confidence
        )
        regex_payload["extraction_status"] = self._status_for_payload(regex_payload)

        should_use_ai = (
            regex_payload["extraction_confidence"]
            < self._config_value("AI_CONFIDENCE_THRESHOLD")
            or regex_payload["extraction_status"] == "needs_review"
        )

        if should_use_ai and self.ai_service.enabled:
            try:
                if image_paths:
                    ai_payload = self.ai_service.extract_json_from_images(
                        raw_text,
                        image_paths,
                        source_file_name=source_file_name,
                        source_file_type=source_file_type,
                    )
                else:
                    ai_payload = self.ai_service.extract_json(
                        raw_text,
                        source_file_name=source_file_name,
                        source_file_type=source_file_type,
                    )
                merged = self._merge_payloads(regex_payload, ai_payload or {})
                merged["raw_ocr_text"] = raw_text
                merged["source_file_name"] = source_file_name
                merged["source_file_type"] = source_file_type
                merged["extraction_confidence"] = max(
                    float(merged.get("extraction_confidence") or 0.0),
                    min(1.0, regex_payload["extraction_confidence"] + 0.15),
                )
                if barcode_value and not merged.get("barcode_value"):
                    merged["barcode_value"] = barcode_value
                merged["extraction_status"] = self._status_for_payload(merged)
                merged = self._normalize_payload(merged)
                return ValidationService.validate_medical_record(merged)
            except (ValidationError, RuntimeError, ValueError) as exc:
                logger.warning("ai_payload_rejected", extra={"error": str(exc)})

        return ValidationService.validate_medical_record(regex_payload)

    def _prepare_images(self, document, output_dir):
        if document.file_type == "pdf":
            return self.pdf_service.convert_to_images(
                document.stored_file_path, output_dir=output_dir
            )
        return [document.stored_file_path]

    def _extract_cv_bill_payload(self, image_paths, output_dir):
        if not self._config_value("CV_BILL_EXTRACTION_ENABLED"):
            return {}
        try:
            return self.cv_bill_service.extract(image_paths, output_dir=output_dir)
        except Exception as exc:
            logger.warning("cv_bill_extraction_failed", extra={"error": str(exc)})
            return {}

    def _text_for_ai_correction(self, document, image_paths, output_dir):
        if document.raw_ocr_text:
            return (
                document.raw_ocr_text,
                float(document.extraction_confidence or 0.0),
                document.medical_record.barcode_value if document.medical_record else None,
                {},
            )

        cv_payload = self._extract_cv_bill_payload(image_paths, output_dir)
        if cv_payload:
            return (
                self._payload_to_raw_text(cv_payload),
                0.92,
                cv_payload.get("barcode_value"),
                cv_payload,
            )

        processed_paths = [
            self.preprocessing_service.preprocess(path, output_dir)
            for path in image_paths
        ]
        raw_text, ocr_confidence = self.ocr_service.extract_text(processed_paths)
        barcode_value = self._extract_barcode_value(processed_paths)
        return raw_text, ocr_confidence, barcode_value, {}

    @staticmethod
    def _payload_to_raw_text(payload):
        lines = []
        for key, value in (payload or {}).items():
            if key == "billing_items" and value:
                lines.append("Billing Items:")
                for item in value:
                    lines.append(
                        "{date} {cpt} {description} ${charges:.2f}".format(
                            date=item.get("date", ""),
                            cpt=item.get("cpt", ""),
                            description=item.get("description", ""),
                            charges=float(item.get("charges") or 0),
                        )
                    )
            elif value not in (None, "", [], {}):
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _extract_barcode_value(image_paths):
        try:
            import cv2
        except ImportError:
            return None

        detector_class = getattr(cv2, "barcode_BarcodeDetector", None)
        if detector_class is None:
            return None

        detector = detector_class()
        for path in image_paths:
            image = cv2.imread(str(path))
            if image is None:
                continue
            try:
                decoded = detector.detectAndDecode(image)
            except Exception:
                continue

            value = ExtractionService._first_decoded_barcode(decoded)
            if value:
                return value[:255]
        return None

    @staticmethod
    def _first_decoded_barcode(decoded):
        if isinstance(decoded, str):
            return decoded.strip() or None
        if isinstance(decoded, (list, tuple)):
            for item in decoded:
                value = ExtractionService._first_decoded_barcode(item)
                if value:
                    return value
        return None

    @staticmethod
    def _regex_extract(raw_text):
        text = raw_text or ""
        primary_diagnosis = ExtractionService._match(
            text,
            [
                r"(?:primary diagnosis|diagnostico principal)\s*[:\-]\s*(.+)",
                r"(?:admission diagnosis|diagnosis|diagnostico de admissao)\s*[:\-]\s*(.+)",
            ],
        )
        payload = {
            "document_type": "medical_record",
            "hospital_name": ExtractionService._match(
                text,
                [
                    r"(?:hospital|facility|medical center|clinica|clinic)\s*[:\-]\s*(.+)",
                    r"^(.*(?:hospital|medical center|clinic|clinica).*)$",
                ],
            ),
            "hospital_address": ExtractionService._hospital_address(text),
            "hospital_phone": ExtractionService._match(
                text,
                [r"(?:phone|telefone|tel)\s*[:#\-]\s*([\(\)\d\s.+-]{7,})"],
            ),
            "hospital_npi": ExtractionService._match(
                text, [r"(?:npi)\s*[:#\-]\s*([A-Z0-9\-]+)"]
            ),
            "patient_name": ExtractionService._match(
                text,
                [
                    r"(?:patient|patient name|nome do paciente)\s*[:\-]\s*(.+)",
                    r"(?:name|nome)\s*[:\-]\s*([A-Z][A-Za-z ,.'-]{3,})",
                ],
            ),
            "mrn": ExtractionService._match(
                text, [r"(?:mrn|medical record number|prontuario)\s*[:#\-]\s*([A-Z0-9\-]+)"]
            ),
            "guarantor_no": ExtractionService._match(
                text,
                [r"(?:guarantor no|guarantor number|account no|account number)\s*[:#\-]\s*([A-Z0-9\-]+)"],
            ),
            "dob": ExtractionService._match(
                text,
                [
                    r"(?:dob|date of birth|data de nascimento|nascimento)\s*[:\-]\s*([0-9]{1,4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,4})"
                ],
            ),
            "statement_date": ExtractionService._match(
                text,
                [r"(?:statement date|data do demonstrativo)\s*[:\-]\s*([0-9]{1,4}[\/\-][0-9]{1,2}[\/\-][0-9]{1,4})"],
            ),
            "primary_insurance": ExtractionService._match(
                text, [r"(?:primary insurance|insurance|convenio|seguro)\s*[:\-]\s*(.+)"]
            ),
            "group_no": ExtractionService._match(
                text, [r"(?:group no|group number|grupo)\s*[:#\-]\s*([A-Z0-9\-]+)"]
            ),
            "chief_complaint": ExtractionService._section(
                text, ["chief complaint", "queixa principal"]
            ),
            "admission_diagnosis": primary_diagnosis
            or ExtractionService._section(
                text, ["admission diagnosis", "diagnosis", "diagnostico de admissao"]
            ),
            "primary_diagnosis": primary_diagnosis,
            "icd10_code": ExtractionService._match(
                text,
                [
                    r"(?:icd-?10(?: code)?|cid-?10)\s*[:#\-]\s*([A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?)",
                    r"\b([A-TV-Z][0-9][0-9AB](?:\.[0-9A-TV-Z]{1,4})?)\b",
                ],
            ),
            "hospital_course": ExtractionService._section(
                text, ["hospital course", "clinical course", "evolucao hospitalar"]
            ),
            "labs_and_imaging": ExtractionService._section(
                text, ["labs and imaging", "laboratory", "imaging", "exames"]
            ),
            "discharge_medications": ExtractionService._section(
                text, ["discharge medications", "medications", "medicamentos"]
            ),
            "discharge_instructions": ExtractionService._section(
                text, ["discharge instructions", "instructions", "instrucoes de alta"]
            ),
            "allergies": ExtractionService._match(
                text, [r"(?:allergies|alergias)\s*[:\-]\s*(.+)"]
            ),
            "code_status": ExtractionService._match(
                text, [r"(?:code status|status do codigo)\s*[:\-]\s*(.+)"]
            ),
            "physician_name": ExtractionService._match(
                text,
                [
                    r"(?:physician|doctor|provider|medico)\s*[:\-]\s*(.+)",
                    r"(?:signed by|assinado por)\s*[:\-]\s*(.+)",
                ],
            ),
            "signed_datetime": ExtractionService._match(
                text,
                [
                    r"(?:signed|assinado)\s*(?:date|datetime|em)?\s*[:\-]\s*(.+)",
                    r"(?:signature date)\s*[:\-]\s*(.+)",
                ],
            ),
            "billing_items": ExtractionService._billing_items(text),
            "total_billed_charges": ExtractionService._money(
                text, ["total billed charges", "total charges", "total cobrado"]
            ),
            "insurance_adjustments": ExtractionService._money(
                text, ["insurance adjustments", "insurance adjustment", "ajustes do convenio"]
            ),
            "patient_amount_due": ExtractionService._money(
                text, ["patient amount due", "amount due", "valor devido pelo paciente"]
            ),
            "barcode_value": ExtractionService._match(
                text, [r"(?:barcode|codigo de barras)\s*[:#\-]\s*([A-Z0-9\- ]{6,})"]
            ),
        }
        return ExtractionService._normalize_payload(payload)

    @staticmethod
    def _normalize_payload(payload):
        if payload.get("billing_items") or payload.get("patient_amount_due") is not None:
            payload["document_type"] = "billing_statement"
        if (
            payload.get("document_type") == "billing_statement"
            and payload.get("patient_amount_due") is None
            and payload.get("total_billed_charges") is not None
            and payload.get("insurance_adjustments") is not None
        ):
            payload["patient_amount_due"] = round(
                float(payload["total_billed_charges"])
                + float(payload["insurance_adjustments"]),
                2,
            )
        if payload.get("primary_diagnosis") and not payload.get("admission_diagnosis"):
            payload["admission_diagnosis"] = payload["primary_diagnosis"]
        if payload.get("admission_diagnosis") and not payload.get("primary_diagnosis"):
            payload["primary_diagnosis"] = payload["admission_diagnosis"]
        return payload

    @staticmethod
    def _match(text, patterns):
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip(" \t\r\n:;-")
                return value[:1000] if value else None
        return None

    @staticmethod
    def _section(text, headings):
        heading_pattern = "|".join(re.escape(heading) for heading in headings)
        known_headings = (
            "chief complaint|admission diagnosis|diagnosis|hospital course|labs and imaging|"
            "laboratory|imaging|discharge medications|medications|discharge instructions|"
            "instructions|allergies|code status|physician|signed|queixa principal|"
            "diagnostico|evolucao hospitalar|exames|medicamentos|instrucoes de alta|alergias"
        )
        pattern = rf"(?:{heading_pattern})\s*[:\-]?\s*(.*?)(?=\n\s*(?:{known_headings})\s*[:\-]|\Z)"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        value = re.sub(r"\s+", " ", match.group(1)).strip(" \t\r\n:;-")
        return value[:4000] if value else None

    @staticmethod
    def _hospital_address(text):
        lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
        for index, line in enumerate(lines):
            if re.search(r"\b(hospital|medical center|clinic|clinica)\b", line, re.I):
                for candidate in lines[index + 1 : index + 4]:
                    if re.search(r"\b(npi|phone|patient|statement|account)\b", candidate, re.I):
                        continue
                    if "," in candidate or re.search(r"\d{4,}", candidate):
                        return candidate[:500]
        return None

    @staticmethod
    def _money(text, labels):
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(
            rf"(?:{label_pattern})[\s\S]{{0,120}}?(-?\$?\s*[0-9][0-9,]*(?:\.[0-9]{{2}})?)",
            text or "",
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        value = match.group(1).replace("$", "").replace(",", "").replace(" ", "")
        return float(value)

    @staticmethod
    def _billing_items(text):
        items = []
        pattern = re.compile(
            r"^\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+([A-Z0-9]{2,8})\s+(.+?)\s+\$?\s*([0-9][0-9,]*(?:\.[0-9]{2}))\s*$",
            flags=re.IGNORECASE | re.MULTILINE,
        )
        for match in pattern.finditer(text or ""):
            description = re.sub(r"\s+", " ", match.group(3)).strip(" -")
            items.append(
                {
                    "date": match.group(1),
                    "cpt": match.group(2),
                    "description": description,
                    "charges": float(match.group(4).replace(",", "")),
                }
            )
        if items:
            return items
        return ExtractionService._billing_items_from_split_lines(text)

    @staticmethod
    def _billing_items_from_split_lines(text):
        lines = [
            line.strip()
            for line in (text or "").splitlines()
            if line.strip() and not re.search(r"^(date|cpt|description|charges)$", line, re.I)
        ]
        items = []
        index = 0
        while index < len(lines):
            if not re.match(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$", lines[index]):
                index += 1
                continue
            if index + 2 >= len(lines):
                break

            date = lines[index]
            cpt = lines[index + 1]
            if not re.match(r"^[A-Z0-9]{2,8}$", cpt, re.I):
                index += 1
                continue

            description_parts = []
            cursor = index + 2
            amount = None
            while cursor < len(lines):
                amount_match = re.search(
                    r"^\$?\s*([0-9][0-9,]*(?:\.[0-9]{2}))$", lines[cursor]
                )
                if amount_match:
                    amount = float(amount_match.group(1).replace(",", ""))
                    break
                if re.search(r"total billed|insurance adjustments|patient amount", lines[cursor], re.I):
                    break
                description_parts.append(lines[cursor])
                cursor += 1

            if amount is not None and description_parts:
                items.append(
                    {
                        "date": date,
                        "cpt": cpt,
                        "description": " ".join(description_parts),
                        "charges": amount,
                    }
                )
                index = cursor + 1
                continue
            index += 1

        return items or None

    def _score_payload(self, payload, ocr_confidence):
        if payload.get("document_type") == "billing_statement":
            return self._score_billing_payload(payload, ocr_confidence)

        populated = sum(1 for key in self.CRITICAL_FIELDS if payload.get(key))
        optional_keys = [
            "mrn",
            "guarantor_no",
            "dob",
            "icd10_code",
            "primary_insurance",
            "patient_amount_due",
            "discharge_medications",
            "physician_name",
        ]
        optional = sum(1 for key in optional_keys if payload.get(key))
        structure_score = (populated / len(self.CRITICAL_FIELDS)) * 0.65 + (
            optional / len(optional_keys)
        ) * 0.25
        return round(min(1.0, structure_score + (float(ocr_confidence or 0) * 0.10)), 3)

    def _score_billing_payload(self, payload, ocr_confidence):
        missing = [key for key in self.BILLING_CRITICAL_FIELDS if not payload.get(key)]
        if not missing and self._billing_totals_are_consistent(payload):
            return 1.0

        populated = len(self.BILLING_CRITICAL_FIELDS) - len(missing)
        optional_keys = [
            "hospital_address",
            "hospital_phone",
            "hospital_npi",
            "group_no",
            "insurance_adjustments",
            "barcode_value",
        ]
        optional = sum(1 for key in optional_keys if payload.get(key) not in (None, "", []))
        structure_score = (populated / len(self.BILLING_CRITICAL_FIELDS)) * 0.82 + (
            optional / len(optional_keys)
        ) * 0.12
        return round(min(1.0, structure_score + (float(ocr_confidence or 0) * 0.06)), 3)

    @staticmethod
    def _billing_totals_are_consistent(payload):
        try:
            total = float(payload.get("total_billed_charges"))
            due = float(payload.get("patient_amount_due"))
            items = payload.get("billing_items") or []

            if items:
                items_total = sum(float(item.get("charges") or 0) for item in items)
                if abs(items_total - total) > 0.05:
                    return False

            adjustment = payload.get("insurance_adjustments")
            if adjustment is not None and abs(total + float(adjustment) - due) > 0.05:
                return False
        except (TypeError, ValueError, AttributeError):
            return False

        return True

    def _status_for_payload(self, payload):
        if payload.get("document_type") == "billing_statement":
            missing = [
                field for field in self.BILLING_CRITICAL_FIELDS if not payload.get(field)
            ]
            if missing:
                return "needs_review"
            if float(payload.get("extraction_confidence") or 0) < 0.90:
                return "needs_review"
            return "validated"

        missing_critical = [field for field in self.CRITICAL_FIELDS if not payload.get(field)]
        if missing_critical:
            return "needs_review"
        if float(payload.get("extraction_confidence") or 0) < self._config_value(
            "AI_CONFIDENCE_THRESHOLD"
        ):
            return "needs_review"
        return "validated"

    @staticmethod
    def _merge_payloads(base, override):
        merged = dict(base)
        for key, value in (override or {}).items():
            if value not in (None, "", [], {}):
                merged[key] = value
        return merged

    @staticmethod
    def _upsert_record(document, payload):
        record = document.medical_record or MedicalRecord(document_id=document.id)
        for key, value in payload.items():
            if hasattr(record, key):
                setattr(record, key, value)
        record.structured_json = payload
        db.session.add(record)
        db.session.commit()
        return record
