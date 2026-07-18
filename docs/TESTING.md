# Testing

```bash
cd backend
python -m app.cli reset-seed
ruff check app tests
mypy app --no-incremental --follow-imports=skip
pytest

cd ../frontend
npm ci
npm run typecheck
npm run test
npm run lint
NEXT_TELEMETRY_DISABLED=1 npm run build
```

The backend suite covers auth failure, persisted dashboard values, organization isolation, polygon validation, IFC parsing, dependency graph/critical path, real video metrics, change output, progress approval and audit, risk explanations, safety/quality/alerts, PDF download, cycle rejection, invalid IFC, geometry, and risk monotonicity.

The frontend test verifies required operations navigation. TypeScript, ESLint, and the Next production compiler provide broader static/build validation. Screenshot previews are generated from authenticated seeded API data and should be refreshed only from local/demo records without secrets or private paths.
