from sqlalchemy.orm import Session

from app.models.entities import AuditEvent, User


def record_audit(db: Session, user: User | None, action: str, entity_type: str, entity_id: int | None, *, project_id: int | None=None, before: dict | None=None, after: dict | None=None, correlation_id: str="") -> AuditEvent:
    event=AuditEvent(organization_id=user.organization_id if user else 1,project_id=project_id,actor_id=user.id if user else None,action=action,entity_type=entity_type,entity_id=entity_id,before_values=before or {},after_values=after or {},correlation_id=correlation_id)
    db.add(event); db.flush(); return event
