import csv
from datetime import date, timedelta
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.bim.ifc_parser import parse_ifc
from app.core.config import settings
from app.risk.model import calculate_delay_risk
from app.schedule.engine import load_schedule
from app.services.public_dataset import public_permit_schedule_rows, read_public_permits
from app.vision.change_detection import compare_images
from app.vision.video_reader import process_video
from app.vision.zone_geometry import box_centroid_inside, validate_polygon


def test_polygon_geometry():
    poly=[[0,0],[100,0],[100,100],[0,100]]; validate_polygon(poly)
    assert box_centroid_inside(poly,{"x1":20,"y1":20,"x2":40,"y2":40})
    assert not box_centroid_inside(poly,{"x1":120,"y1":20,"x2":140,"y2":40})


def test_cycle_detection(tmp_path):
    path=tmp_path/"cycle.csv"
    with path.open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["activity_id","name","planned_start","planned_finish","planned_progress","actual_progress","predecessors"]); w.writerow(["A","A","2026-01-01","2026-01-02",0,0,"B"]); w.writerow(["B","B","2026-01-02","2026-01-03",0,0,"A"])
    with pytest.raises(ValueError,match="circular"): load_schedule(str(path))


def test_ifc_parser_rejects_fake(tmp_path):
    p=tmp_path/"fake.ifc"; p.write_text("not ifc")
    with pytest.raises(ValueError,match="header"): parse_ifc(str(p))


def test_change_detection_calculation(tmp_path):
    a=np.full((200,300,3),200,np.uint8); b=a.copy(); cv2.rectangle(b,(50,50),(150,150),(0,0,0),-1)
    pa=tmp_path/"a.jpg"; pb=tmp_path/"b.jpg"; cv2.imwrite(str(pa),a); cv2.imwrite(str(pb),b)
    result=compare_images(str(pa),str(pb),str(tmp_path/"out"),threshold=20)
    assert result.changed_area_percent>10
    assert Path(result.overlay_path).exists()


def test_real_video_decoding():
    result=process_video(str(settings.media_root/"videos"/"level1_progress.mp4"),str(settings.media_root/"outputs"/"test_video"),sample_every=18,max_frames=72)
    assert result.decoded_frames==72 and result.sampled_frames==4


def test_public_dataset_maps_to_schedule_rows():
    permits=read_public_permits(settings.media_root/"public"/"nyc_dob_permit_sample.csv")
    rows=public_permit_schedule_rows(permits)
    assert len(rows)==12
    assert rows[0]["activity_id"].startswith("NYC-DOB-")
    assert rows[0]["zone"]=="NYC Public Permit Sample"
    assert all(0 <= row["actual_progress"] <= row["planned_progress"] <= 100 for row in rows)
    assert {row["work_package"] for row in rows} <= {"Alteration","Equipment","Plumbing","General Construction"}


def test_risk_monotonicity():
    low=calculate_delay_risk(planned_progress=50,actual_progress=50,critical=False,planned_finish=date.today()+timedelta(days=10),delayed_predecessors=0,evidence_age_hours=4,safety_events=0,quality_issues=0)
    high=calculate_delay_risk(planned_progress=95,actual_progress=40,critical=True,planned_finish=date.today()-timedelta(days=5),delayed_predecessors=2,evidence_age_hours=120,safety_events=2,quality_issues=1)
    assert high["score"]>low["score"] and high["band"] in {"high","critical"}
