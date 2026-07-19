from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.core.config import settings
from app.main import app

OUT = ROOT / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1440, 900
BG = "#091017"
PANEL = "#101922"
PANEL2 = "#14212b"
LINE = "#263645"
TEXT = "#eaf0f5"
MUTED = "#8fa1af"
ACCENT = "#f6a821"
GREEN = "#65d7a7"
RED = "#ff7d89"
BLUE = "#5da7ff"

FONT = ImageFont.load_default()


client = TestClient(app)
token = client.post("/api/v1/auth/login", json={"email": "admin@buildtwin.local", "password": "BuildTwin123!"}).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}


def get(path: str) -> Any:
    response = client.get(path, headers=headers)
    response.raise_for_status()
    return response.json()


def media_path(url: str) -> Path | None:
    if not url.startswith("/media-files/"):
        return None
    path = settings.media_root / url.removeprefix("/media-files/")
    return path if path.exists() else None


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: Any, fill: str = TEXT) -> None:
    draw.text(xy, str(value), fill=fill, font=FONT)


def wrap(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, width: int, fill: str = MUTED, line_height: int = 17) -> int:
    y = xy[1]
    for line in textwrap.wrap(str(value), width=max(12, width // 8)):
        draw.text((xy[0], y), line, fill=fill, font=FONT)
        y += line_height
    return y


def card(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, value: Any, detail: str = "", tone: str = LINE) -> None:
    draw.rounded_rectangle(box, radius=10, fill=PANEL, outline=tone)
    x, y, _, _ = box
    text(draw, (x + 16, y + 14), title.upper(), MUTED)
    text(draw, (x + 16, y + 38), value, TEXT)
    if detail:
        wrap(draw, (x + 16, y + 64), detail, box[2] - box[0] - 30)


def status(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str) -> None:
    color = GREEN if value in {"complete", "completed", "approved", "accepted", "online", "live"} else RED if value in {"critical", "high", "delayed", "blocked", "offline", "rejected"} else ACCENT
    label = value.replace("_", " ").upper()
    w = 8 * len(label) + 16
    draw.rounded_rectangle((xy[0], xy[1], xy[0] + w, xy[1] + 22), radius=11, fill="#17232d", outline=color)
    text(draw, (xy[0] + 8, xy[1] + 6), label, color)


def display_activity_id(value: str) -> str:
    if not value.startswith("NYC-DOB-"):
        return value
    parts = value.split("-")
    return f"NYC-{parts[2]}-{parts[-1]}" if len(parts) > 4 else value


def progress(draw: ImageDraw.ImageDraw, xy: tuple[int, int], actual: float, planned: float = 0, width: int = 180) -> None:
    x, y = xy
    draw.rounded_rectangle((x, y, x + width, y + 7), radius=4, fill="#25343f")
    draw.rounded_rectangle((x, y, x + int(width * min(100, max(0, actual)) / 100), y + 7), radius=4, fill=BLUE)
    px = x + int(width * min(100, max(0, planned)) / 100)
    draw.rectangle((px, y - 3, px + 2, y + 10), fill=ACCENT)


def shell(title: str, subtitle: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 245, H), fill="#0b131b")
    draw.line((245, 0, 245, H), fill=LINE)
    draw.rounded_rectangle((24, 22, 62, 60), radius=8, fill=ACCENT)
    text(draw, (36, 36), "BT", "#17110a")
    text(draw, (74, 32), "BuildTwin Vision", TEXT)
    draw.rounded_rectangle((18, 88, 226, 150), radius=10, fill="#111d27", outline=LINE)
    text(draw, (34, 104), "PUBLIC DATA DEMO", ACCENT)
    wrap(draw, (34, 126), "NYC DOB permits + local evidence pipeline", 175)
    nav = ["Command Center", "Digital Twin", "4D Schedule", "Captures", "Progress", "Changes", "Safety", "Quality", "Risk", "Reports", "Cameras", "Alerts", "Audit"]
    y = 178
    for item in nav:
        fill = "#17232d" if item.lower() in title.lower() else "#0b131b"
        draw.rounded_rectangle((18, y, 226, y + 27), radius=7, fill=fill)
        text(draw, (34, y + 8), item, TEXT if fill != "#0b131b" else MUTED)
        y += 31
    draw.rectangle((245, 0, W, 112), fill="#0b1219")
    text(draw, (280, 28), "BUILDTWIN / PUBLIC DATA SAMPLE", ACCENT)
    text(draw, (280, 52), title, TEXT)
    wrap(draw, (280, 76), subtitle, 850)
    status(draw, (1250, 42), "live")
    return img, draw


def paste_evidence(img: Image.Image, box: tuple[int, int, int, int], url: str) -> None:
    path = media_path(url)
    if not path:
        ImageDraw.Draw(img).rectangle(box, fill="#071018", outline=LINE)
        return
    ev = Image.open(path).convert("RGB")
    ev.thumbnail((box[2] - box[0], box[3] - box[1]))
    x = box[0] + ((box[2] - box[0]) - ev.width) // 2
    y = box[1] + ((box[3] - box[1]) - ev.height) // 2
    ImageDraw.Draw(img).rectangle(box, fill="#071018", outline=LINE)
    img.paste(ev, (x, y))


def save(name: str, img: Image.Image) -> None:
    img.save(OUT / f"{name}.png")


dashboard = get("/api/v1/dashboard/executive?project_id=1")
zones = get("/api/v1/dashboard/progress?project_id=1")
activities = get("/api/v1/schedule/activities?project_id=1")
risk_rows = get("/api/v1/risk/activities?project_id=1")
dataset = get("/api/v1/datasets/public-demo?project_id=1")

img, d = shell("Command Center", "Planned-versus-actual control with NYC DOB public permit records mapped into the demo schedule.")
d.rounded_rectangle((280, 132, 1360, 178), radius=10, fill=PANEL2, outline="#355066")
text(d, (300, 148), dataset["title"], ACCENT)
text(d, (455, 148), f"{dataset['records']} public records | planned {dataset['planned_progress']}% | approved {dataset['approved_progress']}%", TEXT)
kpis = [
    ("Planned", f"{dashboard['planned_progress']}%", "Baseline"),
    ("Approved", f"{dashboard['approved_actual_progress']}%", f"{dashboard['schedule_variance']} pts variance"),
    ("Public permits", dashboard["public_permit_activities"], "NYC DOB sample"),
    ("At risk", dashboard["at_risk_activities"], f"{dashboard['delayed_activities']} delayed"),
    ("Safety", dashboard["critical_safety_events"], "open high/critical"),
    ("Evidence age", f"{dashboard['evidence_freshness_hours']}h", "latest observation"),
]
for i, k in enumerate(kpis):
    card(d, (280 + i * 180, 198, 445 + i * 180, 292), *k)
y = 330
for row in dashboard["activity_risk"][:8]:
    d.line((280, y - 10, 1040, y - 10), fill=LINE)
    text(d, (290, y), display_activity_id(row["external_id"]), ACCENT)
    wrap(d, (410, y), row["name"], 290, TEXT)
    progress(d, (720, y + 6), row["actual"], row["planned"], 170)
    text(d, (925, y), f"{row['variance']} pts", RED if row["variance"] < 0 else GREEN)
    text(d, (1010, y), row["risk_score"], ACCENT)
    y += 54
y = 330
for alert in dashboard["alerts"][:5]:
    status(d, (1080, y), alert["severity"])
    wrap(d, (1180, y), alert["title"], 160, TEXT)
    y += 64
save("command-center", img)

img, d = shell("4D Schedule", "Synthetic site activities plus NYC DOB public permit sample activities.")
y = 145
for row in activities[:13]:
    d.rounded_rectangle((280, y, 1360, y + 48), radius=8, fill=PANEL, outline=LINE)
    text(d, (295, y + 13), display_activity_id(row["external_id"]), ACCENT)
    wrap(d, (420, y + 10), row["name"], 430, TEXT)
    text(d, (885, y + 13), f"{row['planned_start']} -> {row['planned_finish']}", MUTED)
    progress(d, (1120, y + 18), row["approved_progress"], row["planned_progress"], 170)
    status(d, (1300, y + 13), row["status"])
    y += 56
save("schedule", img)

img, d = shell("Risk Forecast", "Heuristic delay-risk contributions for public permit sample and local site workflow.")
y = 145
for row in risk_rows[:8]:
    d.rounded_rectangle((280, y, 1360, y + 78), radius=8, fill=PANEL, outline=LINE)
    text(d, (300, y + 16), row["score"], ACCENT)
    text(d, (300, y + 38), row["band"], MUTED)
    text(d, (380, y + 14), f"{row['external_id']} - {row['activity']}", TEXT)
    factors = "; ".join(f"{f['name']} +{f['contribution']}" for f in row["factors"][:3])
    wrap(d, (380, y + 36), factors, 650)
    wrap(d, (990, y + 18), row["recommendation"], 330)
    y += 88
save("risk", img)

models = get("/api/v1/bim/models?project_id=1")
elements = get(f"/api/v1/bim/models/{next(x for x in models if x['status']=='completed')['id']}/elements")
img, d = shell("Digital Twin", "IFC element register linked to construction context.")
y = 145
for row in elements[:10]:
    d.rounded_rectangle((280, y, 1360, y + 54), radius=8, fill=PANEL, outline=LINE)
    text(d, (300, y + 16), row["element_type"], ACCENT)
    text(d, (475, y + 16), row["name"], TEXT)
    text(d, (820, y + 16), row["ifc_guid"], MUTED)
    progress(d, (1130, y + 20), row["progress_percent"], 0, 150)
    y += 62
save("digital-twin", img)

for name, title, path, key in [
    ("progress-review", "Progress Review", "/api/v1/progress/observations?project_id=1", "evidence_url"),
    ("change-analysis", "Change Analysis", "/api/v1/changes?project_id=1", "overlay_url"),
    ("safety", "Safety Operations", "/api/v1/safety/events?project_id=1", "evidence_url"),
    ("quality", "Quality Intelligence", "/api/v1/quality/observations?project_id=1", "evidence_url"),
]:
    rows = get(path)
    img, d = shell(title, "Evidence and review records generated by the local processing pipeline.")
    x, y = 280, 145
    for row in rows[:4]:
        d.rounded_rectangle((x, y, x + 500, y + 300), radius=10, fill=PANEL, outline=LINE)
        paste_evidence(img, (x + 12, y + 12, x + 488, y + 190), row.get(key, ""))
        label = row.get("activity") or row.get("candidate_type") or row.get("event_type") or f"Change {row.get('id')}"
        wrap(d, (x + 18, y + 205), str(label).replace("_", " "), 430, TEXT)
        status(d, (x + 18, y + 252), str(row.get("review_status") or row.get("status") or row.get("severity") or "record"))
        x += 530
        if x > 920:
            x, y = 280, y + 330
    save(name, img)

for name, title, path in [
    ("cameras", "Camera Health", "/api/v1/cameras?project_id=1"),
    ("alerts", "Alerts", "/api/v1/alerts?project_id=1"),
    ("reports", "Reports", "/api/v1/reports?project_id=1"),
    ("audit", "Audit Log", "/api/v1/audit?project_id=1"),
]:
    rows = get(path)
    img, d = shell(title, "Operational records from the seeded public-data demo.")
    y = 145
    for row in rows[:10]:
        d.rounded_rectangle((280, y, 1360, y + 54), radius=8, fill=PANEL, outline=LINE)
        text(d, (300, y + 16), str(row.get("id", "")), ACCENT)
        wrap(d, (360, y + 10), json.dumps(row, default=str)[:210], 880, TEXT)
        y += 62
    save(name, img)

for name, title, subtitle in [
    ("landing", "BuildTwin Vision", "Evidence-first 4D construction intelligence using public DOB permit samples and local vision outputs."),
    ("login", "Local Demo Login", "Use deterministic demo credentials; data is public/sample and not a customer deployment."),
    ("captures", "Site Captures", "Persisted image and MP4 evidence generated by the local demo pipeline."),
    ("pdf-report-preview", "PDF Report Preview", "Report generated from persisted KPIs, risks, alerts, and public permit sample metadata."),
]:
    img, d = shell(title, subtitle)
    d.rounded_rectangle((330, 240, 1120, 530), radius=18, fill=PANEL, outline=LINE)
    wrap(d, (380, 300), subtitle, 650, TEXT, 24)
    card(d, (390, 400, 560, 500), "Public records", dataset["records"], "NYC DOB")
    card(d, (590, 400, 760, 500), "Activities", len(activities), "Seeded schedule")
    card(d, (790, 400, 960, 500), "Reports", len(get("/api/v1/reports?project_id=1")), "PDF output")
    save(name, img)

print(f"rendered {len(list(OUT.glob('*.png')))} PNG previews from FastAPI seeded data")
