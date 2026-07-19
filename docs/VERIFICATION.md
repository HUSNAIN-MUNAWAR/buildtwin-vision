# Verification report

Latest local verification date: 2026-07-19.
Latest GitHub Actions verification: run `29678149082` on `main` passed backend, frontend, and Docker jobs for commit `c2eeb4a`.

| Check | Command | Result | Evidence / limitation |
|---|---|---|---|
| Backend install | `py -m pip install -e ".[dev]"` | Passed after packaging fix | Explicit setuptools package discovery added for `app*` |
| Migration state | `py -m alembic current -v` | Passed | SQLite database at `20260719_0001 (head)` |
| Public dataset download | `py scripts\download_public_dataset.py` | Passed | 12 processed NYC DOB Permit Issuance records written to `sample_data/public/nyc_dob_permit_sample.csv`; raw cache ignored |
| Seed | `py -m app.cli reset-seed` | Passed | 12 IFC entities, 20 activities, 12 public permit records, 72 decoded frames, 12.956% change, PDF path |
| Backend lint | `ruff check app tests` | Passed | All checks passed |
| Backend typecheck | `mypy app --no-incremental --follow-imports=skip` | Passed | 37 source files |
| Backend tests | `pytest` | Passed | 21 tests |
| API smoke | `py ..\scripts\smoke_api.py` from `backend/` | Passed | health, projects, dashboard, schedule, risk endpoints returned 200 |
| Frontend test | `npm run test` | Passed | Required navigation test |
| Frontend install | `npm ci` | Not completed locally | Timed out after 5 minutes in this Windows environment and left incomplete `node_modules`; CI remains configured to run clean Linux `npm ci` |
| Frontend lint/typecheck/build | `npm run lint`, `npm run typecheck`, `npm run build` | Not completed locally | `eslint`, `tsc`, and `next` were unavailable because local dependency install did not complete |
| GitHub frontend CI | `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` | Passed | Run `29678149082` on clean GitHub Actions Linux runner |
| GitHub Docker CI | `docker compose config`, `docker compose build` | Passed | Run `29678149082` on clean GitHub Actions Linux runner |
| PDF API | Backend integration test | Passed | Response starts with `%PDF` |
| Docker runtime | `docker --version` | Not available | Docker CLI is not installed in this environment |
| Portfolio previews | `py scripts\render_previews.py` | Passed | 16 PNG previews regenerated from authenticated FastAPI seeded data and generated media; script uses Pillow and FastAPI TestClient |

Warnings about naive `datetime.utcnow()` under Python 3.13 are known and documented for conversion to timezone-aware UTC fields during production hardening.
