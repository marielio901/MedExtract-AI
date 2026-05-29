# Deploy

## Componentes

- `web`: aplica migrations leves, inicializa o Flask via Gunicorn e expõe a porta `5000`.
- `worker`: mantém o processamento assíncrono de documentos pendentes, OCR, extração e suporte de IA.
- `volumes`: persistem o banco SQLite, uploads originais e cache do PaddleOCR. Imagens processadas ficam apenas em diretórios temporários.

## Subir localmente

```bash
cp .env.example .env
docker compose up --build
```

Depois acesse:

```text
http://localhost:5000
```

## Variáveis principais

```env
SECRET_KEY=troque-em-producao
OPENROUTER_API_KEY=
AI_EXTRACTION_ENABLED=true
OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct
OPENROUTER_VISION_MODEL=qwen/qwen3-vl-32b-instruct
DATABASE_URL=sqlite:////app/data/medextract_ai.db
UPLOAD_ORIGINAL_FOLDER=/app/uploads/original
UPLOAD_PROCESSED_FOLDER=/tmp/medextract-processed
```

## Operação

```bash
docker compose ps
docker compose logs -f web
docker compose logs -f worker
docker compose restart web worker
docker compose down
```

## Observações

O deploy atual usa SQLite com volume persistente, adequado para uso local, demonstração ou servidor único. Para produção com múltiplas instâncias, migre `DATABASE_URL` para PostgreSQL e troque o processamento em memória/polling por uma fila externa como Redis/RQ ou Celery.
