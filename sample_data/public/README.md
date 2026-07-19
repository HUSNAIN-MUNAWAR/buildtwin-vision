# Public Dataset Sample

`nyc_dob_permit_sample.csv` is a small processed sample from New York City's **DOB Permit Issuance** dataset, published by the Department of Buildings on NYC Open Data.

The sample keeps only fields needed by BuildTwin Vision's schedule/risk demo and omits permittee names, owner names, phone numbers, and other fields that are not needed for the public repository demonstration.

Regenerate it with:

```bash
python scripts/download_public_dataset.py
```

Raw downloaded JSON is written to `sample_data/public/raw/`, which is intentionally Git-ignored.
