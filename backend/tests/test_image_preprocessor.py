"""Unit tests for ImagePreprocessor module."""

import cv2
import numpy as np

from app.ingestion.image_preprocessor import ImagePreprocessor


def test_image_preprocessor_rotation():
    preprocessor = ImagePreprocessor()
    # Create synthetic white image with a black horizontal bar
    img = np.ones((200, 400, 3), dtype=np.uint8) * 255
    cv2.line(img, (50, 100), (350, 100), (0, 0, 0), thickness=5)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    rotated = preprocessor.rotate_image(gray, 10.0)

    assert rotated.shape[0] > 0
    assert rotated.shape[1] > 0
    assert rotated.dtype == np.uint8


def test_image_preprocessor_pipeline():
    preprocessor = ImagePreprocessor()
    img = np.ones((300, 300, 3), dtype=np.uint8) * 255
    # Draw some text-like lines
    cv2.line(img, (20, 50), (280, 50), (0, 0, 0), 2)
    cv2.line(img, (20, 100), (280, 100), (0, 0, 0), 2)

    processed, result = preprocessor.preprocess(img)

    assert processed is not None
    assert len(processed.shape) == 3  # 3-channel BGR for PaddleOCR compatibility
    assert result.original_shape == (300, 300)
