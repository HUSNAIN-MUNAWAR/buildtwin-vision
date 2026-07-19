# Public Dataset Demo

## Dataset

- **Title:** DOB Permit Issuance
- **Publisher:** New York City Department of Buildings (DOB)
- **Official source:** https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a
- **API endpoint:** https://data.cityofnewyork.us/resource/ipu4-2q9a.json
- **Terms:** https://opendata.cityofnewyork.us/overview/#termsofuse
- **Download date:** 2026-07-19
- **Repository sample:** `sample_data/public/nyc_dob_permit_sample.csv`

NYC Open Data identifies the submitting agency as the authoritative source and provides public datasets for informational purposes. The dataset page attributes the records to the Department of Buildings.

## Why This Dataset Fits

BuildTwin Vision models construction progress, schedules, work packages, risks, evidence, audit records, and operational reporting. The DOB Permit Issuance dataset contains real construction and demolition permit lifecycle records with job numbers, work types, permit statuses, filing statuses, and dates. Those fields map naturally into a schedule-style construction activity feed for demonstrating import, progress normalization, variance, and risk analytics.

## Fields Used

| Source field | Project use |
|---|---|
| `job__` | Stable external activity identifier |
| `borough` | Public sample zone context |
| `bin__` | Public building identifier metadata |
| `street_name` | Activity display context |
| `job_type` | Work-package and contractor-label context |
| `permit_type` | Work-package mapping |
| `work_type` | Work-package mapping and activity title |
| `permit_status` | Source status metadata |
| `filing_status` | Variance/risk scenario input |
| `issuance_date` | Source lifecycle date |
| `job_start_date` | Source lifecycle date |
| `expiration_date` | Source lifecycle date |

## Fields Ignored

The sample intentionally excludes permittee names, owner names, contact details, house numbers, and other fields that are unnecessary for the demo workflow. The app does not describe these public records as customers, clients, or production deployments.

## Transformations

The download script selects 12 Manhattan records with issued permits and non-empty `job_start_date` and `expiration_date`.

The backend importer:

- Deduplicates records by job number, permit type, and work type.
- Validates all required dates.
- Maps permit/work types to BuildTwin work packages.
- Converts public permit records into schedule activities.
- Date-shifts the public records into a fixed July 2026 demo window so progress and risk calculations are visible in a stable local demo.
- Preserves source job number, BIN, permit status, and filing status in returned seed metadata.

No model training is performed. The project computes deterministic schedule variance and heuristic delay-risk scores from the imported public sample.

## Reproduction

```bash
python scripts/download_public_dataset.py
cd backend
python -m app.cli reset-seed
python ../scripts/smoke_api.py
```

The processed CSV is committed because it is small and reproducible. The raw JSON cache is written under `sample_data/public/raw/` and is Git-ignored.

## Expected Layout

```text
sample_data/public/
  README.md
  nyc_dob_permit_sample.csv
  raw/                         # ignored download cache
```

## Limitations

- The sample is a small public subset, not a representative statistical sample of all NYC construction activity.
- Dates are shifted for demo scheduling so the dashboard remains stable.
- The records are public permit records, not BuildTwin customers or private project data.
- The app does not evaluate permit-processing accuracy; it performs import, normalization, dashboarding, and risk simulation using real public records.

## Removal

Remove the processed sample and ignored raw cache with normal file deletion:

```bash
rm sample_data/public/nyc_dob_permit_sample.csv
rm -rf sample_data/public/raw
```
