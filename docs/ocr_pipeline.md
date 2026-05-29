# Pipeline OCR

## Entrada

Formatos aceitos: PDF, JPG, JPEG e PNG. Os arquivos sao validados por extensao, limitação de tamanho e `secure_filename`.

## PDF

`PDFService` tenta PyMuPDF primeiro. Se falhar, usa `pdf2image`.

## Imagem

`ImagePreprocessingService` aplica:

- grayscale
- denoise
- threshold adaptativo
- deskew
- contraste com CLAHE
- resize para melhorar OCR quando necessario

Quando OpenCV nao esta disponivel, ha fallback basico com Pillow para manter a operacao local previsivel.

## OCR

`OCRService` inicializa PaddleOCR de forma lazy. O resultado e normalizado para texto bruto e confianca media.
