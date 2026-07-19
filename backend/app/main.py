from __future__ import annotations

import time
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.bim.ifc_parser import parse_ifc
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.base import Base
from app.db.session import engine, get_db
from app.models.entities import *
from app.reports.pdf import create_progress_report
from app.risk.model import calculate_delay_risk
from app.schedule.engine import critical_path, load_schedule
from app.services.audit import record_audit
from app.services.dashboard import executive_dashboard
from app.services.public_dataset import DATASET_PUBLISHER, DATASET_SOURCE, DATASET_TERMS, DATASET_TITLE
from app.services.seed import seed_database
from app.vision.change_detection import compare_images
from app.vision.video_reader import process_video
from app.vision.zone_geometry import validate_polygon

Base.metadata.create_all(engine)
settings.media_root.mkdir(parents=True, exist_ok=True)
app=FastAPI(title=settings.app_name,version="1.0.0",description="Evidence-first 4D construction intelligence API")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.mount("/media-files",StaticFiles(directory=str(settings.media_root)),name="media-files")

@app.middleware("http")
async def correlation_and_timing(request: Request, call_next):
    cid=request.headers.get("x-correlation-id",str(uuid.uuid4()))
    start=time.perf_counter()
    try:
        response=await call_next(request)
    except Exception as exc:
        response=JSONResponse(status_code=500,content={"error":"internal_error","detail":"An unexpected error occurred","correlation_id":cid})
        print({"level":"error","correlation_id":cid,"path":request.url.path,"exception":repr(exc)})
    response.headers["x-correlation-id"]=cid
    response.headers["x-response-time-ms"]=f"{(time.perf_counter()-start)*1000:.2f}"
    response.headers["x-content-type-options"]="nosniff"
    response.headers["x-frame-options"]="DENY"
    return response

class LoginRequest(BaseModel): email: str; password: str
class ReviewRequest(BaseModel): decision: str; approved_progress: float|None=None; notes: str=""
class ZoneCreate(BaseModel): project_id:int; floor_id:int|None=None; name:str; polygon:list[list[float]]; restricted:bool=False
class ChangeRequest(BaseModel): project_id:int; zone_id:int; baseline_asset_id:int; current_asset_id:int; threshold:int=Field(default=28,ge=1,le=254)
class LinkRequest(BaseModel): activity_id:int; score:float=Field(default=1.0,ge=0,le=1); reason:str="manual"


def scoped(db:Session, model, user:User, entity_id:int):
    obj=db.get(model,entity_id)
    if not obj or getattr(obj,"organization_id",None)!=user.organization_id: raise HTTPException(404,"Record not found")
    return obj

def media_url(path:str)->str:
    try: rel=Path(path).resolve().relative_to(settings.media_root.resolve()); return "/media-files/"+str(rel).replace("\\","/")
    except Exception: return path

@app.get("/")
def root(): return {"name":settings.app_name,"docs":"/docs","health":"/api/v1/health"}

@app.get("/api/v1/health")
def health(): return {"status":"ok","service":"buildtwin-api","time":datetime.utcnow().isoformat()}

@app.get("/api/v1/ready")
def ready(db:Session=Depends(get_db)):
    try: db.execute(text("SELECT 1")); return {"status":"ready","database":"ok","media_root":settings.media_root.exists()}
    except Exception as exc: raise HTTPException(503,f"Database unavailable: {exc}")

@app.post("/api/v1/auth/login")
def login(payload:LoginRequest,db:Session=Depends(get_db)):
    user=db.scalar(select(User).where(User.email==payload.email.lower()))
    if not user or not verify_password(payload.password,user.password_hash): raise HTTPException(401,"Invalid credentials")
    return {"access_token":create_access_token(user.id,user.organization_id,user.role),"token_type":"bearer","user":{"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role,"organization_id":user.organization_id}}

@app.get("/api/v1/auth/me")
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"full_name":user.full_name,"role":user.role,"organization_id":user.organization_id}

@app.post("/api/v1/admin/seed")
def seed(db:Session=Depends(get_db)): return seed_database(db,reset=True)

@app.get("/api/v1/projects")
def projects(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Project).where(Project.organization_id==user.organization_id).order_by(Project.name)).all()
    return [{"id":p.id,"name":p.name,"code":p.code,"location":p.location,"start_date":p.start_date,"finish_date":p.finish_date} for p in rows]

