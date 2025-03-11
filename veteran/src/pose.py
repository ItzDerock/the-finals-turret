# Load environment variables before anything else
from dotenv import load_dotenv
load_dotenv()

import time
import cv2
import numpy as np
from cli import options
from send import KlipperWebSocketClient
from juxtapose import Annotator, RTMDet, RTMPose
from juxtapose.trackers import Tracker
from juxtapose.utils.core import Detections
from juxtapose.utils.ops import Profile
from multiprocessing import Process, Pipe

try:
    from hailort import (
        Device,
        InferVStreams,
        ResourceManager,
        ConfigureParams,
    )
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False

# Configurations
CENTER_THRESHOLD = 200 # Pixels for center threshold
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
if options.hailo and HAILO_AVAILABLE:
    # Initialize Hailo device
    resource_manager = ResourceManager()
    device = resource_manager.get_default_device()
    
    # Load RTMDet model
    rtmdet_network = device.load_network(
        "models/rtmdet_s.hef",
        configure_params=ConfigureParams.default()
    )
    
    # Load RTMPose model
    rtmpose_network = device.load_network(
        "models/rtmpose_s.hef",
        configure_params=ConfigureParams.default()
    )
    
    # Create inference streams
    rtmdet_streams = InferVStreams(rtmdet_network)
    rtmpose_streams = InferVStreams(rtmpose_network)
    
    print("[i] Hailo models loaded")
else:
    rtmdet = RTMDet("s", device="cpu")
    rtmpose = RTMPose("s", device="cpu")
    print("[i] CPU models loaded")

tracker = Tracker("bytetrack").tracker
annotator = Annotator(thickness=3, font_color=(128, 128, 128))

# Performance profiling
# (detection, tracking, pose estimation)
profilers = (Profile(), Profile(), Profile())

def preprocess_frame(frame, target_shape=None):
    """Preprocess frame for Hailo input"""
    if target_shape:
        frame = cv2.resize(frame, target_shape)
    # Convert to float32 and normalize to [0, 1]
    frame = frame.astype(np.float32) / 255.0
    # Transpose from HWC to CHW format
    frame = frame.transpose(2, 0, 1)
    # Add batch dimension
    frame = np.expand_dims(frame, axis=0)
    return frame

def postprocess_detections(output):
    """Convert Hailo detection output to Detections format"""
    # This needs to be implemented based on the actual output format of your converted model
    # The exact implementation depends on how the model was converted and its output format
    boxes = output['boxes'] if isinstance(output, dict) else output[0]
    scores = output['scores'] if isinstance(output, dict) else output[1]
    labels = np.ones(len(boxes))  # Assuming all detections are people
    
    return Detections(
        xyxy=boxes,
        confidence=scores,
        labels=labels
    )

def postprocess_pose(output, orig_shape):
    """Convert Hailo pose output to keypoints format"""
    # This needs to be implemented based on the actual output format of your converted model
    # The exact implementation depends on how the model was converted and its output format
    keypoints = output['keypoints'] if isinstance(output, dict) else output[0]
    scores = output['scores'] if isinstance(output, dict) else output[1]
    
    # Scale keypoints back to original image size if needed
    if orig_shape is not None:
        h, w = orig_shape[:2]
        keypoints[:, :, 0] *= w
        keypoints[:, :, 1] *= h
    
    return keypoints, scores

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print('[w] Ignoring empty frame')
        continue

    # Perform detection
    with profilers[0]:
        if options.hailo and HAILO_AVAILABLE:
            # Preprocess frame for Hailo
            input_data = preprocess_frame(frame, (416, 416))  # Adjust size as needed
            # Run inference on Hailo
            outputs = rtmdet_streams.infer(input_data)
            # Convert Hailo output to Detections format
            detections = postprocess_detections(outputs)
        else:
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
            if options.hailo and HAILO_AVAILABLE:
                # Crop and preprocess regions for pose estimation
                person_crops = [frame[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])] 
                              for bbox in detections.xyxy]
                kpts = []
                kpts_scores = []
                
                for crop in person_crops:
                    # Preprocess crop for Hailo
                    crop_input = preprocess_frame(crop, (256, 192))  # Standard RTMPose input size
                    # Run inference
                    pose_outputs = rtmpose_streams.infer(crop_input)
                    # Convert output to keypoints format
                    crop_kpts, crop_scores = postprocess_pose(pose_outputs, crop.shape)
                    kpts.append(crop_kpts)
                    kpts_scores.append(crop_scores)
                
                kpts = np.array(kpts)
                kpts_scores = np.array(kpts_scores)
            else:
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
