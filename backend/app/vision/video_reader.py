from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class VideoMetrics:
    decoded_frames: int
    sampled_frames: int
    fps: float
    duration_seconds: float
    average_frame_latency_ms: float
    output_paths: list[str]


def process_video(
    path: str,
    output_dir: str,
    sample_every: int = 10,
    max_frames: int = 180,
    annotated_output: str | None = None,
    trace_output: str | None = None,
) -> VideoMetrics:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("OpenCV could not open the video; file may be corrupted or codec unsupported")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    decoded = sampled = 0
    outputs: list[str] = []
    trace_rows: list[dict[str, float | int]] = []
    writer = None
    if annotated_output:
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        writer = cv2.VideoWriter(
            annotated_output,
            getattr(cv2, "VideoWriter_fourcc")(*"mp4v"),
            fps / max(1, sample_every) if fps > 0 else 1.0,
            (width, height),
        )
        if not writer.isOpened():
            cap.release()
            raise RuntimeError(f"Could not create annotated video: {annotated_output}")
    start = time.perf_counter()
    while decoded < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if decoded % max(1, sample_every) == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 80, 160)
            edge_density = float((edges > 0).mean())
            cv2.putText(
                frame, f"frame={decoded} edge_density={edge_density:.3f}", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2
            )
            output = out / f"frame_{decoded:05d}.jpg"
            cv2.imwrite(str(output), frame)
            outputs.append(str(output))
            sampled += 1
            if writer is not None:
                writer.write(frame)
            trace_rows.append(
                {
                    "frame_index": decoded,
                    "timestamp_seconds": round(decoded / fps, 6) if fps else 0.0,
                    "edge_density": round(edge_density, 6),
                }
            )
        decoded += 1
    cap.release()
    if writer is not None:
        writer.release()
        outputs.append(str(annotated_output))
    if trace_output:
        trace_path = Path(trace_output)
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("w", newline="", encoding="utf-8") as fh:
            writer_csv = csv.DictWriter(fh, fieldnames=["frame_index", "timestamp_seconds", "edge_density"])
            writer_csv.writeheader()
            writer_csv.writerows(trace_rows)
    elapsed = time.perf_counter() - start
    if decoded == 0:
        raise ValueError("Video contains no decodable frames")
    return VideoMetrics(decoded, sampled, fps, round(elapsed, 3), round(elapsed / decoded * 1000, 3), outputs)
