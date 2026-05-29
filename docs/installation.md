# Instalacao

## Requisitos

- Python 3.11+
- Poppler instalado no sistema para fallback com `pdf2image`
- Dependencias Python em `requirements.txt`

## Passos

```bash
cd medextract_ai
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app run.py init-db
python run.py
```

Abra `http://localhost:5000`.

## Observacoes

PaddleOCR pode baixar modelos na primeira execucao. Em ambientes sem GPU, mantenha `OCR_USE_GPU=false`.
