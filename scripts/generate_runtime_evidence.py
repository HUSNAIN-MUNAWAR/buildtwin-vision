from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import cv2

from app.vision.video_reader import process_video

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "sample_data/videos/level1_progress.mp4"
OUTPUT_DIR = ROOT / "docs/runtime_evidence"
ANNOTATED = OUTPUT_DIR / "buildtwin-progress-runtime.mp4"
POSTER = OUTPUT_DIR / "buildtwin-progress-runtime-poster.jpg"
TRACE = OUTPUT_DIR / "buildtwin-progress-edge-trace.csv"
SUMMARY = OUTPUT_DIR / "buildtwin-progress-runtime-summary.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, str | int]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def poster_metadata(path: Path) -> dict[str, int | float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not decode annotated runtime video: {path}")
    frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frames // 2))
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise RuntimeError("Could not read an annotated poster frame")
    cv2.imwrite(str(POSTER), frame)
    return {"frames": frames, "fps": fps, "width": width, "height": height}


def main() -> None:
    os.chdir(ROOT)
    if not SOURCE.exists():
        raise SystemExit(f"Missing committed demo video: {SOURCE}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (ANNOTATED, POSTER, TRACE, SUMMARY):
        path.unlink(missing_ok=True)
    run_dir = OUTPUT_DIR / "_buildtwin_run"
    shutil.rmtree(run_dir, ignore_errors=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    metrics = process_video(
        str(SOURCE),
        str(run_dir),
        sample_every=12,
        max_frames=72,
        annotated_output=str(run_dir / "annotated.mp4"),
        trace_output=str(run_dir / "trace.csv"),
    )
    Path(run_dir / "annotated.mp4").replace(ANNOTATED)
    Path(run_dir / "trace.csv").replace(TRACE)
    shutil.rmtree(run_dir, ignore_errors=True)
    encoded = poster_metadata(ANNOTATED)

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "opencv": cv2.__version__,
        },
        "source": {
            "file": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(SOURCE),
            "synthetic_demo_input": True,
            "metadata": {
                "fps": metrics.fps,
                "decoded_frames": metrics.decoded_frames,
                "sampled_frames": metrics.sampled_frames,
                "duration_seconds": round(metrics.decoded_frames / metrics.fps, 6)
                if metrics.fps
                else 0.0,
            },
        },
        "pipeline": {
            "processor": "BuildTwin backend.app.vision.video_reader.process_video",
            "algorithm": "OpenCV grayscale conversion and Canny edge-density measurement",
            "sample_every": 12,
            "max_frames": 72,
            "decoded_frames": metrics.decoded_frames,
            "sampled_frames": metrics.sampled_frames,
            "average_frame_latency_ms": metrics.average_frame_latency_ms,
            "encoded_output": encoded,
        },
        "artifacts": {
            "annotated_video": artifact(ANNOTATED),
            "poster": artifact(POSTER),
            "edge_trace": artifact(TRACE),
        },
        "claim_boundary": [
            "This is a real OpenCV processing run over the committed encoded demo MP4.",
            "The source video is synthetic demo input; it is not construction-site footage or a labeled benchmark.",
            "The runtime measures image edge density and does not detect construction defects, workers, equipment, or BIM correspondence.",
            "No learned vision checkpoint, model training, accuracy score, or fabricated detection is claimed.",
        ],
    }
    SUMMARY.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
