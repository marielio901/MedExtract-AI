# Arquitetura

MedExtract AI usa uma app factory Flask em `app/__init__.py`. A aplicacao e dividida em camadas para manter o processamento clinico isolado da interface e da API.

## Camadas

- IA: `app/services/ai_model_service.py`
- OCR e leitura: `ocr_service.py`, `pdf_service.py`, `image_preprocessing_service.py`
- CRUD: `crud_routes.py`, `document_routes.py`, repositories e models
- Dashboard: `dashboard_routes.py`, `dashboard_service.py`
- API: `api_routes.py`
- Validacao: `validation_service.py`, `schemas/medical_record_schema.py`
- Frontend: `templates/`, `static/`
- Documentacao: `docs/`

## Fluxo

Upload -> arquivo original -> conversao PDF -> preprocessamento -> OCR -> regex -> IA opcional -> validacao Pydantic -> SQLite -> dashboard/API/CRUD.

## Escalabilidade

O pipeline esta em services para permitir troca futura de processamento sincrono por Celery/RQ, armazenamento local por S3 e SQLite por PostgreSQL.
