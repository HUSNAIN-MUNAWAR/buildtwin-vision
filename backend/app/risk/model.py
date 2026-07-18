from __future__ import annotations

from datetime import date


def calculate_delay_risk(*, planned_progress: float, actual_progress: float, critical: bool, planned_finish: date, delayed_predecessors: int, evidence_age_hours: float, safety_events: int, quality_issues: int) -> dict:
    variance=max(0.0, planned_progress-actual_progress)
    overdue=max(0,(date.today()-planned_finish).days)
    components=[
        ("progress_variance", min(35.0, variance*0.7), f"Actual progress trails plan by {variance:.1f} points"),
        ("critical_path", 18.0 if critical else 0.0, "Activity is on the critical path" if critical else "Not critical"),
        ("delayed_predecessors", min(18.0, delayed_predecessors*9.0), f"{delayed_predecessors} delayed predecessor(s)"),
        ("evidence_freshness", min(12.0, max(0,evidence_age_hours-24)/12), f"Latest accepted evidence is {evidence_age_hours:.0f} hours old"),
        ("overdue", min(10.0, overdue*2.0), f"Planned finish is {overdue} day(s) overdue"),
        ("operational_interruptions", min(7.0, safety_events*2 + quality_issues*2.5), f"{safety_events} safety and {quality_issues} quality issue(s)"),
    ]
    score=round(min(100.0,sum(x[1] for x in components)),1)
    band="low" if score<25 else "medium" if score<50 else "high" if score<75 else "critical"
    factors=[{"name":name,"contribution":round(points,1),"reason":reason} for name,points,reason in components if points>0]
    recommendation=("Escalate a recovery plan and validate downstream constraints today." if band in {"high","critical"} else "Review fresh evidence and confirm remaining crew/material capacity." if band=="medium" else "Continue monitoring through the normal look-ahead review.")
    return {"score":score,"band":band,"factors":factors,"recommendation":recommendation,"model_version":"heuristic-v1"}
