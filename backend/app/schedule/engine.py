from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path

import networkx as nx

REQUIRED = {"activity_id","name","planned_start","planned_finish","planned_progress","actual_progress","predecessors"}


def _date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_schedule(path: str) -> list[dict]:
    p=Path(path)
    if p.suffix.lower()==".csv":
        with p.open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    elif p.suffix.lower()==".json": rows=json.loads(p.read_text())
    else: raise ValueError("Schedule must be CSV or JSON")
    if not rows: raise ValueError("Schedule is empty")
    missing=REQUIRED-set(rows[0])
    if missing: raise ValueError(f"Missing schedule fields: {sorted(missing)}")
    ids=set(); normalized=[]
    for row in rows:
        aid=row["activity_id"].strip()
        if aid in ids: raise ValueError(f"Duplicate activity ID: {aid}")
        ids.add(aid)
        start=_date(row["planned_start"]); finish=_date(row["planned_finish"])
        if finish < start: raise ValueError(f"Activity {aid} finishes before it starts")
        planned=float(row["planned_progress"]); actual=float(row["actual_progress"])
        if not (0<=planned<=100 and 0<=actual<=100): raise ValueError(f"Activity {aid} has invalid progress")
        predecessors=[x.strip() for x in row.get("predecessors","").split("|") if x.strip()]
        normalized.append({**row,"activity_id":aid,"planned_start":start,"planned_finish":finish,"planned_progress":planned,"actual_progress":actual,"predecessors":predecessors,"critical":str(row.get("critical","")).lower() in {"1","true","yes"}})
    for row in normalized:
        missing_preds=[p for p in row["predecessors"] if p not in ids]
        if missing_preds: raise ValueError(f"Activity {row['activity_id']} references missing predecessors: {missing_preds}")
    graph=nx.DiGraph(); graph.add_nodes_from(ids)
    for row in normalized:
        graph.add_edges_from((p,row["activity_id"]) for p in row["predecessors"])
    if not nx.is_directed_acyclic_graph(graph): raise ValueError("Schedule contains a circular dependency")
    return normalized


def critical_path(activity_rows: list[dict], dependencies: list[tuple[str,str]]) -> list[str]:
    graph=nx.DiGraph()
    for a in activity_rows:
        duration=max(1,(a["planned_finish"]-a["planned_start"]).days+1)
        graph.add_node(a["activity_id"], duration=duration)
    graph.add_edges_from(dependencies)
    if not nx.is_directed_acyclic_graph(graph): raise ValueError("Dependency graph is cyclic")
    return nx.dag_longest_path(graph, weight="duration")
