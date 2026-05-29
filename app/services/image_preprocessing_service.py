import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ImagePreprocessingService:
    def __init__(self, processed_folder):
        self.processed_folder = Path(processed_folder)
        self.processed_folder.mkdir(parents=True, exist_ok=True)

    def preprocess(self, image_path, output_dir=None):
        image_path = Path(image_path)
        output_folder = Path(output_dir) if output_dir else self.processed_folder
        output_folder.mkdir(parents=True, exist_ok=True)
        output_path = output_folder / f"{image_path.stem}_processed.png"
        try:
            return self._opencv_pipeline(image_path, output_path)
        except Exception as exc:
            logger.warning("opencv_preprocess_failed", extra={"error": str(exc)})
            return self._pillow_fallback(image_path, output_path)

    def _opencv_pipeline(self, image_path, output_path):
        import cv2
        import numpy as np

        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Nao foi possivel ler a imagem: {image_path}")

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=20)
        threshold = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        deskewed = self._deskew(threshold, cv2, np)
        contrasted = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(deskewed)
        resized = self._resize_if_needed(contrasted, cv2)
        cv2.imwrite(str(output_path), resized)
        return output_path

    @staticmethod
    def _deskew(image, cv2, np):
        coords = np.column_stack(np.where(image < 255))
        if coords.size == 0:
            return image
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) < 0.5:
            return image

        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

    @staticmethod
    def _resize_if_needed(image, cv2):
        height, width = image.shape[:2]
        target_width = 1200
        if width == target_width:
            return image
        scale = target_width / max(width, 1)
        return cv2.resize(
            image, (target_width, int(height * scale)), interpolation=cv2.INTER_CUBIC
        )

    @staticmethod
    def _pillow_fallback(image_path, output_path):
        from PIL import Image, ImageEnhance, ImageFilter

        with Image.open(image_path) as image:
            gray = image.convert("L")
            denoised = gray.filter(ImageFilter.MedianFilter(size=3))
            contrasted = ImageEnhance.Contrast(denoised).enhance(1.7)
            threshold = contrasted.point(lambda p: 255 if p > 165 else 0)
            threshold.save(output_path, "PNG")
        return output_path
