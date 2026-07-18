# Verification report

Latest local verification date: 2026-07-19.

| Check | Command | Result | Evidence / limitation |
|---|---|---|---|
| Backend install | `py -m pip install -e ".[dev]"` | Passed after packaging fix | Explicit setuptools package discovery added for `app*` |
| Migration state | `py -m alembic current -v` | Passed | SQLite database at `20260719_0001 (head)` |
| Seed | `py -m app.cli reset-seed` | Passed | 12 IFC entities, 8 activities, 72 decoded frames, 12.956% change, PDF path |
| Backend lint | `ruff check app tests` | Passed | All checks passed |
| Backend typecheck | `mypy app --no-incremental --follow-imports=skip` | Passed | 36 source files |
| Backend tests | `pytest` | Passed | 19 tests |
| API smoke | `py ..\scripts\smoke_api.py` from `backend/` | Passed | health, projects, dashboard, schedule, risk endpoints returned 200 |
| Frontend test | `npm run test` | Passed | Required navigation test |
| Frontend install | `npm ci`, `npm install`, `corepack pnpm install` | Not completed locally | Package-manager processes repeatedly timed out on this Windows environment and left incomplete `node_modules`; CI remains configured to run clean Linux `npm ci` |
| Frontend lint/typecheck/build | `npm run lint`, `npm run typecheck`, `npm run build` | Not completed in latest local run | Blocked by incomplete local dependency install; previous verification snapshot in `verification.json` records these as passing |
| PDF API | Backend integration test | Passed | Response starts with `%PDF` |
| Docker runtime | `docker --version` | Not available | Docker CLI is not installed in this environment |
| Portfolio previews | `py scripts\render_previews.py` | Not regenerated locally | WeasyPrint import failed because native Pango/GObject libraries are missing on Windows; existing 15 PNG previews are retained |

Warnings about naive `datetime.utcnow()` under Python 3.13 are known and documented for conversion to timezone-aware UTC fields during production hardening.
