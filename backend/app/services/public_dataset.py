from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

DATASET_TITLE = "DOB Permit Issuance"
DATASET_PUBLISHER = "New York City Department of Buildings (DOB)"
DATASET_SOURCE = "https://data.cityofnewyork.us/Housing-Development/DOB-Permit-Issuance/ipu4-2q9a"
DATASET_API = "https://data.cityofnewyork.us/resource/ipu4-2q9a.json"
DATASET_TERMS = "https://opendata.cityofnewyork.us/overview/#termsofuse"


@dataclass(frozen=True)
class PublicPermit:
    job_number: str
    borough: str
    bin_number: str
    street_name: str
    job_type: str
    permit_type: str
    work_type: str
    permit_status: str
    filing_status: str
    issuance_date: date
    expiration_date: date
    job_start_date: date

    @property
    def work_label(self) -> str:
        work = self.work_type or self.permit_type or "GEN"
        return f"{self.permit_type}-{work}".strip("-")


def parse_socrata_date(value: str) -> date:
    value = (value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Invalid NYC DOB date value: {value!r}")


def read_public_permits(path: str | Path) -> list[PublicPermit]:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Public dataset sample not found: {source}")
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    permits: list[PublicPermit] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=2):
        job_number = row.get("job_number", "").strip()
        if not job_number:
            raise ValueError(f"Missing job_number in public permit sample row {index}")
        permit_type = row.get("permit_type", "").strip() or "GEN"
        work_type = row.get("work_type", "").strip() or permit_type
        key = f"{job_number}-{permit_type}-{work_type}"
        if key in seen:
            continue
        seen.add(key)
        permits.append(
            PublicPermit(
                job_number=job_number,
                borough=row.get("borough", "").strip() or "UNKNOWN",
                bin_number=row.get("bin_number", "").strip(),
                street_name=row.get("street_name", "").strip() or "Unknown street",
                job_type=row.get("job_type", "").strip() or "UNK",
                permit_type=permit_type,
                work_type=work_type,
                permit_status=row.get("permit_status", "").strip() or "UNKNOWN",
                filing_status=row.get("filing_status", "").strip() or "UNKNOWN",
                issuance_date=parse_socrata_date(row.get("issuance_date", "")),
                expiration_date=parse_socrata_date(row.get("expiration_date", "")),
                job_start_date=parse_socrata_date(row.get("job_start_date", "")),
            )
        )
    if not permits:
        raise ValueError("Public dataset sample did not contain any usable permits")
    return permits


def work_package_for_permit(permit: PublicPermit) -> str:
    code = (permit.work_type or permit.permit_type).upper()
    if code == "PL":
        return "Plumbing"
    if code == "EQ":
        return "Equipment"
    if permit.permit_type.upper() == "AL" or permit.job_type.upper().startswith("A"):
        return "Alteration"
    return "General Construction"


def _activity_suffix(permit: PublicPermit, index: int) -> str:
    parts = (permit.permit_type, permit.work_type, f"{index:02d}")
    return "-".join("".join(ch for ch in part.upper() if ch.isalnum()) for part in parts if part)


def public_permit_schedule_rows(permits: list[PublicPermit], base_date: date = date(2026, 7, 1)) -> list[dict]:
    rows: list[dict] = []
    for index, permit in enumerate(permits, start=1):
        raw_duration = max(7, (permit.expiration_date - permit.job_start_date).days)
        duration = min(45, max(10, raw_duration // 12))
        planned_start = base_date + timedelta(days=(index - 1) * 4)
        planned_finish = planned_start + timedelta(days=duration)
        elapsed = max(0, min(duration, (date(2026, 7, 19) - planned_start).days))
        planned_progress = round((elapsed / duration) * 100, 1)
        variance = 12 if permit.filing_status.upper() == "RENEWAL" else 5 + (index % 4) * 3
        actual_progress = max(0.0, round(planned_progress - variance, 1))
        rows.append(
            {
                "activity_id": f"NYC-DOB-{permit.job_number}-{_activity_suffix(permit, index)}",
                "name": f"Public DOB {permit.work_label} permit - {permit.street_name.title()}, {permit.borough.title()}",
                "work_package": work_package_for_permit(permit),
                "zone": "NYC Public Permit Sample",
                "planned_start": planned_start,
                "planned_finish": planned_finish,
                "planned_progress": planned_progress,
                "actual_progress": actual_progress,
                "predecessors": [],
                "critical": index <= 3,
                "contractor": f"Public DOB filing {permit.job_type}/{permit.permit_type}",
                "source": "NYC DOB Permit Issuance public dataset",
                "source_job_number": permit.job_number,
                "source_bin": permit.bin_number,
                "source_status": permit.permit_status,
                "source_filing_status": permit.filing_status,
            }
        )
    return rows
