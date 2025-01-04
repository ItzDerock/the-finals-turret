# Load environment variables before anything else
from dotenv import load_dotenv
load_dotenv()

import time
import cv2
import torch
import time
import pid
import numpy as np
from cli import options
from send import KlipperWebSocketClient
from juxtapose import Annotator, RTMDet, RTMPose
from juxtapose.trackers import Tracker
from juxtapose.utils.core import Detections
from juxtapose.utils.ops import Profile
from multiprocessing import Process, Pipe

device = "cuda" if torch.cuda.is_available() else "cpu"

# Configurations
CENTER_THRESHOLD = 60 # Pixels for center threshold
NO_DETECTION_TIMEOUT = 2  # Seconds before switching target

cap = cv2.VideoCapture(options.video)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, options.resolution[0]) # try to force the requested resolution
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, options.resolution[1])
width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
center_x, center_y = width // 2, height // 2

# Variables to track the target person and last detection time
target_id = None
last_detection_time = time.time()

parent_conn, child_conn = Pipe(duplex=True)
client = KlipperWebSocketClient()
p = Process(target=client.start, args=(child_conn,))
if not options.dry_run:
  p.start()
  print("[i] Spawned communication thread")

# Load the models
rtmdet = RTMDet("s", device=device)
rtmpose = RTMPose("s", device=device)
tracker = Tracker("bytetrack").tracker
annotator = Annotator(thickness=3, font_color=(128, 128, 128))
print("[i] Models loaded")

# Performance profiling
# (detection, tracking, pose estimation)
profilers = (Profile(), Profile(), Profile())

while cap.isOpened():
  ret, frame = cap.read()
  if not ret:
    print('[w] Ignoring empty frame')
    continue

  # Perform detection
  with profilers[0]:
    detections: Detections = rtmdet(frame)

  # Only do the expensive calculations if we found a person
  if detections:
    # Invoke bytetrack
    with profilers[1]:
      detections: Detections = tracker.update(
        bboxes=detections.xyxy,
        confidence=detections.confidence,
        labels=detections.labels,
      )

    # Perform pose estimation
    with profilers[2]:
      kpts, kpts_scores = rtmpose(frame, bboxes=detections.xyxy)

    # Turn into an easier to use format
    persons = [
      {"id": str(id), "kpts": kpt.tolist(), "bboxes": bboxes}
      for i, kpt, bboxes in zip(
        detections.track_id, kpts, detections.xyxy.tolist()
      )
    ]

    # Draw
    annotator.draw_bboxes(frame, detections.xyxy, labels=np.array(
      [
        f"person {id} {score:.2f}"
        for score, label, id in zip(
          detections.confidence, detections.labels, detections.track_id
        )
      ]
    ))

    annotator.draw_kpts(frame, kpts)
    annotator.draw_skeletons(frame, kpts)

    # Print the tracking stats
    bbox_ms, track_ms, pose_ms = [profile.dt * 1e3 / 1 for profile in profilers]
    fps = 1.0 / (bbox_ms + track_ms + pose_ms)
    print(f"Found {len(persons)} person(s), bbox: {bbox_ms:.2f}ms, track: {track_ms:.2f}ms, pose: {pose_ms:.2f}ms | FPS: {fps:.2f}")

    if persons:
      # Select or update target
      if target_id is None:
          target_id = persons[0]['id']  # Select the first person as target
          last_detection_time = time.time()

      # Find target person
      target_person = next((person for person in persons if person['id'] == target_id), None)

      if target_person is None:
          print("no one")
          if time.time() - last_detection_time > NO_DETECTION_TIMEOUT:
              target_id = None  # Reset target if current one is gone
          continue

      # Get keypoints for the target person
      keypoints = target_person['kpts']

      if keypoints is None or len(keypoints) < 5:  # Ensure head keypoints are available
          print("no one")
          if time.time() - last_detection_time > NO_DETECTION_TIMEOUT:
              target_id = None
          continue

      last_detection_time = time.time()  # Update last detection time

      # Extract head position (e.g., keypoint 0 for head center)
      head_x, head_y = keypoints[0]

      # Determine position relative to screen
            # if abs(head_x - center_x) <= CENTER_THRESHOLD:
      #     continue
      parent_conn.send("shoot" if abs(head_x - center_x) <= CENTER_THRESHOLD else "noshoot")

      x = pid.X_PID(setpoint=head_x, processValue=center_x)
      y = pid.Y_PID(setpoint=head_y, processValue=center_y)

      parent_conn.send(f"move {x} {y}")
  else:
    print("Found no targets")
    parent_conn.send("noshoot")
    if time.time() - last_detection_time > NO_DETECTION_TIMEOUT:
        target_id = None  # Reset target if no one is detected for long

  # show
  cv2.imshow("Turret tracking", frame)
  if cv2.waitKey(1) & 0xFF == ord('q'):
    parent_conn.send("noshoot")
    print("[i] Recieved 'q' key. Exiting...")
    # wait 100ms to ensure the message is sent
    time.sleep(0.1)
    break

# Clean up
cap.release()
cv2.destroyAllWindows()
if not options.dry_run:
  p.terminate()
  p.join()
  print("[i] Communication thread terminated")
