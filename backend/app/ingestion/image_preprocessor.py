"""Image Preprocessor module for OpenCV deskewing, denoising, and contrast enhancement."""

import cv2
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel


class PreprocessResult(BaseModel):
    skew_angle: float
    is_deskewed: bool
    original_shape: tuple[int, int]
    processed_shape: tuple[int, int]


class ImagePreprocessor:
    """Applies computer vision filters to optimize scanned pages for OCR."""

    def __init__(self, deskew_threshold: float = 0.5):
        self.deskew_threshold = deskew_threshold

    def detect_skew_angle(self, gray_image: NDArray[np.uint8]) -> float:
        """Detect skew angle of text lines using Hough Line Transform."""
        edges = cv2.Canny(gray_image, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=100,
            minLineLength=100,
            maxLineGap=20,
        )

        if lines is None or len(lines) == 0:
            return 0.0

        angles: list[float] = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            # Filter near horizontal lines only (-45 to 45 deg)
            if -45 < angle < 45:
                angles.append(angle)

        if not angles:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    def rotate_image(self, image: NDArray[np.uint8], angle: float) -> NDArray[np.uint8]:
        """Rotate image by given angle while expanding bounding box to prevent cropping."""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)

        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        cos = np.abs(rot_mat[0, 0])
        sin = np.abs(rot_mat[0, 1])

        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))

        rot_mat[0, 2] += (new_w / 2) - center[0]
        rot_mat[1, 2] += (new_h / 2) - center[1]

        rotated = cv2.warpAffine(
            image,
            rot_mat,
            (new_w, new_h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return rotated

    def denoise(self, image: NDArray[np.uint8]) -> NDArray[np.uint8]:
        """Bilateral filter reduces noise while keeping character edges sharp."""
        return cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)

    def preprocess(
        self, bgr_image: NDArray[np.uint8]
    ) -> tuple[NDArray[np.uint8], PreprocessResult]:
        """Full preprocessing pipeline: Grayscale -> Deskew -> Denoise."""
        h, w = bgr_image.shape[:2]
        gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)

        # Detect and fix skew
        angle = self.detect_skew_angle(gray)
        deskewed = False
        if abs(angle) >= self.deskew_threshold:
            gray = self.rotate_image(gray, angle)
            deskewed = True

        # Denoise
        cleaned = self.denoise(gray)
        # Convert back to 3-channel BGR for PaddleOCR input requirement
        cleaned_bgr = cv2.cvtColor(cleaned, cv2.COLOR_GRAY2BGR)

        res = PreprocessResult(
            skew_angle=round(angle, 2),
            is_deskewed=deskewed,
            original_shape=(h, w),
            processed_shape=(cleaned.shape[0], cleaned.shape[1]),
        )
        return cleaned_bgr, res
