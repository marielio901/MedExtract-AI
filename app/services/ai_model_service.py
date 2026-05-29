import base64
from io import BytesIO
import json
import logging
import mimetypes
from pathlib import Path
import re
import time

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "Voce e um extrator de dados medicos. Recebera texto OCR bruto de documentos "
    "clinicos, demonstrativos hospitalares e contas medicas. Extraia apenas os "
    "campos solicitados e retorne somente JSON valido. "
    "Nao escreva explicacoes. Se nao encontrar um campo, retorne null."
)


FIELD_LIST = [
    "hospital_name",
    "hospital_address",
    "hospital_phone",
    "hospital_npi",
    "patient_name",
    "mrn",
    "guarantor_no",
    "dob",
    "statement_date",
    "primary_insurance",
    "group_no",
    "chief_complaint",
    "admission_diagnosis",
    "primary_diagnosis",
    "icd10_code",
    "hospital_course",
    "labs_and_imaging",
    "discharge_medications",
    "discharge_instructions",
    "allergies",
    "code_status",
    "physician_name",
    "signed_datetime",
    "raw_ocr_text",
    "extraction_confidence",
    "extraction_status",
    "source_file_name",
    "source_file_type",
    "billing_items",
    "total_billed_charges",
    "insurance_adjustments",
    "patient_amount_due",
    "barcode_value",
]


