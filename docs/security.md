# Seguranca

## Upload

- extensoes permitidas: PDF, JPG, JPEG, PNG
- limite por `MAX_CONTENT_LENGTH`
- nomes sanitizados com `secure_filename`
- arquivos ficam em `uploads/`, fora de `static/`

## Segredos

API keys devem ficar somente no `.env`. `.env.example` nao contem chaves reais.

## Erros

Handlers globais evitam expor stacktrace em producao. Logs internos registram falhas de processamento e IA.

## LGPD

O projeto prepara auditoria via `audit_logs`, isolamento de upload fora da web publica e revisao manual. Para producao real, adicionar autenticacao, autorizacao, criptografia de dados sensiveis, politicas de retencao e trilhas de acesso por usuario.

## Autenticacao futura

A arquitetura permite adicionar JWT, usuarios, papeis e multi-tenant sem reescrever o pipeline OCR/IA.
