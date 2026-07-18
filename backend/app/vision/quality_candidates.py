import cv2


def assess_image_quality(path: str) -> dict:
    image = cv2.imread(path)
    if image is None:
        raise ValueError("Image could not be decoded")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    candidates = []
    if sharpness < 90:
        candidates.append({"type":"excessive_blur", "confidence": round(min(0.95, (90-sharpness)/90+0.4),3)})
    if brightness < 45:
        candidates.append({"type":"insufficient_lighting", "confidence": round(min(0.95, (45-brightness)/45+0.4),3)})
    return {"sharpness": round(sharpness,2), "brightness": round(brightness,2), "candidates": candidates}