@app.get("/api/v1/projects/{project_id}")
def project_detail(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=scoped(db,Project,user,project_id)
    return {"id":p.id,"name":p.name,"code":p.code,"location":p.location,"start_date":p.start_date,"finish_date":p.finish_date}

@app.get("/api/v1/dashboard/executive")
def dashboard(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); return executive_dashboard(db,user.organization_id,project_id)

@app.get("/api/v1/datasets/public-demo")
def public_dataset_demo(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id)
    rows=db.scalars(select(Activity).where(Activity.organization_id==user.organization_id,Activity.project_id==project_id,Activity.external_id.like("NYC-DOB-%")).order_by(Activity.planned_start)).all()
    return {"title":DATASET_TITLE,"publisher":DATASET_PUBLISHER,"source":DATASET_SOURCE,"terms":DATASET_TERMS,"records":len(rows),"activity_ids":[a.external_id for a in rows],"planned_progress":round(sum(a.planned_progress for a in rows)/len(rows),1) if rows else 0,"approved_progress":round(sum(a.approved_progress for a in rows)/len(rows),1) if rows else 0}

@app.get("/api/v1/dashboard/progress")
def progress_dashboard(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id)
    zones=db.scalars(select(Zone).where(Zone.organization_id==user.organization_id,Zone.project_id==project_id)).all()
    result=[]
    for z in zones:
        acts=db.scalars(select(Activity).where(Activity.zone_id==z.id)).all()
        result.append({"zone_id":z.id,"zone":z.name,"restricted":z.restricted,"planned":round(sum(a.planned_progress for a in acts)/len(acts),1) if acts else 0,"actual":round(sum(a.approved_progress for a in acts)/len(acts),1) if acts else 0,"risk":round(max([a.risk_score for a in acts],default=0),1),"activity_count":len(acts)})
    return result

@app.get("/api/v1/buildings")
def buildings(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); return [{"id":x.id,"name":x.name} for x in db.scalars(select(Building).where(Building.organization_id==user.organization_id,Building.project_id==project_id)).all()]

@app.get("/api/v1/floors")
def floors(building_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    b=scoped(db,Building,user,building_id); return [{"id":x.id,"name":x.name,"elevation_m":x.elevation_m} for x in db.scalars(select(Floor).where(Floor.organization_id==user.organization_id,Floor.building_id==b.id)).all()]

@app.get("/api/v1/zones")
def zones(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); return [{"id":z.id,"name":z.name,"floor_id":z.floor_id,"polygon":z.polygon,"restricted":z.restricted,"stale_after_hours":z.stale_after_hours} for z in db.scalars(select(Zone).where(Zone.organization_id==user.organization_id,Zone.project_id==project_id)).all()]

@app.post("/api/v1/zones")
def create_zone(payload:ZoneCreate,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value)),db:Session=Depends(get_db)):
    scoped(db,Project,user,payload.project_id)
    try: validate_polygon(payload.polygon)
    except ValueError as exc: raise HTTPException(422,str(exc))
    z=Zone(organization_id=user.organization_id,**payload.model_dump()); db.add(z); db.flush(); record_audit(db,user,"zone.created","zone",z.id,project_id=z.project_id,after=payload.model_dump()); db.commit(); return {"id":z.id,"name":z.name}

@app.get("/api/v1/bim/models")
def bim_models(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(BIMModel).where(BIMModel.organization_id==user.organization_id,BIMModel.project_id==project_id).order_by(BIMModel.created_at.desc())).all(); return [{"id":x.id,"filename":x.filename,"status":x.status,"element_count":x.element_count,"failure_count":x.failure_count,"report":x.report} for x in rows]

