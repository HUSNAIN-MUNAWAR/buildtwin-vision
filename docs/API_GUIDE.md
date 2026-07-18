# API guide

Base path: `/api/v1`. Interactive OpenAPI is available at `/docs`.

## Authentication

`POST /auth/login` returns a bearer JWT. Protected calls use `Authorization: Bearer <token>`.

## Core reads

- `GET /projects`
- `GET /dashboard/executive?project_id=1`
- `GET /dashboard/progress?project_id=1`
- `GET /bim/models?project_id=1`
- `GET /bim/models/{id}/elements`
- `GET /schedule/activities?project_id=1`
- `GET /schedule/dependency-graph?project_id=1`
- `GET /schedule/critical-path?project_id=1`
- `GET /captures?project_id=1`
- `GET /processing/jobs?project_id=1`
- `GET /progress/observations?project_id=1`
- `GET /changes?project_id=1`
- `GET /safety/events?project_id=1`
- `GET /quality/observations?project_id=1`
- `GET /risk/activities?project_id=1`
- `GET /alerts?project_id=1`
- `GET /reports?project_id=1`
- `GET /audit?project_id=1`

## Mutations

- `POST /captures/images` and `/captures/videos`: multipart upload with project/zone/camera IDs.
- `POST /processing/media/{asset_id}/run`: executes the local job contract.
- `POST /changes/compare`: creates and persists a real image comparison.
- `POST /progress/observations/{id}/review`: approve/reject; optional approved progress.
- `POST /alerts/{id}/acknowledge`
- `POST /reports/generate?project_id=1`

Validation errors use HTTP 4xx and a human-readable `detail`. A response correlation ID is returned as `x-correlation-id`.