class AIModelService:
    def __init__(self, config):
        self.config = config

    def _config_value(self, key, default=None):
        if hasattr(self.config, key):
            return getattr(self.config, key)
        return self.config.get(key, default)

    @property
    def configured(self):
        return bool(self._config_value("OPENROUTER_API_KEY", ""))

    @property
    def enabled(self):
        return bool(self._config_value("AI_EXTRACTION_ENABLED", False)) and self.configured

    def extract_json(
        self,
        raw_text,
        source_file_name=None,
        source_file_type=None,
        retries=2,
        force=False,
    ):
        if not self.enabled and not (force and self.configured):
            logger.info("openrouter_not_configured")
            return None

        prompt = self._build_prompt(raw_text, source_file_name, source_file_type)
        last_error = None
        for attempt in range(1, retries + 2):
            try:
                response = self._invoke_model(prompt)
                payload = self._parse_json(response)
                logger.info(
                    "ai_extraction_success",
                    extra={
                        "model": self._config_value("OPENROUTER_MODEL"),
                        "attempt": attempt,
                    },
                )
                return payload
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ai_extraction_failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(min(attempt, 3))
        raise RuntimeError("Falha ao extrair JSON valido com IA.") from last_error

    def _invoke_model(self, prompt):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "LangChain/OpenAI provider nao esta instalado. Instale requirements.txt."
            ) from exc

        headers = {}
        http_referer = self._config_value("OPENROUTER_HTTP_REFERER", "")
        app_title = self._config_value("OPENROUTER_APP_TITLE", "")
        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if app_title:
            headers["X-Title"] = app_title

        chat = ChatOpenAI(
            api_key=self._config_value("OPENROUTER_API_KEY"),
            base_url=self._config_value("OPENROUTER_BASE_URL"),
            model=self._config_value("OPENROUTER_MODEL"),
            temperature=0,
            default_headers=headers or None,
        )
        result = chat.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)])
        return getattr(result, "content", result)

    @staticmethod
    def _build_prompt(raw_text, source_file_name, source_file_type):
        fields = "\n".join(f'- "{field}"' for field in FIELD_LIST)
        return f"""
Extraia os campos abaixo do texto OCR e retorne somente um objeto JSON valido.
Use strings, numeros ou null. Nao inclua markdown.
Para billing_items, use uma lista de objetos com date, cpt, description e charges.
Para valores monetarios, retorne numeros sem simbolo de moeda.

Campos:
{fields}

Metadados conhecidos:
source_file_name: {source_file_name}
source_file_type: {source_file_type}

Texto OCR:
{raw_text}
"""

    @staticmethod
    def _parse_json(content):
        if not content:
            raise ValueError("Resposta vazia da IA.")
        text = str(content).strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))

    def extract_json_from_images(
        self,
        raw_text,
        image_paths,
        source_file_name=None,
        source_file_type=None,
        retries=2,
        force=False,
    ):
        if not self.enabled and not (force and self.configured):
            logger.info("openrouter_not_configured")
            return None

        prompt = self._build_vision_prompt(raw_text, source_file_name, source_file_type)
        image_payloads = self._image_payloads(image_paths)
        if not image_payloads:
            return self.extract_json(
                raw_text,
                source_file_name=source_file_name,
                source_file_type=source_file_type,
                retries=retries,
                force=force,
            )

        last_error = None
        for attempt in range(1, retries + 2):
            try:
                response = self._invoke_vision_model(prompt, image_payloads)
                payload = self._parse_json(response)
                logger.info(
                    "ai_vision_extraction_success",
                    extra={
                        "model": self._config_value("OPENROUTER_VISION_MODEL"),
                        "attempt": attempt,
                        "images": len(image_payloads),
                    },
                )
                return payload
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ai_vision_extraction_failed",
                    extra={"attempt": attempt, "error": str(exc)},
                )
                time.sleep(min(attempt, 3))
        raise RuntimeError("Falha ao extrair JSON valido com IA visual.") from last_error

    def _invoke_vision_model(self, prompt, image_payloads):
        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise RuntimeError(
                "LangChain/OpenAI provider nao esta instalado. Instale requirements.txt."
            ) from exc

        headers = {}
        http_referer = self._config_value("OPENROUTER_HTTP_REFERER", "")
        app_title = self._config_value("OPENROUTER_APP_TITLE", "")
        if http_referer:
            headers["HTTP-Referer"] = http_referer
        if app_title:
            headers["X-Title"] = app_title

        chat = ChatOpenAI(
            api_key=self._config_value("OPENROUTER_API_KEY"),
            base_url=self._config_value("OPENROUTER_BASE_URL"),
            model=self._config_value("OPENROUTER_VISION_MODEL"),
            temperature=0,
            default_headers=headers or None,
        )
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": image_payload}}
            for image_payload in image_payloads
        )
        result = chat.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=content)])
        return getattr(result, "content", result)

    @staticmethod
    def _build_vision_prompt(raw_text, source_file_name, source_file_type):
        fields = "\n".join(f'- "{field}"' for field in FIELD_LIST)
        return f"""
Leia as imagens anexadas do documento e use o texto OCR bruto apenas como apoio.
Corrija erros de OCR, leia tabelas e retorne somente um objeto JSON valido.
Nao inclua markdown, comentarios ou explicacoes.
Para billing_items, retorne todos os itens visiveis como objetos com date, cpt, description e charges.
Para valores monetarios, retorne numeros sem simbolo de moeda.
Se houver conflito entre OCR e imagem, confie mais na imagem.

Campos:
{fields}

Metadados conhecidos:
source_file_name: {source_file_name}
source_file_type: {source_file_type}

Texto OCR de apoio:
{raw_text or ""}
"""

    def _image_payloads(self, image_paths):
        max_pages = int(self._config_value("AI_MAX_VISION_PAGES", 3) or 3)
        return [
            payload
            for payload in (
                self._image_to_data_url(path)
                for path in list(image_paths or [])[:max_pages]
            )
            if payload
        ]

    def _image_to_data_url(self, image_path):
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            return None

        try:
            from PIL import Image

            with Image.open(path) as image:
                image = image.convert("RGB")
                max_width = int(self._config_value("AI_VISION_MAX_WIDTH", 1400) or 1400)
                if image.width > max_width:
                    ratio = max_width / image.width
                    image = image.resize(
                        (max_width, max(1, int(image.height * ratio))),
                        Image.Resampling.LANCZOS,
                    )
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=88, optimize=True)
                encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
                return f"data:image/jpeg;base64,{encoded}"
        except Exception as exc:
            logger.warning("ai_image_encoding_failed", extra={"path": str(path), "error": str(exc)})
            mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{encoded}"
