# MedExtract AI

MedExtract AI é uma aplicação Flask para importar documentos médicos em PDF ou imagem, executar OCR, extrair dados estruturados, validar o resultado e visualizar tudo em um dashboard analítico.

O foco atual do projeto é processar contas e demonstrativos hospitalares, como `PATIENT ACCOUNT STATEMENT`, lendo dados do hospital, paciente, convênio, diagnóstico, itens cobrados, totais e valor devido. O sistema combina visão computacional determinística, OCR e suporte de IA visual para melhorar a leitura de arquivos ruidosos ou rasurados.



## O Que O Sistema Faz

- Importa documentos em `pdf`, `jpg`, `jpeg` e `png`.
- Salva apenas o arquivo original enviado pelo usuário.
- Converte PDFs e imagens intermediárias somente em diretórios temporários.
- Detecta contas hospitalares por layout visual.
- Recorta regiões importantes do documento para OCR regional.
- Extrai campos por regex, visão computacional e OCR.
- Usa IA como suporte quando a confiança fica baixa ou quando o usuário clica em `Correção IA`.
- Valida os dados com Pydantic antes de gravar no banco.
- Persiste documentos, registros médicos e logs de auditoria em SQLite.
- Exibe dashboard com métricas, gráficos, atividades recentes e diagnósticos frequentes.
- Permite visualizar o documento original em modal sem salvar previews processados.
- Exporta registros para CSV e XLSX.

## Fluxo De Funcionamento

1. O usuário importa um documento pela tela `Importar`.
2. O arquivo original é salvo em `uploads/original`.
3. Um registro é criado na tabela `documents` com status `pending`.
4. O worker em segundo plano busca documentos pendentes.
5. Se o arquivo for PDF, ele é convertido em imagens temporárias.
6. O sistema tenta detectar se é uma conta hospitalar conhecida.
7. Para contas hospitalares, regiões como cabeçalho, dados do paciente, tabela e totais são recortadas temporariamente.
8. O OCR lê o texto bruto e o sistema extrai campos estruturados.
9. Se faltar dado ou a confiança ficar abaixo do limite configurado, a IA pode ser acionada.
10. O payload final é validado por Pydantic.
11. O registro é salvo em `medical_records`.
12. O documento muda para `processed`, `needs_review` ou `error`.
13. O dashboard e as tabelas passam a refletir os dados extraídos.

## Arquitetura

```text
app/
  models/          Modelos SQLAlchemy
  repositories/    Camada de acesso ao banco
  routes/          Rotas Flask, telas e API
  schemas/         Validação Pydantic
  services/        OCR, IA, arquivos, PDF, extração, dashboard e auditoria
  static/          CSS e JavaScript
  templates/       Templates Jinja2
docs/              Documentação técnica
tests/             Testes automatizados
uploads/original/  Arquivos originais importados
```

Componentes principais:

- `Document`: representa o arquivo importado.
- `MedicalRecord`: representa os dados extraídos do documento.
- `AuditLog`: registra eventos importantes.
- `ExtractionService`: orquestra OCR, visão computacional, regex, IA e persistência.
- `BillingStatementCVService`: faz leitura determinística de contas hospitalares.
- `OCRService`: encapsula PaddleOCR.
- `AIModelService`: integra OpenRouter/Qwen para correção por IA.
- `BatchProcessingService`: processa documentos pendentes em background.

## Tecnologias

- Python 3.12
- Flask
- SQLAlchemy
- SQLite
- Flask-Migrate
- Flask-WTF
- Jinja2
- Bootstrap 5
- Chart.js
- OpenCV
- Pillow
- PaddleOCR
- PyMuPDF
- pdf2image
- LangChain
- OpenRouter API
- Pydantic
- Pandas
- pytest
- Docker e Docker Compose

## Requisitos Locais

No Ubuntu/Debian, instale pacotes de sistema usados por OCR, PDF e OpenCV:

```bash
sudo apt update
sudo apt install -y poppler-utils libgl1 libglib2.0-0 libgomp1
```

Crie e ative o ambiente Python:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuração Do Ambiente

Crie o arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Principais variáveis:

