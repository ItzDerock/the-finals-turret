import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst
from keypoints import KEYPOINTS
import cv2
import hailo
from multiprocessing import Process, Pipe
from communication import Communication
from person import Person
from cli import options

from hailo_apps_infra.hailo_rpi_common import (
    get_caps_from_pad,
    get_numpy_from_buffer,
    app_callback_class,
)
from pipeline import GStreamerPoseEstimationApp

class TurretContext(app_callback_class):
    comm_thread: Process
    pipe: Connection

    def __init__(self):
        parent_conn, child_conn = Pipe()
        self.comm_thread = Process(target=Communication('/dev/ttyUSB0').updateLoop, args=(child_conn,))
        if not options.dry_run:
            self.comm_thread.start()
            print("[!] Communication thread started.")
        self.conn = parent_conn
        super().__init__()

def process_callback(pad, info, user_data: TurretContext):
    buffer = info.get_buffer()
    if buffer is None:
        return Gst.PadProbeReturn.OK

    string_to_print = ""

    # Get the caps from the pad
    format, width, height = get_caps_from_pad(pad) or (None, None, None)
    frame = get_numpy_from_buffer(buffer, format, width, height) if user_data.use_frame and format is not None and width is not None and height is not None else None

    # Get the detections from the buffer
    roi = hailo.get_roi_from_buffer(buffer)
    detections = roi.get_objects_typed(hailo.HAILO_DETECTION)

    # all detections parsed
    parsed_detections = []

    # Parse the detections
    for detection in detections:
        label, bbox, confidence = detection.get_label(), detection.get_bbox(), detection.get_confidence()

        if label != "person":
            continue

        # tracking id
        track_id = 0
        track = detection.get_objects_typed(hailo.HAILO_UNIQUE_ID)
        if len(track) == 1:
            track_id = track[0].get_id()

        string_to_print += (f"Detection: ID: {track_id} Label: {label} Confidence: {confidence:.2f}\n")

        # now retrieve pose estimation landmarks
        landmarks = detection.get_objects_typed(hailo.HAILO_LANDMARKS)
        parsed_detections.append(Person(track_id, confidence, bbox, landmarks, (width, height)))

        if len(landmarks) != 0:
            points = landmarks[0].get_points()
            for eye in ['left_eye', 'right_eye']:
                keypoint_index = KEYPOINTS[eye]
                point = points[keypoint_index]
                # Convert normalized coordinates to absolute pixel coordinates
                # First scale relative to bounding box, then offset by bbox position, then scale to image dimensions
                x = int((point.x() * bbox.width() + bbox.xmin()) * width)
                y = int((point.y() * bbox.height() + bbox.ymin()) * height)
                string_to_print += f"{eye}: x: {x:.2f} y: {y:.2f}\n"

                if user_data.use_frame:
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

    if user_data.use_frame:
        # Convert the frame to BGR
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        user_data.set_frame(frame)

    # find closest target
    closest_target = parsed_detections[0]
    closest_distance = parsed_detections[0].distance(width/2, height/2)

    for detection in parsed_detections[1:]:
        distance = detection.distance(width/2, height/2)
        if distance < closest_distance:
            closest_target = detection
            closest_distance = distance

    user_data.conn.send(closest_target)

    print(string_to_print)
    return Gst.PadProbeReturn.OK

if __name__ == "__main__":
    GStreamerPoseEstimationApp(process_callback, TurretContext()).run()
