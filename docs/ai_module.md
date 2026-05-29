# Modulo de IA

`AIModelService` usa LangChain com endpoint OpenAI-compativel do OpenRouter.

## Variaveis

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## Modelos

- `qwen/qwen-2.5-7b-instruct`
- `deepseek/deepseek-chat`
- `google/gemini-flash`
- `meta-llama/llama-3.1-8b-instruct`

## Contrato

A IA recebe texto OCR bruto e retorna somente JSON valido com os campos solicitados. A aplicacao remove cercas markdown quando necessario, tenta parsear JSON e rejeita qualquer resposta invalida.

## Prompt interno

Voce e um extrator de dados medicos. Recebera texto OCR bruto de documentos clinicos. Extraia apenas os campos solicitados e retorne somente JSON valido. Nao escreva explicacoes. Se nao encontrar um campo, retorne null.
