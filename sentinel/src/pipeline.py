# BASED OFF OF hailo_apps_infra/gstreamer_helper_pipelines.py
# LICENSED UNDER MIT
# SEE https://github.com/hailo-ai/hailo-apps-infra/blob/main/LICENSE

# The USB camera I have does not support streaming at 720@30fps, causing a gstreamer pipeline error.
CAMERA_FRAMERATE="120/1"

import gi
gi.require_version('Gst', '1.0')
import os
import setproctitle
from cli import options
from collections import defaultdict
from hailo_apps_infra.hailo_rpi_common import (
    get_default_parser,
    detect_hailo_arch,
)
from hailo_apps_infra.gstreamer_helper_pipelines import(
    SOURCE_PIPELINE,
    INFERENCE_PIPELINE,
    INFERENCE_PIPELINE_WRAPPER,
    TRACKER_PIPELINE,
    USER_CALLBACK_PIPELINE,
    DISPLAY_PIPELINE,
)
from hailo_apps_infra.gstreamer_app import (
    GStreamerApp,
    app_callback_class,
    dummy_callback
)


class HailoArgs:
    def __init__(self):
        self.input = None
        self.use_frame = False
        self.show_fps = False
        self.arch = None
        self.hef_path = None
        self.disable_sync = False
        self.disable_callback = False
        self.dump_dot = False

    def to_dict(self):
        return self.__dict__

#-----------------------------------------------------------------------------------------------
# User Gstreamer Application
# -----------------------------------------------------------------------------------------------

# This class inherits from the hailo_rpi_common.GStreamerApp class

class GStreamerPoseEstimationApp(GStreamerApp):
    def __init__(self, app_callback, user_data):
        args = HailoArgs()

        # Set the arguments
        args.input = options.video
        args.use_frame = False
        args.show_fps = True
        args.arch = None
        args.hef_path = options.hef
        args.disable_sync = True
        args.disable_callback = False
        args.dump_dot = False

        # Call the parent class constructor
        super().__init__(args, user_data)

        # Batch size of 1 to reduce latency
        self.batch_size = 1
        self.video_width = 1280
        self.video_height = 720
        self.hef_path = options.hef

        # Determine the architecture if not specified
        if args.arch is None:
            detected_arch = detect_hailo_arch()
            if detected_arch is None:
                raise ValueError("Could not auto-detect Hailo architecture. Please specify --arch manually.")
            self.arch = detected_arch
            print(f"Auto-detected Hailo architecture: {self.arch}")
        else:
            self.arch = args.arch

        if self.arch != "hailo8":
            print("Support for non hailo8 chips not implemented. Likely all you will need to change is the HEF file (src/pipeline.py).")
            raise ValueError(f"Unsupported architecture: {self.arch}. Supported architectures are hailo8.")

        self.app_callback = app_callback

        # Set the post-processing shared object file
        self.post_process_so = os.path.join(self.current_path, '../resources/libyolov8pose_postprocess.so')
        self.post_process_function = "filter_letterbox"

        # Set the process title
        setproctitle.setproctitle("Hailo Pose Estimation App")
        self.create_pipeline()

    def get_pipeline_string(self):
        source_pipeline = SOURCE_PIPELINE(video_source=self.video_source, video_width=self.video_width, video_height=self.video_height)
        infer_pipeline = INFERENCE_PIPELINE(
            hef_path=self.hef_path,
            post_process_so=self.post_process_so,
            post_function_name=self.post_process_function,
            batch_size=self.batch_size
        )
        infer_pipeline_wrapper = INFERENCE_PIPELINE_WRAPPER(infer_pipeline)
        tracker_pipeline = TRACKER_PIPELINE(class_id=0)
        user_callback_pipeline = USER_CALLBACK_PIPELINE()
        display_pipeline = DISPLAY_PIPELINE(video_sink=self.video_sink, sync=self.sync, show_fps=self.show_fps)

        # Replace "framerate=30/1" with requested framerate
        source_pipeline = source_pipeline.replace("framerate=30/1", f"framerate={CAMERA_FRAMERATE}")

        pipeline_string = (
            f'{source_pipeline} !'
            f'{infer_pipeline_wrapper} ! '
            f'{tracker_pipeline} ! '
            f'{user_callback_pipeline} ! '
            f'{display_pipeline}'
        )

        print(pipeline_string)
        return pipeline_string

if __name__ == "__main__":
    # Create an instance of the user app callback class
    user_data = app_callback_class()
    app = GStreamerPoseEstimationApp(dummy_callback, user_data)
    app.run()