```env
SECRET_KEY=troque-em-producao
DATABASE_URL=sqlite:///medextract_ai.db

CV_BILL_EXTRACTION_ENABLED=true
AI_EXTRACTION_ENABLED=true
AI_CONFIDENCE_THRESHOLD=0.98

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct
OPENROUTER_VISION_MODEL=qwen/qwen3-vl-32b-instruct
OPENROUTER_APP_TITLE=MedExtract AI

AI_MAX_VISION_PAGES=3
AI_VISION_MAX_WIDTH=1400

ENABLE_BACKGROUND_WORKER=true
BACKGROUND_WORKER_POLL_SECONDS=5
MAX_CONTENT_LENGTH=26214400
LOG_LEVEL=INFO
```

Notas importantes:

- Nunca publique o `.env`.
- A chave `OPENROUTER_API_KEY` deve ficar somente no ambiente.
- `AI_EXTRACTION_ENABLED=true` permite que a IA seja usada automaticamente quando necessário.
- O botão `Correção IA` usa o modelo visual configurado em `OPENROUTER_VISION_MODEL`.
- Por padrão, imagens processadas, crops e páginas de PDF ficam em diretórios temporários.

## Rodando Localmente

Inicialize o banco:

```bash
flask --app run.py init-db
```

Suba a aplicação:

```bash
python3 run.py
```

Acesse:

```text
http://localhost:5000
```

Em modo local, o Flask sobe junto com o worker em background quando `ENABLE_BACKGROUND_WORKER=true`.

## Rodando Com Docker

O projeto já possui `Dockerfile`, `docker-compose.yml` e entrypoint de produção.

Suba tudo com:

```bash
docker compose up --build
```

O Compose cria dois componentes:

- `web`: Flask servido por Gunicorn.
- `worker`: processamento de OCR, extração e IA em segundo plano.

Acesse:

```text
http://localhost:5000
```

Dados persistentes em Docker:

- Banco SQLite: volume `medextract_data`.
- Uploads originais: volume `medextract_uploads`.
- Cache PaddleOCR: volume `medextract_paddlex_cache`.

Arquivos não persistidos:

- Imagens processadas.
- Crops de OCR.
- Páginas convertidas de PDF.
- Previews de documento.

Esses arquivos são temporários e removidos automaticamente.

## Usando A Interface

### Dashboard

Mostra:

- total de documentos;
- processados;
- pendentes;
- erros;
- pacientes únicos;
- hospitais encontrados;
- confiança média;
- gráficos por mês, status, hospital, diagnóstico e procedimento;
- atividades recentes.

### Importar

Tela para enviar um ou vários documentos. Após o upload, o documento entra como `pending` e o worker faz o processamento.

### Documentos

Lista os arquivos importados. A tabela possui:

- nome do arquivo;
- tipo;
- status;
- confiança;
- data de criação;
- botão para visualizar o documento original;
- botão `Correção IA`;
- botão de detalhes.

### Visualizar Documento

O botão de visualização abre o arquivo em um modal com fundo ofuscado. Para PDF, a primeira página é renderizada em memória.

### Correção IA

O botão `Correção IA` envia o documento original, ou a página renderizada do PDF, para o modelo visual Qwen junto com o OCR bruto de apoio. A IA retorna um JSON limpo. O sistema valida esse JSON antes de atualizar o banco.

### Registros Médicos

Lista os dados estruturados extraídos dos documentos. É possível filtrar por paciente, hospital, CID e diagnóstico.

### Detalhes

Mostra o documento, o registro extraído, campos de cobrança, itens cobrados e texto OCR bruto salvo.

## Fluxo OCR

1. O documento original é lido.
2. PDF é convertido em imagem temporária quando necessário.
3. A imagem pode passar por grayscale, denoise, threshold, deskew, contraste e resize.
4. PaddleOCR extrai texto e confiança média.
5. O texto bruto é salvo no documento.
6. Dados estruturados são extraídos e validados.

## Fluxo De Visão Computacional

Para contas hospitalares com layout conhecido:

1. O sistema identifica barras e blocos visuais do documento.
2. Recorta regiões como cabeçalho, conta do paciente, tabela, totais e código de barras.
3. Executa OCR regional.
4. Aplica regex e normalização.
5. Calcula totais e confiança.

Esse fluxo reduz dependência da IA e é mais rápido para documentos padronizados.

## Fluxo De IA

A IA entra como suporte em dois cenários:

- automaticamente, quando a confiança fica abaixo de `AI_CONFIDENCE_THRESHOLD` ou o registro precisa de revisão;
- manualmente, quando o usuário clica em `Correção IA`.

