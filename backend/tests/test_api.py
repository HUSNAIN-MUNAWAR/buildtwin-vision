from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.entities import Organization, Project


def test_health_and_ready(client):
    assert client.get("/api/v1/health").status_code==200
    assert client.get("/api/v1/ready").json()["database"]=="ok"


def test_login_rejects_bad_password(client):
    assert client.post("/api/v1/auth/login",json={"email":"admin@buildtwin.local","password":"wrong"}).status_code==401


def test_dashboard_is_persisted_and_coherent(client,headers):
    data=client.get("/api/v1/dashboard/executive?project_id=1",headers=headers).json()
    assert data["planned_progress"]>data["approved_actual_progress"]
    assert data["critical_safety_events"]==1
    assert data["at_risk_activities"] >= 1
    assert data["public_permit_activities"]==12
    assert data["dataset_label"]=="NYC DOB Permit Issuance public sample"
    assert len(data["activity_risk"])==10


def test_public_dataset_summary(client,headers):
    data=client.get("/api/v1/datasets/public-demo?project_id=1",headers=headers).json()
    assert data["title"]=="DOB Permit Issuance"
    assert data["publisher"]=="New York City Department of Buildings (DOB)"
    assert data["records"]==12
    assert all(x.startswith("NYC-DOB-") for x in data["activity_ids"])


def test_organization_isolation(client,headers):
    with SessionLocal() as db:
        org=Organization(name="Isolation Test Org"); db.add(org); db.flush()
        project=Project(organization_id=org.id,name="Foreign Project",code="FOREIGN"); db.add(project); db.commit(); pid=project.id
    assert client.get(f"/api/v1/projects/{pid}",headers=headers).status_code==404


def test_invalid_zone_polygon_rejected(client,headers):
    response=client.post("/api/v1/zones",headers=headers,json={"project_id":1,"name":"Bad","polygon":[[0,0],[1,1]],"restricted":False})
    assert response.status_code==422


def test_ifc_elements_are_real(client,headers):
    models=client.get("/api/v1/bim/models?project_id=1",headers=headers).json()
    completed=next(x for x in models if x["status"]=="completed")
    elements=client.get(f"/api/v1/bim/models/{completed['id']}/elements",headers=headers).json()
    assert completed["element_count"]==len(elements)>=10
    assert any("Wall" in x["element_type"] for x in elements)


def test_schedule_graph_and_critical_path(client,headers):
    graph=client.get("/api/v1/schedule/dependency-graph?project_id=1",headers=headers).json()
    cp=client.get("/api/v1/schedule/critical-path?project_id=1",headers=headers).json()["critical_path"]
    assert len(graph["edges"])>=4
    assert cp[0]=="A100" and "A130" in cp
    activities=client.get("/api/v1/schedule/activities?project_id=1",headers=headers).json()
    assert any(a["status"]=="blocked" for a in activities)
    assert any(a["external_id"].startswith("NYC-DOB-") for a in activities)


def test_video_job_contains_decoded_frames(client,headers):
    jobs=client.get("/api/v1/processing/jobs?project_id=1",headers=headers).json()
    completed=next(j for j in jobs if j["status"]=="completed")
    assert completed["metrics"]["decoded_frames"]==72
    assert completed["metrics"]["sampled_frames"]==6


def test_change_comparison_has_real_output(client,headers):
    changes=client.get("/api/v1/changes?project_id=1",headers=headers).json()
    assert changes[0]["changed_area_percent"]>5
    assert changes[0]["overlay_url"].endswith("change_overlay.jpg")
    assert Path(settings.media_root/"outputs"/"change_1"/"change_overlay.jpg").exists()


def test_progress_review_updates_activity_and_audit(client,headers):
    observations=client.get("/api/v1/progress/observations?project_id=1&review_status=pending",headers=headers).json()
    obs=observations[0]
    response=client.post(f"/api/v1/progress/observations/{obs['id']}/review",headers=headers,json={"decision":"approved","approved_progress":26,"notes":"Verified in integration test"})
    assert response.status_code==200 and response.json()["approved_progress"]==26
    activities=client.get("/api/v1/schedule/activities?project_id=1",headers=headers).json()
    assert next(a for a in activities if a["id"]==obs["activity_id"])["approved_progress"]==26
    audit=client.get("/api/v1/audit?project_id=1",headers=headers).json()
    assert any(e["action"]=="progress_observation.approved" and e["after_values"].get("approved_progress")==26 for e in audit)


def test_risk_is_explainable(client,headers):
    risks=client.get("/api/v1/risk/activities?project_id=1",headers=headers).json()
    assert risks[0]["score"]>=risks[-1]["score"]
    assert risks[0]["factors"] and risks[0]["recommendation"]


def test_safety_quality_alerts(client,headers):
    safety=client.get("/api/v1/safety/events?project_id=1",headers=headers).json()
    quality=client.get("/api/v1/quality/observations?project_id=1",headers=headers).json()
    alerts=client.get("/api/v1/alerts?project_id=1",headers=headers).json()
    assert safety[0]["event_type"]=="person_in_restricted_zone"
    assert any(q["status"]=="rejected" for q in quality)
    assert any(a["alert_type"]=="camera_offline" for a in alerts)


def test_report_download(client,headers):
    reports=client.get("/api/v1/reports?project_id=1",headers=headers).json()
    response=client.get(reports[0]["download_url"],headers=headers)
    assert response.status_code==200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")