@app.get("/api/v1/bim/models/{model_id}/elements")
def bim_elements(model_id:int,element_type:str|None=None,status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    model=scoped(db,BIMModel,user,model_id); q=select(BIMElement).where(BIMElement.organization_id==user.organization_id,BIMElement.model_id==model.id)
    if element_type:q=q.where(BIMElement.element_type.ilike(f"%{element_type}%"))
    if status:q=q.where(BIMElement.progress_status==status)
    rows=db.scalars(q.order_by(BIMElement.element_type,BIMElement.name)).all(); return [{"id":x.id,"ifc_guid":x.ifc_guid,"element_type":x.element_type,"name":x.name,"floor_name":x.floor_name,"zone_id":x.zone_id,"discipline":x.discipline,"material":x.material,"bbox":x.bbox,"progress_status":x.progress_status,"progress_percent":x.progress_percent,"confidence":x.confidence} for x in rows]

@app.post("/api/v1/bim/models")
async def upload_ifc(project_id:int=Form(...),file:UploadFile=File(...),user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value)),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id)
    if not file.filename or not file.filename.lower().endswith(".ifc"): raise HTTPException(415,"Only .ifc uploads are supported")
    safe=f"{uuid.uuid4().hex}_{Path(file.filename).name}"; target=settings.media_root/"ifc"/safe; target.parent.mkdir(parents=True,exist_ok=True)
    content=await file.read(settings.max_upload_bytes+1)
    if len(content)>settings.max_upload_bytes: raise HTTPException(413,"File exceeds upload limit")
    target.write_bytes(content); model=BIMModel(organization_id=user.organization_id,project_id=project_id,filename=Path(file.filename).name,status="processing"); db.add(model); db.flush()
    try:
        parsed,failures=parse_ifc(str(target))
        for e in parsed: db.add(BIMElement(organization_id=user.organization_id,project_id=project_id,model_id=model.id,ifc_guid=e.ifc_guid,element_type=e.element_type,name=e.name,progress_status="unverified"))
        model.status="completed"; model.element_count=len(parsed); model.failure_count=len(failures); model.report={"source":str(target),"failures":failures,"parser":"STEP lightweight parser"}
    except ValueError as exc: model.status="failed"; model.failure_count=1; model.report={"error":str(exc)}
    record_audit(db,user,"bim_model.ingested","bim_model",model.id,project_id=project_id,after=model.report); db.commit(); return {"id":model.id,"status":model.status,"element_count":model.element_count,"failure_count":model.failure_count,"report":model.report}

@app.post("/api/v1/bim/elements/{element_id}/activity-links")
def link_element(element_id:int,payload:LinkRequest,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.REVIEWER.value)),db:Session=Depends(get_db)):
    e=scoped(db,BIMElement,user,element_id); a=scoped(db,Activity,user,payload.activity_id)
    link=ActivityBIMLink(organization_id=user.organization_id,activity_id=a.id,bim_element_id=e.id,score=payload.score,reason=payload.reason,status="accepted" if payload.score>=.65 else "suggested"); db.add(link); record_audit(db,user,"bim_activity_link.created","activity_bim_link",None,project_id=e.project_id,after=payload.model_dump()); db.commit(); return {"id":link.id,"status":link.status}

@app.get("/api/v1/schedule/activities")
def activities(project_id:int,critical:bool|None=None,status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); q=select(Activity).where(Activity.organization_id==user.organization_id,Activity.project_id==project_id)
    if critical is not None:q=q.where(Activity.critical==critical)
    if status:q=q.where(Activity.status==status)
    rows=db.scalars(q.order_by(Activity.planned_start)).all(); return [{"id":a.id,"external_id":a.external_id,"name":a.name,"zone_id":a.zone_id,"planned_start":a.planned_start,"planned_finish":a.planned_finish,"planned_progress":a.planned_progress,"approved_progress":a.approved_progress,"ai_progress":a.ai_progress,"variance":round(a.approved_progress-a.planned_progress,1),"status":a.status,"critical":a.critical,"contractor":a.contractor,"risk_score":a.risk_score} for a in rows]

@app.get("/api/v1/schedule/dependency-graph")
def dependency_graph(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); acts=db.scalars(select(Activity).where(Activity.organization_id==user.organization_id,Activity.project_id==project_id)).all(); deps=db.scalars(select(ScheduleDependency).where(ScheduleDependency.organization_id==user.organization_id,ScheduleDependency.project_id==project_id)).all(); by={a.id:a for a in acts}; return {"nodes":[{"id":a.id,"external_id":a.external_id,"name":a.name,"critical":a.critical,"risk_score":a.risk_score} for a in acts],"edges":[{"from":by[d.predecessor_id].external_id,"to":by[d.successor_id].external_id,"type":d.dependency_type,"lag_days":d.lag_days} for d in deps]}

