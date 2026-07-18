# Contributing

Thank you for taking BuildTwin Vision seriously. This project is meant to stay credible, runnable, and honest about what is implemented.

## Development Setup

1. Set up the backend from `backend/` with Python 3.12 and `pip install -e ".[dev]"`.
2. Run `alembic upgrade head` and `python -m app.cli reset-seed`.
3. Set up the frontend from `frontend/` with `npm ci`.
4. Run the backend and frontend checks before opening a pull request.

## Quality Bar

- Keep changes focused and aligned with the existing architecture.
- Add or update tests when changing API behavior, domain logic, parsers, risk scoring, or review workflows.
- Do not add hardcoded dashboard values, silent fallbacks, unlicensed media, copied screenshots, fabricated customers, fabricated benchmarks, or production claims without evidence.
- Keep AI/vision outputs clearly labeled when they are candidates or estimates.
- Do not commit `.env` files, tokens, local databases, generated dependency folders, private media, or credentials.

## Useful Commands

```bash
cd backend
ruff check app tests
mypy app --no-incremental --follow-imports=skip
pytest
```

```bash
cd frontend
npm run lint
npm run typecheck
npm run test
npm run build
```

## Pull Requests

Use a concise title, explain the user/developer impact, list validation commands, and call out any known limitations. Screenshots should come from the real local/demo application data and must not include secrets or private paths.
