# API REST

Todas as respostas usam JSON. Uploads aceitam `multipart/form-data`.

## Endpoints

## `POST /api/upload`

Campo: `file` ou `document`.

```bash
curl -F "file=@alta.pdf" http://localhost:5000/api/upload
```

## `GET /api/documents`

Filtros: `status`, `q`.

## `GET /api/documents/<id>`

Retorna documento e registro medico associado.

## `DELETE /api/documents/<id>`

Remove documento, registro associado e arquivo original.

## `GET /api/records`

Filtros: `patient`, `hospital`, `icd`, `diagnosis`, `status`, `q`.

## `GET /api/records/<id>`

Retorna um registro medico.

## `PUT /api/records/<id>`

Atualiza campos editaveis e revalida com Pydantic.

## `GET /api/dashboard/summary`

Retorna indicadores e series para graficos.