@app.get("/api/v1/schedule/critical-path")
def schedule_critical_path(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); acts=db.scalars(select(Activity).where(Activity.organization_id==user.organization_id,Activity.project_id==project_id)).all(); by={a.id:a for a in acts}; deps=db.scalars(select(ScheduleDependency).where(ScheduleDependency.project_id==project_id)).all(); rows=[{"activity_id":a.external_id,"planned_start":a.planned_start,"planned_finish":a.planned_finish} for a in acts]; edges=[(by[d.predecessor_id].external_id,by[d.successor_id].external_id) for d in deps]; return {"critical_path":critical_path(rows,edges)}

@app.post("/api/v1/schedule/import")
async def schedule_import(project_id:int=Form(...),file:UploadFile=File(...),user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value)),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id)
    suffix=Path(file.filename or "").suffix.lower()
    if suffix not in {".csv",".json"}: raise HTTPException(415,"Schedule must be CSV or JSON")
    target=settings.media_root/"schedules"/f"{uuid.uuid4().hex}_{Path(file.filename).name}"; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(await file.read())
    try: rows=load_schedule(str(target))
    except ValueError as exc: raise HTTPException(422,str(exc))
    return {"valid":True,"activities":len(rows),"message":"Validated successfully. Import into an existing production schedule is intentionally non-destructive in this demo."}

@app.get("/api/v1/cameras")
def cameras(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); return [{"id":c.id,"name":c.name,"zone_id":c.zone_id,"source_type":c.source_type,"status":c.status,"last_seen_at":c.last_seen_at,"last_error":c.last_error} for c in db.scalars(select(Camera).where(Camera.organization_id==user.organization_id,Camera.project_id==project_id)).all()]

@app.get("/api/v1/captures")
def captures(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(MediaAsset).where(MediaAsset.organization_id==user.organization_id,MediaAsset.project_id==project_id).order_by(MediaAsset.captured_at.desc())).all(); return [{"id":m.id,"kind":m.kind,"filename":m.filename,"url":media_url(m.path),"zone_id":m.zone_id,"camera_id":m.camera_id,"captured_at":m.captured_at,"synthetic":m.synthetic,"metadata":m.metadata_json} for m in rows]

async def save_capture(file:UploadFile,project_id:int,zone_id:int|None,camera_id:int|None,kind:str,user:User,db:Session):
    scoped(db,Project,user,project_id)
    allowed={"image":{".jpg",".jpeg",".png"},"video":{".mp4"}}[kind]; suffix=Path(file.filename or "").suffix.lower()
    if suffix not in allowed: raise HTTPException(415,f"Unsupported {kind} type")
    content=await file.read(settings.max_upload_bytes+1)
    if len(content)>settings.max_upload_bytes: raise HTTPException(413,"File exceeds upload limit")
    safe=f"{uuid.uuid4().hex}_{Path(file.filename).name}"; target=settings.media_root/("images" if kind=="image" else "videos")/safe; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(content)
    m=MediaAsset(organization_id=user.organization_id,project_id=project_id,zone_id=zone_id,camera_id=camera_id,kind=kind,filename=Path(file.filename).name,path=str(target),synthetic=False); db.add(m); db.flush(); record_audit(db,user,"capture.uploaded","media_asset",m.id,project_id=project_id,after={"kind":kind,"filename":m.filename}); db.commit(); return {"id":m.id,"kind":m.kind,"filename":m.filename,"url":media_url(m.path)}

@app.post("/api/v1/captures/images")
async def upload_image(project_id:int=Form(...),zone_id:int|None=Form(None),camera_id:int|None=Form(None),file:UploadFile=File(...),user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value,Role.REVIEWER.value)),db:Session=Depends(get_db)): return await save_capture(file,project_id,zone_id,camera_id,"image",user,db)

@app.post("/api/v1/captures/videos")
async def upload_video(project_id:int=Form(...),zone_id:int|None=Form(None),camera_id:int|None=Form(None),file:UploadFile=File(...),user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value)),db:Session=Depends(get_db)): return await save_capture(file,project_id,zone_id,camera_id,"video",user,db)

