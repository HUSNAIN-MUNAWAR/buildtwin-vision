from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.bim.ifc_parser import parse_ifc
from app.core.config import settings
from app.core.security import hash_password
from app.models.entities import *
from app.reports.pdf import create_progress_report
from app.risk.model import calculate_delay_risk
from app.services.dashboard import executive_dashboard
from app.vision.change_detection import compare_images
from app.vision.video_reader import process_video


def generate_assets() -> dict[str,str]:
    base=settings.media_root
    for d in ["ifc","schedules","images","videos","outputs","reports"]: (base/d).mkdir(parents=True,exist_ok=True)
    ifc=base/"ifc"/"northstar_minimal.ifc"
    ifc.write_text("""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('ViewDefinition [CoordinationView]'),'2;1');
FILE_NAME('northstar_minimal.ifc','2026-07-19T00:00:00',('BuildTwin'),('OpenAI'),'BuildTwin Generator','BuildTwin Vision','');
FILE_SCHEMA(('IFC4'));
ENDSEC;
DATA;
#10=IFCPROJECT('3vBProjectGuid0000000001',$,'Northstar Medical Center Expansion',$,$,$,$,$,$);
#20=IFCBUILDINGSTOREY('3vBStoreyGround00000001',$,'Ground Floor',$,$,$,$,$,$,0.0);
#21=IFCBUILDINGSTOREY('3vBStoreyLevel100000001',$,'Level 1',$,$,$,$,$,$,4.2);
#100=IFCWALL('3vBWallGroundEast000001',$,'GF East Shear Wall',$,$,$,$,$,$);
#101=IFCSLAB('3vBSlabGroundEast000001',$,'GF East Structural Slab',$,$,$,$,$,$);
#102=IFCCOLUMN('3vBColumnLevel1Core001',$,'L1 Core Column C01',$,$,$,$,$,$);
#103=IFCBEAM('3vBBeamLevel1Core00001',$,'L1 Core Beam B01',$,$,$,$,$,$);
#104=IFCDOOR('3vBDoorPatientRoom00001',$,'Patient Room Door D01',$,$,$,$,$,$,$,$,$,$);
#105=IFCWINDOW('3vBWindowPatient000001',$,'Patient Room Window W01',$,$,$,$,$,$,$,$,$,$,$);
#106=IFCSPACE('3vBSpacePatientRooms001',$,'Level 1 Patient Rooms',$,$,$,$,$,$,$);
#107=IFCROOF('3vBRoofMechanical000001',$,'Roof Mechanical Deck',$,$,$,$,$,$);
#108=IFCSTAIR('3vBStairCore000000001',$,'Main Core Stair',$,$,$,$,$,$);
#109=IFCRAILING('3vBRailingParking00001',$,'Parking Deck Railing',$,$,$,$,$,$);
ENDSEC;
END-ISO-10303-21;
""",encoding="utf-8")
    sched=base/"schedules"/"northstar_schedule.csv"
    rows=[
      ["A100","Foundations - Main Clinical Building","Foundations","Ground Floor East Wing","2026-05-01","2026-06-10","100","100","","true","Atlas Civil"],
      ["A110","Ground Floor Structural Slab","Structural Concrete","Ground Floor East Wing","2026-06-05","2026-07-05","100","96","A100","true","Prime Concrete"],
      ["A120","Level 1 Core Columns","Structural Concrete","Level 1 Core","2026-06-28","2026-07-18","95","62","A110","true","Prime Concrete"],
      ["A130","Level 1 Core Beams","Structural Concrete","Level 1 Core","2026-07-12","2026-08-03","36","18","A120","true","Prime Concrete"],
      ["A140","Patient Room Masonry","Masonry","Level 1 Patient Rooms","2026-07-15","2026-08-18","14","20","A120","false","MasonWorks"],
      ["A150","Roof Mechanical Curbs","Mechanical","Roof Mechanical Zone","2026-08-01","2026-08-19","0","0","A130","false","Northstar MEP"],
      ["A160","Parking Deck Railing","Steel","Parking Deck Zone A","2026-07-01","2026-07-28","68","68","","false","SteelLine"],
      ["A170","Utility Trench Plumbing","Plumbing","Utility Trench","2026-06-25","2026-07-25","80","72","","false","Northstar MEP"],
    ]
    with sched.open("w",newline="",encoding="utf-8") as f:
      w=csv.writer(f); w.writerow(["activity_id","name","work_package","zone","planned_start","planned_finish","planned_progress","actual_progress","predecessors","critical","contractor"]); w.writerows(rows)
    baseline=base/"images"/"ground_east_baseline.jpg"; current=base/"images"/"ground_east_current.jpg"
    img: np.ndarray = np.full((540,960,3),215,np.uint8); cv2.rectangle(img,(70,380),(890,500),(110,110,110),-1); cv2.line(img,(80,380),(880,380),(50,50,50),5); cv2.putText(img,"NORTHSTAR - BASELINE",(30,45),cv2.FONT_HERSHEY_SIMPLEX,1,(30,40,50),2); cv2.imwrite(str(baseline),img)
    img2=img.copy(); cv2.rectangle(img2,(180,170),(260,380),(145,145,145),-1); cv2.rectangle(img2,(420,135),(500,380),(145,145,145),-1); cv2.rectangle(img2,(650,190),(730,380),(145,145,145),-1); cv2.line(img2,(150,340),(760,120),(80,80,80),10); cv2.circle(img2,(770,330),24,(20,20,210),-1); cv2.rectangle(img2,(753,355),(787,420),(40,160,220),-1); cv2.putText(img2,"CURRENT CAPTURE",(650,45),cv2.FONT_HERSHEY_SIMPLEX,.75,(20,20,20),2); cv2.imwrite(str(current),img2)
    video = base / "videos" / "level1_progress.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # type: ignore[attr-defined]
    writer = cv2.VideoWriter(str(video), fourcc, 12, (640, 360))
    for i in range(72):
      frame: np.ndarray = np.full((360,640,3),205,np.uint8); cv2.rectangle(frame,(35,280),(605,338),(100,100,100),-1)
      height=min(190,40+i*2); cv2.rectangle(frame,(150,280-height),(205,280),(135,135,135),-1); cv2.rectangle(frame,(340,280-height),(395,280),(135,135,135),-1)
      x=70+(i*7)%500; cv2.circle(frame,(x,260),14,(10,10,200),-1); cv2.rectangle(frame,(x-10,274),(x+10,318),(30,155,230),-1)
      cv2.putText(frame,f"Northstar synthetic capture frame {i}",(15,25),cv2.FONT_HERSHEY_SIMPLEX,.55,(30,30,30),1); writer.write(frame)
    writer.release()
    corrupted=base/"videos"/"corrupted_capture.mp4"; corrupted.write_bytes(b"not an mp4")
    return {"ifc":str(ifc),"schedule":str(sched),"baseline":str(baseline),"current":str(current),"video":str(video),"corrupted":str(corrupted)}


