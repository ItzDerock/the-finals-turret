import cv2
import time
import numpy as np
from typing import TypedDict, Generator
from juxtapose import Annotator, RTMDet, RTMPose
from juxtapose.trackers import Tracker
from juxtapose.utils.core import Detections
from juxtapose.utils.ops import Profile

class PoseDetectionOptions(TypedDict):
  width: int
  height: int
  device: str
  center_threshold: int
  no_detection_timeout: int
  show: bool

class PoseDetection:
  # configuration
  center_threshold: int = 60
  no_detection_timeout: int = 2
  show: bool = True

  # video
  cap: cv2.VideoCapture
  width: int = 0
  height: int = 0

  # runtime tracking
  target_id = None
  last_detection_time = 0
  profilers = (Profile(), Profile(), Profile())

  def __init__(self, source, **kwargs: PoseDetectionOptions):
    """
    Initialize the PoseDetection class
    """
    self.cap = cv2.VideoCapture(source)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, kwargs.width)
    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, kwargs.height)
    self.width = kwargs.width
    self.height = kwargs.height
    self.center_threshold = kwargs.center_threshold if 'center_threshold' in kwargs else 60
    self.no_detection_timeout = kwargs.no_detection_timeout if 'no_detection_timeout' in kwargs else 2
    self.show = kwargs.show if 'show' in kwargs else True

    # Load the models
    self.rtmdet = RTMDet("s", device=kwargs.device)
    self.rtmpose = RTMPose("s", device=kwargs.device)
    self.tracker = Tracker("bytetrack").tracker
    self.annotator = Annotator(thickness=3, font_color=(128, 128, 128))

  def __del__(self):
    """
    Release the video capture object
    """
    if self.cap is not None:
      self.cap.release()

  def annotate_frame(self, frame, detections, kpts):
    """
    Annotate the frame with the detections, drawing bounding boxes and
    the pose keypoints
    """
    self.annotator.draw_bboxes(frame, detections.xyxy, labels=np.array(
      [
        f"person {id} {score:.2f}"
        for score, label, id in zip(
          detections.confidence, detections.labels, detections.track_id
        )
      ]
    ))

    self.annotator.draw_kpts(frame, kpts)
    self.annotator.draw_skeletons(frame, kpts)

  def track(self) -> Generator[tuple[int, int] | None]:
    """
    Generator returning the current target
    Returns the (x, y) coordinate of the current target
    """
    while self.cap.isOpened():
      success, frame = self.cap.read()
      if not success:
        print('[w] Ignoring empty/invalid frame')
        continue

      # Perform detection
      with self.profilers[0]:
        detections: Detections = self.rtmdet(frame)

      # Only do the expensive calculations if we found a person
      if detections:
        # Invoke bytetrack
        with self.profilers[1]:
          detections: Detections = self.tracker.update(
            bboxes=detections.xyxy,
            confidence=detections.confidence,
            labels=detections.labels,
          )

        # Perform pose estimation
        with self.profilers[2]:
          kpts, kpts_scores = self.rtmpose(frame, bboxes=detections.xyxy)

        # Turn into an easier to use format
        persons = [
          {"id": str(id), "kpts": kpt.tolist(), "bboxes": bboxes}
          for i, kpt, bboxes in zip(
            detections.track_id, kpts, detections.xyxy.tolist()
          )
        ]

        # Draw
        if self.show:
          self.annotate_frame(frame, detections, kpts)

        # Print the tracking stats
        bbox_ms, track_ms, pose_ms = [profile.dt * 1e3 / 1 for profile in self.profilers]
        fps = 1.0 / (bbox_ms + track_ms + pose_ms)
        print(f"Found {len(persons)} person(s), bbox: {bbox_ms:.2f}ms, track: {track_ms:.2f}ms, pose: {pose_ms:.2f}ms | FPS: {fps:.2f}")

        if persons:
          # Select or update target
          if self.target_id is None:
              self.target_id = persons[0]['id']  # Select the first person as target
              self.last_detection_time = time.time()

          # Find target person
          target_person = next((person for person in persons if person['id'] == self.target_id), None)

          if target_person is None:
              if time.time() - self.last_detection_time > self.no_detection_timeout:
                  self.target_id = None  # Reset target if current one is gone
              yield None
              continue

          # Get keypoints for the target person
          keypoints = target_person['kpts']

          if keypoints is None or len(keypoints) < 5:  # Ensure head keypoints are available
              if time.time() - self.last_detection_time > self.no_detection_timeout:
                  self.target_id = None
              yield None
              continue

          last_detection_time = time.time()  # Update last detection time

          # Extract head position (e.g., keypoint 0 for head center)
          head_x, head_y = keypoints[0]
          yield (head_x, head_y)
      else:
        print("Found no targets")
        if time.time() - self.last_detection_time > self.no_detection_timeout:
            self.target_id = None  # Reset target if no one is detected for long

        yield None

      # show
      if self.show:
        cv2.imshow("Turret tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
          print("[i] Recieved 'q' key. Exiting...")
          time.sleep(0.1)
          break
