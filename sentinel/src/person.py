from keypoints import KEYPOINTS
import math
from typing import Tuple

class Person:
    id: int
    confidence: float
    # bbox
    # landmarks
    dimensions: Tuple[int, int]

    def __init__(self, id: int, confidence: float, bbox, landmarks, dimensions):
        self.id = id
        self.confidence = confidence
        self.bbox = bbox
        self.landmarks = landmarks
        self.dimensions = dimensions

    def convert_normalized_to_absolute(self, point):
        """
        Convert normalized coordinates to absolute pixel coordinates
        First scale relative to bounding box, then offset by bbox position, then scale to image dimensions
        """
        if not self.bbox or not self.dimensions:
            print("[warn] No bbox or dimensions")
            return None

        if not point:
            print("[warn] No point")
            return

        width, height = self.dimensions
        x = int((point.x() * self.bbox.width() + self.bbox.xmin()) * width)
        y = int((point.y() * self.bbox.height() + self.bbox.ymin()) * height)
        return x, y

    def center(self):
        """
        Return the coordinates of where the person's eyes are, or their bbox center if no landmarks are available
        """
        width, height = self.dimensions

        if self.landmarks and len(self.landmarks) > 0:
            points = self.landmarks[0].get_points()
            left_eye = self.convert_normalized_to_absolute(points[KEYPOINTS["left_eye"]])
            right_eye = self.convert_normalized_to_absolute(points[KEYPOINTS["right_eye"]])

            if left_eye and right_eye:
                return (left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2

        # bbox center
        return (self.bbox.xmin() + self.bbox.xmax()) / 2, (self.bbox.ymin() + self.bbox.ymax()) / 2

    def distance(self, point: Tuple[int, int]):
        """
        Return the distance between the person and the given point
        """
        center = self.center()
        return math.sqrt((point[0] - center[0]) ** 2 + (point[1] - center[1]) ** 2)