@app.post("/api/v1/processing/media/{asset_id}/run")
def run_processing(asset_id:int,sample_every:int=10,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value)),db:Session=Depends(get_db)):
    asset=scoped(db,MediaAsset,user,asset_id); job=ProcessingJob(organization_id=user.organization_id,project_id=asset.project_id,media_asset_id=asset.id,job_type=f"{asset.kind}_processing",status="running",started_at=datetime.utcnow()); db.add(job); db.flush()
    try:
        if asset.kind=="video": metrics=process_video(asset.path,str(settings.media_root/"outputs"/f"job_{job.id}"),sample_every=sample_every).__dict__; output=metrics["output_paths"][-1]
        else:
            import cv2
            image=cv2.imread(asset.path)
            if image is None: raise ValueError("Image could not be decoded")
            metrics={"width":image.shape[1],"height":image.shape[0],"channels":image.shape[2]}; output=asset.path
        job.status="completed"; job.progress=100; job.metrics=metrics; job.output_reference=output; job.completed_at=datetime.utcnow()
    except ValueError as exc: job.status="failed"; job.error_code="MEDIA_PROCESSING_FAILED"; job.error_message=str(exc); job.completed_at=datetime.utcnow()
    record_audit(db,user,"processing_job.completed" if job.status=="completed" else "processing_job.failed","processing_job",job.id,project_id=asset.project_id,after={"status":job.status,"metrics":job.metrics}); db.commit(); return {"id":job.id,"status":job.status,"progress":job.progress,"metrics":job.metrics,"output_url":media_url(job.output_reference) if job.output_reference else None,"error_code":job.error_code,"error_message":job.error_message}

@app.get("/api/v1/processing/jobs")
def jobs(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(ProcessingJob).where(ProcessingJob.organization_id==user.organization_id,ProcessingJob.project_id==project_id).order_by(ProcessingJob.created_at.desc())).all(); return [{"id":j.id,"job_type":j.job_type,"status":j.status,"progress":j.progress,"metrics":j.metrics,"output_url":media_url(j.output_reference) if j.output_reference else None,"error_code":j.error_code,"error_message":j.error_message,"created_at":j.created_at} for j in rows]

@app.post("/api/v1/changes/compare")
def change_compare(payload:ChangeRequest,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.SITE_ENGINEER.value,Role.REVIEWER.value)),db:Session=Depends(get_db)):
    scoped(db,Project,user,payload.project_id); baseline=scoped(db,MediaAsset,user,payload.baseline_asset_id); current=scoped(db,MediaAsset,user,payload.current_asset_id)
    try: result=compare_images(baseline.path,current.path,str(settings.media_root/"outputs"/f"change_{uuid.uuid4().hex[:8]}"),threshold=payload.threshold)
    except ValueError as exc: raise HTTPException(422,str(exc))
    comp=ChangeComparison(organization_id=user.organization_id,project_id=payload.project_id,zone_id=payload.zone_id,baseline_asset_id=baseline.id,current_asset_id=current.id,changed_area_percent=result.changed_area_percent,alignment_status=result.alignment_status,confidence=result.confidence,overlay_path=result.overlay_path); db.add(comp); db.flush(); record_audit(db,user,"change_comparison.created","change_comparison",comp.id,project_id=payload.project_id,after={"changed_area_percent":comp.changed_area_percent}); db.commit(); return {"id":comp.id,"changed_area_percent":comp.changed_area_percent,"confidence":comp.confidence,"alignment_status":comp.alignment_status,"overlay_url":media_url(comp.overlay_path),"review_status":comp.review_status}

@app.get("/api/v1/changes")
def changes(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(ChangeComparison).where(ChangeComparison.organization_id==user.organization_id,ChangeComparison.project_id==project_id).order_by(ChangeComparison.created_at.desc())).all(); return [{"id":x.id,"zone_id":x.zone_id,"baseline_asset_id":x.baseline_asset_id,"current_asset_id":x.current_asset_id,"changed_area_percent":x.changed_area_percent,"alignment_status":x.alignment_status,"confidence":x.confidence,"overlay_url":media_url(x.overlay_path),"review_status":x.review_status,"reviewer_notes":x.reviewer_notes,"created_at":x.created_at} for x in rows]

@app.get("/api/v1/progress/observations")
def observations(project_id:int,review_status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); q=select(ProgressObservation).where(ProgressObservation.organization_id==user.organization_id,ProgressObservation.project_id==project_id)
    if review_status:q=q.where(ProgressObservation.review_status==review_status)
    rows=db.scalars(q.order_by(ProgressObservation.created_at.desc())).all(); acts={a.id:a for a in db.scalars(select(Activity).where(Activity.project_id==project_id)).all()}; return [{"id":o.id,"activity_id":o.activity_id,"activity":acts[o.activity_id].name,"external_id":acts[o.activity_id].external_id,"zone_id":o.zone_id,"estimated_progress":o.estimated_progress,"previous_progress":o.previous_progress,"confidence":o.confidence,"algorithm":o.algorithm,"algorithm_version":o.algorithm_version,"evidence_url":media_url(o.evidence_path),"review_status":o.review_status,"review_notes":o.review_notes,"created_at":o.created_at} for o in rows]

