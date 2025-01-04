from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

import send
import cv2
import numpy as np
import time
import torch
from cli import options
from camera import pixel_to_angle
from utils import predict_with_ema
from PID_Py.PID import PID
from pathlib import Path
from ultralytics import YOLO
from collections import defaultdict
from ultralytics.utils.plotting import Annotator
from torch.quantization import quantize_dynamic
from multiprocessing import Process, Pipe

track_history = defaultdict(lambda: [])
pid = PID(kp = 0.006, ki = 0, kd = 0.0002)

# Load the model
model = YOLO(options.model)
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
print("[i] Using device: ", device)
model.to(device)

# quantize if requested
if options.quantize:
  quantized_model = quantize_dynamic(model.model, {torch.nn.Linear}, dtype=torch.qint8)
  model.model = quantized_model

names = model.model.names
video_path = options.video

# Load the video file (or webcam)
if not Path(video_path).exists():
  raise FileNotFoundError(f"Source path "
                          f"'{video_path}' "
                          f"does not exist.")

cap = cv2.VideoCapture(video_path)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, options.resolution[0]) # try to force the requested resolution
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, options.resolution[1])

PREDICT_TIME = 500  # in milliseconds
alpha = 0.3  # Smoothing factor for EMA

# Spherical without the r, so (phi, theta)
current_phi = 180
current_theta = 0

parent_conn, child_conn = Pipe(duplex=True)
p = Process(target=send.update_board, args=(child_conn,))
if not options.dry_run:
  p.start()
  print("[i] Spawned communication thread")

# Read the actual width and height
width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
current_target = None
target_last_found = time.time()
shooting_enabled = True

while cap.isOpened():
  success, frame = cap.read()

  if success:
    # Detect objects and extract bounding boxes
    results = model.track(frame, persist=True, classes=[0],
                          tracker="bytetrack.yaml", verbose=options.verbose)

    boxes = results[0].boxes.xywh.cpu()
    clss = results[0].boxes.cls.cpu().tolist()

    if results[0].boxes.id is not None:
      track_ids = results[0].boxes.id.int().cpu().tolist()
    else:
      track_ids = []

    # Draw bounding boxes and labels
    annotator = Annotator(frame, line_width=2,
                          example=str(names))

    for box, track_id, cls in zip(boxes, track_ids, clss):
      x, y, w, h = box
      x1, y1, x2, y2 = (x - w / 2, y - h / 2,
                        x + w / 2, y + h / 2)
      label = str(names[cls]) + " : " + str(track_id)
      annotator.box_label([x1, y1, x2, y2],
                          label, (218, 100, 255))

      # Keep track of previous locations for EMA
      track = track_history[track_id]
      track.append((float(box[0]), float(box[1]), time.time()))
      if len(track) > 30:
        track.pop(0)

      # Draw the previous locations, extracting only (x,y) points
      points = np.hstack([(p[0], p[1]) for p in track]).astype(np.int32).reshape((-1, 1, 2))
      cv2.polylines(frame, [points], isClosed=False,
                    color=(37, 255, 225), thickness=2)

      # Circle indicating the center of the person.
      cv2.circle(frame,
                  (int(track[-1][0]), int(track[-1][1])),
                  5, (235, 219, 11), -1)

      # --------------
      # The turret should only track ONE person at a time
      # so it doesn't bounce between people
      if current_target is None:
        current_target = track_id
        print("[i] Acquired new target with id: " + str(track_id))

      # Ignore everyone else
      if current_target != track_id:
        continue

      target_last_found = time.time()

      # Find absolute angle of person
      rel_phi, rel_theta = pixel_to_angle(track[-1][0], track[-1][1], width, height)
      track_phi = current_phi + rel_phi
      track_theta = current_theta + rel_theta

      # Guess where we are probably going to go
      predicted = predict_with_ema(track, PREDICT_TIME, alpha)

      # Communicate the new angles to the board
      if not options.dry_run:
        parent_conn.send(f"move {str(rel_phi/45)} {str(rel_theta/45)}")

        if shooting_enabled:
          parent_conn.send("shoot" if rel_phi < 2 else "noshoot")

      if options.verbose:
        print("[d] phi = " + str(track_phi))
        print("[d] theta = " + str(track_theta))

      # Draw a circle representing the predicted location
      if predicted is not None:
        cv2.circle(frame,
                    (int(predicted[0]), int(predicted[1])),
                    10, (135, 206, 250), -1)

    # If we haven't seen the target for a while, reset
    if time.time() - target_last_found > 2:
      current_target = None

    # Show the frame, and quit if 'q' is pressed
    cv2.imshow("Turret", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
      break
    if cv2.waitKey(1) & 0xFF == ord("s"):
      parent_conn.send("noshoot")
      shooting_enabled = False
  else:
      break

cap.release()
cv2.destroyAllWindows()
