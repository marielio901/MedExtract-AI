# Banco de dados

O banco padrao e SQLite em `medextract_ai.db`, configuravel por `DATABASE_URL`.

## Tabelas

## `documents`

Armazena arquivo original, caminho interno, tipo, tamanho, status, texto OCR bruto, erro e confianca.

## `medical_records`

Armazena os campos medicos extraidos:

- hospital, paciente, MRN, DOB
- diagnostico, CID-10, curso hospitalar
- exames, medicamentos, instrucoes, alergias
- medico, assinatura, status e confianca
- JSON estruturado validado

## `audit_logs`

Armazena eventos operacionais para rastreabilidade local.

## Migracoes

```bash
flask --app run.py db init
flask --app run.py db migrate -m "initial schema"
flask --app run.py db upgrade
```
