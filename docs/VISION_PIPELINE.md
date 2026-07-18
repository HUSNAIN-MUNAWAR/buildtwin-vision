# Vision pipeline

## Implemented CPU path

1. Validate and persist source media.
2. Stream MP4 frames through `cv2.VideoCapture`; never load the entire video.
3. Sample every Nth frame and cap the local demo frame count.
4. Compute Canny edge density and annotate sampled evidence.
5. For paired images, attempt ORB/homography alignment; fall back to resize with lower confidence.
6. Apply grayscale blur, absolute difference, thresholding, morphological opening/closing, and contour-area filtering.
7. Measure nonzero mask area as a percentage of the image.
8. Save overlay and mask, persist metrics/status, and expose evidence URLs.
9. Fail corrupted/empty media explicitly.

The progress estimator is an analytical rule layer. It is not a trained construction-completion model. Model adapters can add ONNX or specialist detectors while preserving evidence/version/review fields.
