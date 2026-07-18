from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import Activity, Alert, Camera, ProgressObservation, QualityObservation, SafetyEvent


def executive_dashboard(db: Session, org_id: int, project_id: int) -> dict:
    activities=db.scalars(select(Activity).where(Activity.organization_id==org_id,Activity.project_id==project_id)).all()
    if not activities:
        planned=approved=ai=0.0
    else:
        planned=sum(a.planned_progress for a in activities)/len(activities)
        approved=sum(a.approved_progress for a in activities)/len(activities)
        ai=sum(a.ai_progress for a in activities)/len(activities)
    delayed=sum(1 for a in activities if a.approved_progress+5<a.planned_progress)
    at_risk=sum(1 for a in activities if a.risk_score>=40)
    critical_safety=db.scalar(select(func.count()).select_from(SafetyEvent).where(SafetyEvent.organization_id==org_id,SafetyEvent.project_id==project_id,SafetyEvent.status!="resolved",SafetyEvent.severity.in_(["high","critical"]))) or 0
    open_quality=db.scalar(select(func.count()).select_from(QualityObservation).where(QualityObservation.organization_id==org_id,QualityObservation.project_id==project_id,QualityObservation.status.notin_(["closed","rejected"]))) or 0
    cameras=db.scalars(select(Camera).where(Camera.organization_id==org_id,Camera.project_id==project_id)).all()
    latest_obs=db.scalar(select(func.max(ProgressObservation.created_at)).where(ProgressObservation.organization_id==org_id,ProgressObservation.project_id==project_id))
    freshness=(datetime.utcnow()-latest_obs).total_seconds()/3600 if latest_obs else None
    alerts=db.scalars(select(Alert).where(Alert.organization_id==org_id,Alert.project_id==project_id).order_by(Alert.created_at.desc()).limit(8)).all()
    return {
      "project_id":project_id,
      "planned_progress":round(planned,1),"approved_actual_progress":round(approved,1),"ai_estimated_progress":round(ai,1),
      "schedule_variance":round(approved-planned,1),"delayed_activities":delayed,"at_risk_activities":at_risk,
      "critical_safety_events":critical_safety,"open_quality_observations":open_quality,
      "active_cameras":sum(c.status=="online" for c in cameras),"stale_cameras":sum(c.status!="online" for c in cameras),
      "evidence_freshness_hours":round(freshness,1) if freshness is not None else None,
      "alerts":[{"id":a.id,"severity":a.severity,"title":a.title,"message":a.message,"status":a.status,"created_at":a.created_at.isoformat()} for a in alerts],
      "activity_risk":[{"id":a.id,"external_id":a.external_id,"name":a.name,"planned":a.planned_progress,"actual":a.approved_progress,"ai":a.ai_progress,"variance":round(a.approved_progress-a.planned_progress,1),"risk_score":a.risk_score,"critical":a.critical,"status":a.status} for a in sorted(activities,key=lambda x:x.risk_score,reverse=True)[:10]]
    }