O modelo textual (`OPENROUTER_MODEL`) é usado para texto OCR. O modelo visual (`OPENROUTER_VISION_MODEL`) é usado para ler a imagem do documento.

Regras de segurança do fluxo:

- a IA deve retornar apenas JSON;
- respostas inválidas são rejeitadas;
- Pydantic valida o payload antes da gravação;
- dados existentes podem ser usados como base, mas a atualização só ocorre após validação.

## Banco De Dados

Tabelas principais:

- `documents`: arquivo original, caminho, tipo, tamanho, status, OCR bruto, erro, confiança e datas.
- `medical_records`: dados estruturados do paciente, hospital, diagnóstico, conta hospitalar, itens cobrados, totais, status e confiança.
- `audit_logs`: eventos de upload, processamento, correção, edição e exclusão.

SQLite é suficiente para uso local, demonstrações e servidor único. Para produção com múltiplas instâncias, recomenda-se migrar para PostgreSQL.

## API REST

Endpoints principais:

```text
POST   /api/upload
GET    /api/documents
GET    /api/documents/<id>
DELETE /api/documents/<id>
GET    /api/records
GET    /api/records/<id>
PUT    /api/records/<id>
GET    /api/dashboard/summary
GET    /healthz
```

Exemplos:

```bash
curl -F "file=@statement.pdf" http://localhost:5000/api/upload
curl http://localhost:5000/api/dashboard/summary
curl -X PUT http://localhost:5000/api/records/1 \
  -H "Content-Type: application/json" \
  -d '{"patient_name":"Jane Doe","extraction_status":"validated"}'
```

## Testes

Rode:

```bash
python -m pytest
```

Também é útil validar sintaxe:

```bash
python -m compileall app worker.py
```

Validar Compose:

```bash
docker compose config --services
```

## Comandos Úteis

Subir local:

```bash
python3 run.py
```

Inicializar banco:

```bash
flask --app run.py init-db
```

Subir Docker:

```bash
docker compose up --build
```

Ver logs:

```bash
docker compose logs -f web
docker compose logs -f worker
```

Reiniciar:

```bash
docker compose restart web worker
```

Parar:

```bash
docker compose down
```

## Troubleshooting

### `no such table: documents`

O banco ainda não foi criado. Execute:

```bash
flask --app run.py init-db
```

### PaddleOCR consumindo muita memória

O projeto já usa modelos mobile e limita OCR para CPU. Se ainda pesar, reduza:

```env
OCR_DET_LIMIT_SIDE_LEN=640
OCR_CPU_THREADS=1
```

### Correção IA não funciona

Verifique:

```env
OPENROUTER_API_KEY=
AI_EXTRACTION_ENABLED=true
OPENROUTER_VISION_MODEL=qwen/qwen3-vl-32b-instruct
```

Também confira logs:

```bash
docker compose logs -f worker
```

### Porta 5000 ocupada

Altere a porta no `docker-compose.yml`:

```yaml
ports:
  - "5001:5000"
```

Ou rode localmente com:

```bash
PORT=5001 python3 run.py
```

### Muitos arquivos em `uploads/processed`

Versões antigas salvavam imagens processadas. A versão atual usa temporários. Depois de confirmar que não precisa dos arquivos antigos, eles podem ser removidos manualmente.

## Preparação Para Produção

Antes de publicar:

- Troque `SECRET_KEY`.
- Use uma chave OpenRouter segura no ambiente.
- Não versione `.env`.
- Configure backup do banco e uploads.
- Use HTTPS no proxy reverso.
- Monitore logs do `web` e do `worker`.
- Considere PostgreSQL para múltiplas instâncias.
- Considere Redis/RQ ou Celery para filas distribuídas.
- Revise requisitos de LGPD/HIPAA conforme o ambiente de uso.

## Roadmap

- Autenticação e usuários.
- Controle de permissões.
- PostgreSQL.
- Fila externa com Redis/RQ ou Celery.
- Armazenamento S3.
- Busca semântica.
- Auditoria avançada.
- Deploy com proxy reverso e TLS.
- Observabilidade com métricas e tracing.

## Fonte dos dados;

- kaggle: https://www.kaggle.com/datasets/devp1866/noisy-medical-document-images-ocr
- Apresentação youtube: https://youtu.be/466D3f12ejY
