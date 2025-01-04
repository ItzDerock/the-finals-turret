from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

import cv2
import torch
import time
import send
import pid
from cli import options
from juxtapose import RTM, Annotator, RTMDet, RTMPose
from multiprocessing import Process, Pipe

device = "cuda" if torch.cuda.is_available() else "cpu"

# Initialize RTM model
model = RTM(
    det="rtmdet-s",
    pose="rtmpose-s",
    tracker="bytetrack",
    device=device
)

# Configurations
CENTER_THRESHOLD = 50  # Pixels for center threshold
NO_DETECTION_TIMEOUT = 2  # Seconds before switching target

# Annotator
annotator = Annotator(thickness=3, font_color=(128, 128, 128))

cap = cv2.VideoCapture(options.video)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, options.resolution[0]) # try to force the requested resolution
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, options.resolution[1])

# Variables to track the target person and last detection time
target_id = None
last_detection_time = time.time()

parent_conn, child_conn = Pipe(duplex=True)
p = Process(target=send.update_board, args=(child_conn,))
p.start()

# Load the model
rtmdet = RTMDet("s", device=device)

# for result in model(32, imgsz=1920, show=True, plot=True, stream=True):
while cap.isOpened():



    im, persons, kpts = result.im, result.persons, result.kpts

    if not persons or not kpts:
        print("no one")
        if time.time() - last_detection_time > NO_DETECTION_TIMEOUT:
            target_id = None  # Reset target if no one is detected for long
        continue

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
    frame_width = 1280
    center_x = frame_width // 2
    center_y = 720 // 2

    # if abs(head_x - center_x) <= CENTER_THRESHOLD:
    #     continue
    parent_conn.send("shoot" if abs(head_x - center_x) <= CENTER_THRESHOLD else "noshoot")

    x = pid.X_PID(setpoint=head_x, processValue=center_x)
    y = pid.Y_PID(setpoint=head_y, processValue=center_y)

    parent_conn.send(f"move {x} {y}")


# import cv2
# import torch
# from cli import options
# from juxtapose import RTM, Annotator

# # Init a rtm model (including rtmdet, rtmpose, tracker)
# model = RTM(
#     det="rtmdet-s",
#     pose="rtmpose-s",
#     tracker="bytetrack",
#     device="cuda" if torch.cuda.is_available() else "cpu",
# )

# # Load the requested video source
# # cap = cv2.VideoCapture(options.video)
# # cap.set(cv2.CAP_PROP_FRAME_WIDTH, options.resolution[0]) # try to force the requested resolution
# # cap.set(cv2.CAP_PROP_FRAME_HEIGHT, options.resolution[1])

# annotator = Annotator(thickness=3, font_color=(128, 128, 128))  # see rtm.utils.plotting

# for result in model(32, show=True, plot=True, stream=True):
#     # do what ever you want with the data
#     im, bboxes, kpts = result.im, result.bboxes, result.kpts

#     # e.g custom plot anything using cv2 API
#     cv2.putText(
#         im, "custom text", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (128, 128, 128)
#     )

#     # use the annotator class -> see rtm.utils.plotting
#     annotator.draw_bboxes(
#         im, bboxes, labels=[f"children_{i}" for i in range(len(bboxes))]
#     )
#     annotator.draw_kpts(im, kpts, thickness=4)
#     annotator.draw_skeletons(im, kpts)    # do what ever you want with the data
#     im, bboxes, kpts = result.im, result.bboxes, result.kpts

#     # e.g custom plot anything using cv2 API
#     cv2.putText(
#         im, "custom text", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (128, 128, 128)
#     )

#     # use the annotator class -> see rtm.utils.plotting
#     annotator.draw_bboxes(
#         im, bboxes, labels=[f"children_{i}" for i in range(len(bboxes))]
#     )
#     annotator.draw_kpts(im, kpts, thickness=4)
#     annotator.draw_skeletons(im, kpts)    # do what ever you want with the data
#     print(kpts) # Get the coordinates of the chest
#     im, bboxes, kpts = result.im, result.bboxes, result.kpts

#     # e.g custom plot anything using cv2 API
#     cv2.putText(
#         im, "custom text", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (128, 128, 128)
#     )

#     # use the annotator class -> see rtm.utils.plotting
#     annotator.draw_bboxes(
#         im, bboxes, labels=[f"children_{i}" for i in range(len(bboxes))]
#     )
#     annotator.draw_kpts(im, kpts, thickness=4)
#     annotator.draw_skeletons(im, kpts)