@app.post("/api/v1/progress/observations/{observation_id}/review")
def review_observation(observation_id:int,payload:ReviewRequest,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.REVIEWER.value)),db:Session=Depends(get_db)):
    obs=scoped(db,ProgressObservation,user,observation_id); activity=scoped(db,Activity,user,obs.activity_id); before={"review_status":obs.review_status,"approved_progress":activity.approved_progress}
    if payload.decision not in {"approved","rejected"}: raise HTTPException(422,"Decision must be approved or rejected")
    if payload.decision=="approved":
        value=payload.approved_progress if payload.approved_progress is not None else obs.estimated_progress
        if not 0<=value<=100: raise HTTPException(422,"Approved progress must be between 0 and 100")
        activity.approved_progress=value; activity.status="complete" if value>=100 else "delayed" if value+5<activity.planned_progress else "in_progress"
    obs.review_status=payload.decision; obs.reviewer_id=user.id; obs.review_notes=payload.notes; obs.reviewed_at=datetime.utcnow()
    record_audit(db,user,f"progress_observation.{payload.decision}","progress_observation",obs.id,project_id=obs.project_id,before=before,after={"review_status":obs.review_status,"approved_progress":activity.approved_progress,"notes":payload.notes}); db.commit(); return {"id":obs.id,"review_status":obs.review_status,"activity_id":activity.id,"approved_progress":activity.approved_progress}

@app.get("/api/v1/safety/events")
def safety_events(project_id:int,status:str|None=None,severity:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); q=select(SafetyEvent).where(SafetyEvent.organization_id==user.organization_id,SafetyEvent.project_id==project_id)
    if status:q=q.where(SafetyEvent.status==status)
    if severity:q=q.where(SafetyEvent.severity==severity)
    rows=db.scalars(q.order_by(SafetyEvent.first_seen.desc())).all(); return [{"id":e.id,"event_type":e.event_type,"severity":e.severity,"confidence":e.confidence,"zone_id":e.zone_id,"camera_id":e.camera_id,"evidence_url":media_url(e.evidence_path),"detection_boxes":e.detection_boxes,"status":e.status,"first_seen":e.first_seen,"last_seen":e.last_seen,"assigned_to":e.assigned_to,"notes":e.notes} for e in rows]

@app.get("/api/v1/quality/observations")
def quality(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(QualityObservation).where(QualityObservation.organization_id==user.organization_id,QualityObservation.project_id==project_id)).all(); return [{"id":q.id,"candidate_type":q.candidate_type,"severity":q.severity,"confidence":q.confidence,"status":q.status,"zone_id":q.zone_id,"activity_id":q.activity_id,"evidence_url":media_url(q.evidence_path),"corrective_action":q.corrective_action,"due_date":q.due_date,"reviewer_notes":q.reviewer_notes} for q in rows]

@app.get("/api/v1/risk/activities")
def risks(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.execute(select(RiskAssessment,Activity).join(Activity,RiskAssessment.activity_id==Activity.id).where(RiskAssessment.organization_id==user.organization_id,RiskAssessment.project_id==project_id).order_by(RiskAssessment.score.desc())).all(); return [{"id":r.id,"activity_id":a.id,"external_id":a.external_id,"activity":a.name,"score":r.score,"band":r.band,"factors":r.factors,"recommendation":r.recommendation,"model_version":r.model_version,"calculated_at":r.calculated_at,"critical":a.critical,"planned_progress":a.planned_progress,"approved_progress":a.approved_progress} for r,a in rows]

@app.post("/api/v1/risk/recalculate")
def recalc_risk(project_id:int,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value)),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); acts=db.scalars(select(Activity).where(Activity.organization_id==user.organization_id,Activity.project_id==project_id)).all(); count=0
    for a in acts:
        deps=db.scalars(select(ScheduleDependency).where(ScheduleDependency.successor_id==a.id)).all(); delayed=sum(1 for d in deps if (p:=db.get(Activity,d.predecessor_id)) and p.approved_progress+5<p.planned_progress)
        risk=calculate_delay_risk(planned_progress=a.planned_progress,actual_progress=a.approved_progress,critical=a.critical,planned_finish=a.planned_finish,delayed_predecessors=delayed,evidence_age_hours=48,safety_events=0,quality_issues=0); a.risk_score=risk["score"]; db.add(RiskAssessment(organization_id=user.organization_id,project_id=project_id,activity_id=a.id,score=risk["score"],band=risk["band"],factors=risk["factors"],recommendation=risk["recommendation"],model_version=risk["model_version"])); count+=1
    record_audit(db,user,"risk.recalculated","project",project_id,project_id=project_id,after={"activity_count":count}); db.commit(); return {"recalculated":count}