def reset_database(db: Session) -> None:
    for model in [Report,AuditEvent,Alert,RiskAssessment,QualityObservation,SafetyEvent,ProgressObservation,ChangeComparison,ProcessingJob,MediaAsset,Camera,ActivityBIMLink,ScheduleDependency,Activity,BIMElement,BIMModel,WorkPackage,Zone,Floor,Building,Project,User,Organization]:
      db.execute(delete(model))
    db.commit()


def seed_database(db: Session, reset: bool=True) -> dict:
    if reset: reset_database(db)
    assets=generate_assets()
    org=Organization(name="Northstar Construction Group"); db.add(org); db.flush()
    admin=User(organization_id=org.id,email="admin@buildtwin.local",full_name="Ayesha Khan",password_hash=hash_password("BuildTwin123!"),role=Role.ADMIN.value)
    reviewer=User(organization_id=org.id,email="reviewer@buildtwin.local",full_name="Omar Siddiqui",password_hash=hash_password("BuildTwin123!"),role=Role.REVIEWER.value)
    safety_user=User(organization_id=org.id,email="safety@buildtwin.local",full_name="Sara Malik",password_hash=hash_password("BuildTwin123!"),role=Role.SAFETY.value); db.add_all([admin,reviewer,safety_user]); db.flush()
    project=Project(organization_id=org.id,name="Northstar Medical Center Expansion",code="NSMC-26",location="Islamabad Demonstration Site",start_date=date(2026,5,1),finish_date=date(2027,8,30)); db.add(project); db.flush()
    b1=Building(organization_id=org.id,project_id=project.id,name="Main Clinical Building"); b2=Building(organization_id=org.id,project_id=project.id,name="Parking Structure"); b3=Building(organization_id=org.id,project_id=project.id,name="Utility Block"); db.add_all([b1,b2,b3]); db.flush()
    floor_names=[("Basement",-4.0),("Ground Floor",0),("Level 1",4.2),("Level 2",8.4),("Roof",12.6)]
    floors={}
    for name,elev in floor_names:
      f=Floor(organization_id=org.id,building_id=b1.id,name=name,elevation_m=elev); db.add(f); db.flush(); floors[name]=f
    zonespec=[("Ground Floor East Wing","Ground Floor",[[0,0],[960,0],[960,540],[0,540]],False),("Ground Floor West Wing","Ground Floor",[[0,0],[480,0],[480,540],[0,540]],False),("Level 1 Core","Level 1",[[100,80],[540,80],[540,480],[100,480]],True),("Level 1 Patient Rooms","Level 1",[[540,80],[950,80],[950,500],[540,500]],False),("Roof Mechanical Zone","Roof",[[100,100],[850,100],[850,500],[100,500]],True),("Parking Deck Zone A",None,[[0,0],[900,0],[900,500],[0,500]],False),("Utility Trench",None,[[0,250],[960,250],[960,540],[0,540]],True)]
    zones={}
    for name,fname,poly,restricted in zonespec:
      z=Zone(organization_id=org.id,project_id=project.id,floor_id=floors[fname].id if fname else None,name=name,polygon=poly,restricted=restricted,stale_after_hours=48 if name=="Roof Mechanical Zone" else 72); db.add(z); db.flush(); zones[name]=z
    wp_names=["Earthworks","Foundations","Structural Concrete","Steel","Masonry","Mechanical","Electrical","Plumbing","Façade","Interior Fit-Out","Roofing","External Works"]
    wps={}
    for name in wp_names:
      w=WorkPackage(organization_id=org.id,project_id=project.id,name=name,discipline=name); db.add(w); db.flush(); wps[name]=w
    model=BIMModel(organization_id=org.id,project_id=project.id,filename=Path(assets["ifc"]).name,status="processing"); db.add(model); db.flush()
    parsed,failures=parse_ifc(assets["ifc"])
    bim=[]
    type_zone={"IFCWALL":"Ground Floor East Wing","IFCSLAB":"Ground Floor East Wing","IFCCOLUMN":"Level 1 Core","IFCBEAM":"Level 1 Core","IFCDOOR":"Level 1 Patient Rooms","IFCWINDOW":"Level 1 Patient Rooms","IFCSPACE":"Level 1 Patient Rooms","IFCROOF":"Roof Mechanical Zone","IFCSTAIR":"Level 1 Core","IFCRAILING":"Parking Deck Zone A"}
    for i,e in enumerate(parsed):
      zname=next((z for typ,z in type_zone.items() if typ in e.element_type.upper()),"Ground Floor East Wing")
      be=BIMElement(organization_id=org.id,project_id=project.id,model_id=model.id,ifc_guid=e.ifc_guid,element_type=e.element_type,name=e.name,floor_name="Level 1" if "Level1" in e.ifc_guid or "Patient" in e.name or "Core" in e.name else "Ground Floor",zone_id=zones[zname].id,discipline="Structural" if any(x in e.element_type.upper() for x in ["WALL","SLAB","COLUMN","BEAM"]) else "Architectural",material="Concrete" if i<5 else "Mixed",bbox={"min":[i*1.2,0,0],"max":[i*1.2+1,0.4,3.2]},progress_status="in_progress" if i<5 else "planned",progress_percent=60 if i<5 else 0,confidence=.82); db.add(be); db.flush(); bim.append(be)
    model.status="completed"; model.element_count=len(bim); model.failure_count=len(failures); model.report={"parser":"STEP lightweight parser","supported_elements":len(bim),"failures":failures,"source":assets["ifc"]}
    failed_model=BIMModel(organization_id=org.id,project_id=project.id,filename="damaged_export.ifc",status="failed",element_count=0,failure_count=1,report={"error":"Missing ISO-10303-21 header"}); db.add(failed_model)
    from app.schedule.engine import load_schedule
    schedule_rows=load_schedule(assets["schedule"]); acts={}
    for row in schedule_rows:
      a=Activity(organization_id=org.id,project_id=project.id,external_id=row["activity_id"],name=row["name"],work_package_id=wps[row["work_package"]].id,zone_id=zones[row["zone"]].id,planned_start=row["planned_start"],planned_finish=row["planned_finish"],planned_progress=row["planned_progress"],approved_progress=row["actual_progress"],ai_progress=max(0,min(100,row["actual_progress"]+(3 if row["activity_id"] in {"A120","A140"} else 0))),status="blocked" if row["activity_id"]=="A150" else "delayed" if row["actual_progress"]+8<row["planned_progress"] else "in_progress" if row["actual_progress"]<100 else "complete",critical=row["critical"],contractor=row["contractor"]); db.add(a); db.flush(); acts[a.external_id]=a
    for row in schedule_rows:
      for pred in row["predecessors"]: db.add(ScheduleDependency(organization_id=org.id,project_id=project.id,predecessor_id=acts[pred].id,successor_id=acts[row["activity_id"]].id))
    for be in bim:
      aid="A120" if "COLUMN" in be.element_type.upper() else "A130" if "BEAM" in be.element_type.upper() else "A110" if "SLAB" in be.element_type.upper() or "WALL" in be.element_type.upper() else "A140"
      db.add(ActivityBIMLink(organization_id=org.id,activity_id=acts[aid].id,bim_element_id=be.id,score=.88,reason="Matched by compatible IFC class, floor and zone",status="accepted"))
    cam1=Camera(organization_id=org.id,project_id=project.id,zone_id=zones["Ground Floor East Wing"].id,name="GF East Fixed Cam 01",status="online",last_seen_at=datetime.utcnow()-timedelta(minutes=5)); cam2=Camera(organization_id=org.id,project_id=project.id,zone_id=zones["Roof Mechanical Zone"].id,name="Roof Cam 02",status="offline",last_seen_at=datetime.utcnow()-timedelta(days=3),last_error="Heartbeat timeout"); db.add_all([cam1,cam2]); db.flush()
    base_asset=MediaAsset(organization_id=org.id,project_id=project.id,zone_id=zones["Ground Floor East Wing"].id,camera_id=cam1.id,kind="image",filename=Path(assets["baseline"]).name,path=assets["baseline"],captured_at=datetime.utcnow()-timedelta(days=8),synthetic=True,metadata_json={"purpose":"baseline"})
    cur_asset=MediaAsset(organization_id=org.id,project_id=project.id,zone_id=zones["Ground Floor East Wing"].id,camera_id=cam1.id,kind="image",filename=Path(assets["current"]).name,path=assets["current"],captured_at=datetime.utcnow()-timedelta(hours=3),synthetic=True,metadata_json={"purpose":"current"})
    vid_asset=MediaAsset(organization_id=org.id,project_id=project.id,zone_id=zones["Level 1 Core"].id,camera_id=cam1.id,kind="video",filename=Path(assets["video"]).name,path=assets["video"],captured_at=datetime.utcnow()-timedelta(hours=4),synthetic=True); db.add_all([base_asset,cur_asset,vid_asset]); db.flush()
    change=compare_images(base_asset.path,cur_asset.path,str(settings.media_root/"outputs"/"change_1")); comp=ChangeComparison(organization_id=org.id,project_id=project.id,zone_id=zones["Ground Floor East Wing"].id,baseline_asset_id=base_asset.id,current_asset_id=cur_asset.id,changed_area_percent=change.changed_area_percent,alignment_status=change.alignment_status,confidence=change.confidence,overlay_path=change.overlay_path,review_status="accepted",reviewer_notes="Change corresponds to installed columns and temporary works"); db.add(comp)
    vm=process_video(vid_asset.path,str(settings.media_root/"outputs"/"video_1"),sample_every=12,max_frames=72); job=ProcessingJob(organization_id=org.id,project_id=project.id,media_asset_id=vid_asset.id,job_type="video_processing",status="completed",progress=100,metrics=vm.__dict__,output_reference=vm.output_paths[-1],started_at=datetime.utcnow()-timedelta(minutes=1),completed_at=datetime.utcnow()); db.add(job)
    failed=ProcessingJob(organization_id=org.id,project_id=project.id,job_type="video_processing",status="failed",progress=0,error_code="VIDEO_DECODE_FAILED",error_message="OpenCV could not open corrupted_capture.mp4",metrics={"input":assets["corrupted"]},completed_at=datetime.utcnow()); db.add(failed)
    obs1=ProgressObservation(organization_id=org.id,project_id=project.id,activity_id=acts["A120"].id,zone_id=zones["Level 1 Core"].id,media_asset_id=vid_asset.id,observation_type="visual_change_progress",estimated_progress=65,previous_progress=55,confidence=.87,algorithm="zone-change-and-structural-occupancy",algorithm_version="1.0.0",evidence_path=vm.output_paths[-1],review_status="approved",reviewer_id=reviewer.id,review_notes="Accepted after matching column installation quantities",reviewed_at=datetime.utcnow()-timedelta(hours=2)); acts["A120"].approved_progress=65
    obs2=ProgressObservation(organization_id=org.id,project_id=project.id,activity_id=acts["A130"].id,zone_id=zones["Level 1 Core"].id,media_asset_id=vid_asset.id,observation_type="visual_change_progress",estimated_progress=24,previous_progress=18,confidence=.48,algorithm="zone-change-and-edge-density",algorithm_version="1.0.0",evidence_path=vm.output_paths[2],review_status="pending",review_notes="Low confidence: temporary obstruction"); db.add_all([obs1,obs2])
    safety=SafetyEvent(organization_id=org.id,project_id=project.id,zone_id=zones["Level 1 Core"].id,camera_id=cam1.id,event_type="person_in_restricted_zone",severity="high",confidence=.91,evidence_path=vm.output_paths[3],detection_boxes=[{"x1":290,"y1":150,"x2":345,"y2":318,"track_id":7}],status="open",first_seen=datetime.utcnow()-timedelta(hours=5),last_seen=datetime.utcnow()-timedelta(hours=5,minutes=-3),assigned_to=safety_user.id,notes="Track-level deduplicated event; verify permit-to-work",dedupe_key="cam1-zone-core-track7-20260718")
    quality1=QualityObservation(organization_id=org.id,project_id=project.id,zone_id=zones["Ground Floor East Wing"].id,activity_id=acts["A110"].id,candidate_type="surface_anomaly_candidate",severity="medium",confidence=.72,status="open",evidence_path=change.overlay_path,corrective_action="Inspect slab surface and record closure evidence",due_date=date.today()+timedelta(days=2))
    quality2=QualityObservation(organization_id=org.id,project_id=project.id,zone_id=zones["Level 1 Patient Rooms"].id,activity_id=acts["A140"].id,candidate_type="crack_like_line_candidate",severity="low",confidence=.36,status="rejected",evidence_path=assets["current"],reviewer_notes="Rejected: formwork edge, not a defect"); db.add_all([safety,quality1,quality2]); db.flush()
    db.add_all([Alert(organization_id=org.id,project_id=project.id,alert_type="critical_delay_risk",severity="critical",title="Level 1 Core Columns require recovery review",message="Critical activity is materially behind plan and blocks core beam work.",entity_type="activity",entity_id=acts["A120"].id),Alert(organization_id=org.id,project_id=project.id,alert_type="restricted_zone_intrusion",severity="high",title="Restricted-zone entry detected",message="Person track 7 entered Level 1 Core during a controlled work window.",entity_type="safety_event",entity_id=safety.id),Alert(organization_id=org.id,project_id=project.id,alert_type="camera_offline",severity="medium",title="Roof camera offline",message="Roof Cam 02 has not reported for more than 72 hours.",entity_type="camera",entity_id=cam2.id),Alert(organization_id=org.id,project_id=project.id,alert_type="stale_progress_evidence",severity="medium",title="Roof Mechanical Zone evidence is stale",message="No accepted visual evidence exists within the configured freshness window.",entity_type="zone",entity_id=zones["Roof Mechanical Zone"].id)])
    db.flush()
    dep_by_succ={a.id:0 for a in acts.values()}
    for dep in db.scalars(select(ScheduleDependency).where(ScheduleDependency.project_id==project.id)).all():
      pred=db.get(Activity,dep.predecessor_id)
      if pred and pred.approved_progress+5<pred.planned_progress: dep_by_succ[dep.successor_id]+=1
    for a in acts.values():
      risk=calculate_delay_risk(planned_progress=a.planned_progress,actual_progress=a.approved_progress,critical=a.critical,planned_finish=a.planned_finish,delayed_predecessors=dep_by_succ[a.id],evidence_age_hours=96 if a.external_id=="A150" else 8,safety_events=1 if a.zone_id==zones["Level 1 Core"].id else 0,quality_issues=1 if a.external_id=="A110" else 0)
      a.risk_score=risk["score"]; db.add(RiskAssessment(organization_id=org.id,project_id=project.id,activity_id=a.id,score=risk["score"],band=risk["band"],factors=risk["factors"],recommendation=risk["recommendation"],model_version=risk["model_version"]))
    db.add_all([AuditEvent(organization_id=org.id,project_id=project.id,actor_id=reviewer.id,action="progress_observation.approved",entity_type="progress_observation",entity_id=obs1.id,before_values={"review_status":"pending","approved_progress":62},after_values={"review_status":"approved","approved_progress":65},correlation_id="seed-review-001"),AuditEvent(organization_id=org.id,project_id=project.id,actor_id=admin.id,action="bim_model.ingested",entity_type="bim_model",entity_id=model.id,after_values={"element_count":len(bim),"failure_count":len(failures)},correlation_id="seed-bim-001")])
    db.commit()
    dash=executive_dashboard(db,org.id,project.id)
    risks=[]
    for a in sorted(acts.values(),key=lambda x:x.risk_score,reverse=True):
      ra=db.scalar(select(RiskAssessment).where(RiskAssessment.activity_id==a.id).order_by(RiskAssessment.calculated_at.desc()))
      risks.append({"activity":a.name,"score":ra.score,"band":ra.band,"factors":ra.factors})
    alert_rows=[{"severity":x.severity,"title":x.title,"message":x.message} for x in db.scalars(select(Alert).where(Alert.project_id==project.id)).all()]
    report_path=str(settings.media_root/"reports"/"northstar_weekly_progress.pdf")
    create_progress_report(report_path,{"name":project.name,"code":project.code,"location":project.location},{k:dash[k] for k in ["planned_progress","approved_actual_progress","ai_estimated_progress","schedule_variance","delayed_activities","at_risk_activities","critical_safety_events","open_quality_observations"]},risks,alert_rows)
    report=Report(organization_id=org.id,project_id=project.id,report_type="weekly_progress",path=report_path,parameters={"seeded":True}); db.add(report); db.commit()
    return {"organization_id":org.id,"project_id":project.id,"admin_email":admin.email,"password":"BuildTwin123!","elements":len(bim),"activities":len(acts),"video_frames":vm.decoded_frames,"change_percent":change.changed_area_percent,"report":report_path}
