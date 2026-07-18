from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def create_progress_report(path: str, project: dict, kpis: dict, risks: list[dict], alerts: list[dict]) -> str:
    output=Path(path); output.parent.mkdir(parents=True, exist_ok=True)
    styles=getSampleStyleSheet(); story=[]
    story.append(Paragraph("BuildTwin Vision — Weekly Progress Intelligence", styles["Title"]))
    story.append(Paragraph(f"Project: {project['name']} ({project['code']})", styles["Heading2"]))
    story.append(Paragraph(f"Location: {project.get('location','')}", styles["BodyText"])); story.append(Spacer(1,12))
    rows=[["Metric","Value"]]+[[k.replace('_',' ').title(),str(v)] for k,v in kpis.items()]
    table=Table(rows, colWidths=[250,180]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#243044')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),0.5,colors.grey),('PADDING',(0,0),(-1,-1),7)])); story.append(table)
    story.append(Spacer(1,16)); story.append(Paragraph("Highest-risk activities", styles["Heading2"]))
    risk_rows=[["Activity","Score","Band","Primary factor"]]+[[r['activity'],r['score'],r['band'],(r.get('factors') or [{}])[0].get('reason','')] for r in risks[:6]]
    story.append(Table(risk_rows, colWidths=[170,55,70,190], repeatRows=1))
    story.append(Spacer(1,16)); story.append(Paragraph("Open alerts", styles["Heading2"]))
    for alert in alerts[:8]: story.append(Paragraph(f"• <b>{alert['severity'].upper()}</b> — {alert['title']}: {alert['message']}", styles["BodyText"]))
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=32,leftMargin=32,topMargin=34,bottomMargin=34); doc.build(story)
    return str(output)
