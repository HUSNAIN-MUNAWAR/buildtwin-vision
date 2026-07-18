from __future__ import annotations

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


def process_video(path: str, output_dir: str, sample_every: int = 10, max_frames: int = 180) -> VideoMetrics:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise ValueError("OpenCV could not open the video; file may be corrupted or codec unsupported")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    decoded = sampled = 0; outputs: list[str] = []
    start = time.perf_counter()
    while decoded < max_frames:
        ok, frame = cap.read()
        if not ok: break
        if decoded % max(1, sample_every) == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 80, 160)
            edge_density = float((edges > 0).mean())
            cv2.putText(frame, f"frame={decoded} edge_density={edge_density:.3f}", (16,28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,255,255), 2)
            output = out / f"frame_{decoded:05d}.jpg"
            cv2.imwrite(str(output), frame); outputs.append(str(output)); sampled += 1
        decoded += 1
    cap.release()
    elapsed = time.perf_counter() - start
    if decoded == 0:
        raise ValueError("Video contains no decodable frames")
    return VideoMetrics(decoded, sampled, fps, round(elapsed,3), round(elapsed/decoded*1000,3), outputs)
