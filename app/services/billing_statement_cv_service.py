import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class BillingStatementCVService:
    REGIONS = {
        "header": (0.07, 0.055, 0.58, 0.145),
        "account": (0.07, 0.18, 0.93, 0.29),
        "table": (0.07, 0.30, 0.93, 0.50),
        "totals": (0.07, 0.43, 0.93, 0.55),
        "barcode": (0.09, 0.58, 0.43, 0.68),
    }

    def __init__(self, processed_folder, ocr_service):
        self.processed_folder = Path(processed_folder)
        self.processed_folder.mkdir(parents=True, exist_ok=True)
        self.ocr_service = ocr_service

    def extract(self, image_paths, output_dir=None):
        for image_path in image_paths:
            payload = self._extract_from_image(Path(image_path), output_dir=output_dir)
            if payload:
                return payload
        return {}

    def _extract_from_image(self, image_path, output_dir=None):
        import cv2

        image = cv2.imread(str(image_path))
        if image is None or not self._looks_like_bill_statement(image, cv2):
            return {}

        texts = self._ocr_regions(image, image_path, cv2, output_dir=output_dir)
        if not texts:
            return {}

        combined = "\n".join(text for text in texts.values() if text)
        payload = {
            "document_type": "billing_statement",
            "hospital_name": self._hospital_name(texts.get("header", "")),
            "hospital_address": self._hospital_address(texts.get("header", "")),
            "hospital_npi": self._match(combined, [r"\bNPI\s*[:#]?\s*([A-Z0-9-]+)"]),
            "hospital_phone": self._match(
                combined, [r"\bPhone\s*[:#]?\s*([\(\)\d\s.+-]{7,})"]
            ),
            "statement_date": self._match(
                combined, [r"Statement Date\s*[:#]?\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{1,4})"]
            ),
            "guarantor_no": self._match(
                combined, [r"Guarantor No\s*[:#]?\s*([A-Z0-9-]+)"]
            ),
            "patient_name": self._match(combined, [r"Patient Name\s*[:#]?\s*([^\n]+)"]),
            "dob": self._match(
                combined, [r"Date of Birth\s*[:#]?\s*([0-9]{1,4}[/-][0-9]{1,2}[/-][0-9]{1,4})"]
            ),
            "primary_insurance": self._match(
                combined, [r"Primary Insurance\s*[:#]?\s*([^\n]+)"]
            ),
            "group_no": self._match(combined, [r"Group No\s*[:#]?\s*([A-Z0-9-]+)"]),
            "primary_diagnosis": self._match(
                combined, [r"Primary Diagnosis\s*[:#]?\s*([^\n]+)"]
            ),
            "icd10_code": self._match(
                combined, [r"ICD-?10 Code\s*[:#]?\s*([A-Z0-9.]+)"]
            ),
            "billing_items": self._billing_items(texts.get("table", "") or combined),
            "total_billed_charges": self._money(combined, "Total Billed Charges"),
            "insurance_adjustments": self._money(combined, "Insurance Adjustments"),
            "patient_amount_due": self._money(combined, "Patient Amount Due"),
            "barcode_value": self._barcode_value(image, cv2),
        }
        if payload.get("primary_diagnosis"):
            payload["admission_diagnosis"] = payload["primary_diagnosis"]

        return {key: value for key, value in payload.items() if value not in (None, "", [])}

    @staticmethod
    def _looks_like_bill_statement(image, cv2):
        height, width = image.shape[:2]
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        blue_mask = cv2.inRange(hsv, (90, 35, 35), (125, 255, 255))
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > width * 0.35 and h > height * 0.006 and y < height * 0.45:
                return True
        return False

    def _ocr_regions(self, image, image_path, cv2, output_dir=None):
        texts = {}
        stem = image_path.stem
        output_folder = Path(output_dir) if output_dir else self.processed_folder
        output_folder.mkdir(parents=True, exist_ok=True)
        for name, bounds in self.REGIONS.items():
            if name == "barcode":
                continue
            crop = self._crop(image, bounds)
            crop = self._prepare_for_ocr(crop, cv2)
            crop_path = output_folder / f"{stem}_cv_{name}.png"
            cv2.imwrite(str(crop_path), crop)
            try:
                text, _confidence = self.ocr_service.extract_text([crop_path])
            except Exception as exc:
                logger.warning(
                    "cv_region_ocr_failed",
                    extra={"region": name, "error": str(exc)},
                )
                text = ""
            texts[name] = text
        return texts

    @staticmethod
    def _crop(image, bounds):
        height, width = image.shape[:2]
        left, top, right, bottom = bounds
        x1 = max(0, int(width * left))
        y1 = max(0, int(height * top))
        x2 = min(width, int(width * right))
        y2 = min(height, int(height * bottom))
        return image[y1:y2, x1:x2]

    @staticmethod
    def _prepare_for_ocr(crop, cv2):
        height, width = crop.shape[:2]
        target_width = 1100
        scale = target_width / max(width, 1)
        resized = cv2.resize(
            crop,
            (int(width * scale), int(height * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    @staticmethod
    def _hospital_name(text):
        for line in text.splitlines():
            line = line.strip()
            if re.search(r"\bhospital\b", line, re.IGNORECASE):
                return line[:255]
        return None

    @staticmethod
    def _hospital_address(text):
        for line in text.splitlines():
            line = line.strip()
            if not line or re.search(r"\bhospital\b|\bNPI\b|\bPhone\b", line, re.I):
                continue
            return line[:500]
        return None

    @staticmethod
    def _match(text, patterns):
        normalized = re.sub(r"[ \t]+", " ", text or "")
        for pattern in patterns:
            match = re.search(pattern, normalized, flags=re.IGNORECASE)
            if match:
                value = match.group(1).strip(" \t\r\n:;-")
                return value[:1000] if value else None
        return None

    @staticmethod
    def _money(text, label):
        label_pattern = re.escape(label).replace(r"\ ", r"\s+")
        match = re.search(
            rf"{label_pattern}[\s\S]{{0,120}}?(-?\$?\s*[0-9][0-9,]*(?:\.[0-9]{{2}})?)",
            text or "",
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return float(match.group(1).replace("$", "").replace(",", "").replace(" ", ""))

    @staticmethod
    def _billing_items(text):
        items = []
        pattern = re.compile(
            r"^\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\s+([A-Z0-9]{2,8})\s+(.+?)\s+\$?\s*([0-9][0-9,]*(?:\.[0-9]{2}))\s*$",
            flags=re.IGNORECASE | re.MULTILINE,
        )
        for match in pattern.finditer(text or ""):
            items.append(
                {
                    "date": match.group(1),
                    "cpt": match.group(2),
                    "description": re.sub(r"\s+", " ", match.group(3)).strip(" -"),
                    "charges": float(match.group(4).replace(",", "")),
                }
            )
        if items:
            return items
        return BillingStatementCVService._billing_items_from_split_lines(text)

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

            date = lines[index]
            if index + 2 >= len(lines):
                break
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

    def _barcode_value(self, image, cv2):
        detector_class = getattr(cv2, "barcode_BarcodeDetector", None)
        if detector_class is None:
            return None

        crop = self._crop(image, self.REGIONS["barcode"])
        detector = detector_class()
        try:
            decoded = detector.detectAndDecode(crop)
        except Exception:
            return None
        return self._first_decoded_barcode(decoded)

    @staticmethod
    def _first_decoded_barcode(decoded):
        if isinstance(decoded, str):
            return decoded.strip()[:255] or None
        if isinstance(decoded, (list, tuple)):
            for item in decoded:
                value = BillingStatementCVService._first_decoded_barcode(item)
                if value:
                    return value
        return None
