from __future__ import annotations

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "sample_data" / "public" / "nyc_dob_permit_sample.csv"
RAW = ROOT / "sample_data" / "public" / "raw" / "nyc_dob_permit_sample_raw.json"
API = "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
SOURCE = "https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a"
TERMS = "https://opendata.cityofnewyork.us/overview/#termsofuse"

FIELDS = [
    "borough",
    "bin__",
    "street_name",
    "job__",
    "job_type",
    "permit_type",
    "work_type",
    "permit_status",
    "filing_status",
    "issuance_date",
    "expiration_date",
    "job_start_date",
]


def main() -> int:
    where = "permit_status='ISSUED' AND job_start_date IS NOT NULL AND expiration_date IS NOT NULL AND borough='MANHATTAN'"
    params = {
        "$select": ",".join(FIELDS),
        "$where": where,
        "$limit": "12",
        "$order": "issuance_date ASC",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    print("Downloading NYC DOB Permit Issuance sample")
    print(f"Source: {SOURCE}")
    print(f"Terms: {TERMS}")
    print(f"URL: {url}")
    with urllib.request.urlopen(url, timeout=60) as response:
        rows = json.loads(response.read().decode("utf-8"))
    if len(rows) < 8:
        raise RuntimeError(f"Expected at least 8 permit records, received {len(rows)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    RAW.parent.mkdir(parents=True, exist_ok=True)
    RAW.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "job_number",
                "borough",
                "bin_number",
                "street_name",
                "job_type",
                "permit_type",
                "work_type",
                "permit_status",
                "filing_status",
                "issuance_date",
                "expiration_date",
                "job_start_date",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "job_number": row.get("job__", ""),
                    "borough": row.get("borough", ""),
                    "bin_number": row.get("bin__", ""),
                    "street_name": row.get("street_name", ""),
                    "job_type": row.get("job_type", ""),
                    "permit_type": row.get("permit_type", ""),
                    "work_type": row.get("work_type", ""),
                    "permit_status": row.get("permit_status", ""),
                    "filing_status": row.get("filing_status", ""),
                    "issuance_date": row.get("issuance_date", ""),
                    "expiration_date": row.get("expiration_date", ""),
                    "job_start_date": row.get("job_start_date", ""),
                }
            )
    print(f"Wrote processed sample: {OUT.relative_to(ROOT)} ({len(rows)} records)")
    print(f"Wrote raw download cache: {RAW.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