@app.get("/api/v1/alerts")
def alerts(project_id:int,status:str|None=None,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); q=select(Alert).where(Alert.organization_id==user.organization_id,Alert.project_id==project_id)
    if status:q=q.where(Alert.status==status)
    rows=db.scalars(q.order_by(Alert.created_at.desc())).all(); return [{"id":a.id,"alert_type":a.alert_type,"severity":a.severity,"title":a.title,"message":a.message,"status":a.status,"entity_type":a.entity_type,"entity_id":a.entity_id,"created_at":a.created_at} for a in rows]

@app.post("/api/v1/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    a=scoped(db,Alert,user,alert_id); before=a.status; a.status="acknowledged"; record_audit(db,user,"alert.acknowledged","alert",a.id,project_id=a.project_id,before={"status":before},after={"status":a.status}); db.commit(); return {"id":a.id,"status":a.status}

@app.get("/api/v1/audit")
def audit(project_id:int,limit:int=50,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(AuditEvent).where(AuditEvent.organization_id==user.organization_id,AuditEvent.project_id==project_id).order_by(AuditEvent.created_at.desc()).limit(min(limit,200))).all(); users={u.id:u.full_name for u in db.scalars(select(User).where(User.organization_id==user.organization_id)).all()}; return [{"id":e.id,"actor":users.get(e.actor_id,"System"),"action":e.action,"entity_type":e.entity_type,"entity_id":e.entity_id,"before_values":e.before_values,"after_values":e.after_values,"correlation_id":e.correlation_id,"created_at":e.created_at} for e in rows]

@app.get("/api/v1/reports")
def reports(project_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    scoped(db,Project,user,project_id); rows=db.scalars(select(Report).where(Report.organization_id==user.organization_id,Report.project_id==project_id).order_by(Report.generated_at.desc())).all(); return [{"id":r.id,"report_type":r.report_type,"download_url":f"/api/v1/reports/{r.id}/download","generated_at":r.generated_at,"parameters":r.parameters} for r in rows]

@app.post("/api/v1/reports/generate")
def generate_report(project_id:int,user:User=Depends(require_roles(Role.ADMIN.value,Role.PROJECT_MANAGER.value,Role.REVIEWER.value)),db:Session=Depends(get_db)):
    project=scoped(db,Project,user,project_id); dash=executive_dashboard(db,user.organization_id,project_id); risk_rows=risks(project_id,user,db); alert_rows=alerts(project_id,None,user,db); path=str(settings.media_root/"reports"/f"{project.code.lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"); create_progress_report(path,{"name":project.name,"code":project.code,"location":project.location},{k:dash[k] for k in ["planned_progress","approved_actual_progress","ai_estimated_progress","schedule_variance","delayed_activities","at_risk_activities","critical_safety_events","open_quality_observations"]},risk_rows,alert_rows); report=Report(organization_id=user.organization_id,project_id=project_id,report_type="weekly_progress",path=path,parameters={"generated_by":user.email}); db.add(report); db.flush(); record_audit(db,user,"report.generated","report",report.id,project_id=project_id,after={"path":path}); db.commit(); return {"id":report.id,"download_url":f"/api/v1/reports/{report.id}/download"}

@app.get("/api/v1/reports/{report_id}/download")
def download_report(report_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    r=scoped(db,Report,user,report_id)
    if not Path(r.path).exists(): raise HTTPException(404,"Report file not found")
    return FileResponse(r.path,media_type="application/pdf",filename=Path(r.path).name)
