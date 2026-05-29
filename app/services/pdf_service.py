import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class PDFService:
    def __init__(self, processed_folder):
        self.processed_folder = Path(processed_folder)
        self.processed_folder.mkdir(parents=True, exist_ok=True)

    def convert_to_images(self, pdf_path, output_dir=None):
        pdf_path = Path(pdf_path)
        output_folder = Path(output_dir) if output_dir else self.processed_folder
        output_folder.mkdir(parents=True, exist_ok=True)
        try:
            return self._convert_with_pymupdf(pdf_path, output_folder)
        except Exception as exc:
            logger.warning("pymupdf_pdf_conversion_failed", extra={"error": str(exc)})
            return self._convert_with_pdf2image(pdf_path, output_folder)

    def _convert_with_pymupdf(self, pdf_path, output_folder):
        import fitz

        output_paths = []
        document = fitz.open(pdf_path)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            output_path = output_folder / f"{pdf_path.stem}_page_{page_index + 1}.png"
            pixmap.save(output_path)
            output_paths.append(output_path)
        document.close()
        return output_paths

    def _convert_with_pdf2image(self, pdf_path, output_folder):
        from pdf2image import convert_from_path

        images = convert_from_path(str(pdf_path), dpi=220)
        output_paths = []
        for index, image in enumerate(images, start=1):
            output_path = output_folder / f"{pdf_path.stem}_page_{index}.png"
            image.save(output_path, "PNG")
            output_paths.append(output_path)
        return output_paths
