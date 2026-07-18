from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class ChangeResult:
    changed_area_percent: float
    confidence: float
    alignment_status: str
    overlay_path: str
    mask_path: str


def align_images(reference: np.ndarray, current: np.ndarray) -> tuple[np.ndarray, str, float]:
    gray_ref = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY)
    gray_cur = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(1200)  # type: ignore[attr-defined]
    kp1, des1 = orb.detectAndCompute(gray_ref, None)
    kp2, des2 = orb.detectAndCompute(gray_cur, None)
    if des1 is None or des2 is None or len(kp1) < 8 or len(kp2) < 8:
        return cv2.resize(current, (reference.shape[1], reference.shape[0])), "fallback_resize", 0.45
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des1, des2)
    matches = sorted(matches, key=lambda m: m.distance)[:80]
    if len(matches) < 8:
        return cv2.resize(current, (reference.shape[1], reference.shape[0])), "fallback_resize", 0.45
    src = np.asarray([kp2[m.trainIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    dst = np.asarray([kp1[m.queryIdx].pt for m in matches], dtype=np.float32).reshape(-1,1,2)
    matrix, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if matrix is None:
        return cv2.resize(current, (reference.shape[1], reference.shape[0])), "failed", 0.30
    aligned = cv2.warpPerspective(current, matrix, (reference.shape[1], reference.shape[0]))
    ratio = float(inliers.mean()) if inliers is not None else 0.5
    return aligned, "aligned", max(0.5, min(0.95, ratio))


def compare_images(baseline_path: str, current_path: str, output_dir: str, threshold: int = 28, min_area: int = 120) -> ChangeResult:
    baseline = cv2.imread(baseline_path)
    current = cv2.imread(current_path)
    if baseline is None or current is None:
        raise ValueError("Could not decode one or both comparison images")
    aligned, status, alignment_conf = align_images(baseline, current)
    gray_a = cv2.GaussianBlur(cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY), (5,5), 0)
    gray_b = cv2.GaussianBlur(cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY), (5,5), 0)
    diff = cv2.absdiff(gray_a, gray_b)
    _, mask = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7,7), np.uint8))
    filtered = np.zeros_like(mask)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv2.contourArea(contour) >= min_area:
            cv2.drawContours(filtered, [contour], -1, 255, -1)
    changed = float(np.count_nonzero(filtered)) / float(filtered.size) * 100.0
    overlay = aligned.copy()
    overlay[filtered > 0] = (0, 85, 255)
    overlay = cv2.addWeighted(aligned, 0.68, overlay, 0.32, 0)
    out = Path(output_dir); out.mkdir(parents=True, exist_ok=True)
    overlay_path = str(out / "change_overlay.jpg")
    mask_path = str(out / "change_mask.png")
    cv2.imwrite(overlay_path, overlay); cv2.imwrite(mask_path, filtered)
    confidence = max(0.2, min(0.98, alignment_conf * (0.7 + min(changed, 30)/100)))
    return ChangeResult(round(changed, 3), round(confidence, 3), status, overlay_path, mask_path)
