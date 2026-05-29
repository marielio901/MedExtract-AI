import logging
import os
from pathlib import Path
from statistics import mean

logger = logging.getLogger(__name__)


class OCRProcessingError(RuntimeError):
    pass


class OCRService:
    def __init__(self, lang="en", use_gpu=False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._engine = None

    @property
    def engine(self):
        if self._engine is None:
            try:
                cache_home = Path(__file__).resolve().parents[2] / ".paddlex-cache"
                cache_home.mkdir(parents=True, exist_ok=True)
                os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(cache_home))
                os.environ.setdefault("FLAGS_use_onednn", "0")
                os.environ.setdefault("FLAGS_use_mkldnn", "0")
                from paddleocr import PaddleOCR

                self._engine = self._create_engine(PaddleOCR)
            except Exception as exc:
                logger.exception("paddleocr_initialization_failed")
                raise OCRProcessingError(
                    "PaddleOCR nao esta disponivel ou falhou ao inicializar."
                ) from exc
        return self._engine

    def _create_engine(self, paddle_ocr_class):
        import inspect

        parameters = inspect.signature(paddle_ocr_class).parameters
        if "use_textline_orientation" in parameters:
            return paddle_ocr_class(
                text_detection_model_name=os.getenv(
                    "OCR_DETECTION_MODEL", "PP-OCRv5_mobile_det"
                ),
                text_recognition_model_name=os.getenv(
                    "OCR_RECOGNITION_MODEL", "en_PP-OCRv5_mobile_rec"
                ),
                use_textline_orientation=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                text_det_limit_side_len=int(os.getenv("OCR_DET_LIMIT_SIDE_LEN", "736")),
                text_det_limit_type="max",
                text_recognition_batch_size=1,
                device="cpu",
                enable_mkldnn=False,
                cpu_threads=int(os.getenv("OCR_CPU_THREADS", "2")),
            )
        return paddle_ocr_class(use_angle_cls=True, lang=self.lang, use_gpu=self.use_gpu)

    def extract_text(self, image_paths):
        texts = []
        confidences = []
        for image_path in image_paths:
            result = self._run_ocr(image_path)
            page_text, page_confidences = self._parse_result(result)
            texts.append(page_text)
            confidences.extend(page_confidences)

        confidence = mean(confidences) if confidences else 0.0
        return "\n\n".join(text for text in texts if text), float(confidence)

    def _run_ocr(self, image_path):
        engine = self.engine
        if hasattr(engine, "ocr"):
            try:
                return engine.ocr(str(image_path), cls=True)
            except TypeError:
                return engine.ocr(str(image_path))
        return engine.predict(str(image_path))

    @staticmethod
    def _parse_result(result):
        lines = []
        confidences = []
        pages = result if isinstance(result, list) else [result]
        for page in pages:
            if not page:
                continue
            if isinstance(page, dict):
                OCRService._parse_dict_page(page, lines, confidences)
                continue
            if hasattr(page, "json"):
                page_json = page.json() if callable(page.json) else page.json
                OCRService._parse_dict_page(page_json, lines, confidences)
                continue
            for item in page:
                try:
                    text = item[1][0]
                    confidence = float(item[1][1])
                except (TypeError, IndexError, ValueError):
                    continue
                lines.append(text)
                confidences.append(confidence)
        return "\n".join(lines), confidences

    @staticmethod
    def _parse_dict_page(page, lines, confidences):
        data = page.get("res", page)
        texts = data.get("rec_texts") or data.get("texts") or []
        scores = data.get("rec_scores") or data.get("scores") or []
        for index, text in enumerate(texts):
            if not text:
                continue
            lines.append(str(text))
            try:
                confidences.append(float(scores[index]))
            except (IndexError, TypeError, ValueError):
                pass
