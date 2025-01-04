from multiprocessing import connection
from websocket import create_connection
from uuid import uuid4
import json
import time
import math
import os

MOONRAKER_URL = os.getenv("MOONRAKER_WS_URL")
STEPPER_MAPPER = {
    "x": "stepper_x",
    "y": "stepper_y",
    "z": "stepper_z"
}

def steps_needed(delta_angle: float, step_angle: float, driven_teeth: float, driving_teeth: float):
  """
  Calculate the number of steps needed to move a stepper motor a certain number of degrees.

  Parameters:
    delta_angle (float): The number of degrees to move the stepper motor.
    step_angle (float): The angle of each step in degrees (default 1.8).
    driven_teeth (int): The number of teeth on the driven gear (default 120).
    driving_teeth (int): The number of teeth on the driving gear (default 38).
  """

  gear_ratio = driven_teeth / driving_teeth
  degrees_per_step_driven = step_angle / gear_ratio
  steps = delta_angle / degrees_per_step_driven

  return steps

def build_klipper_ws_gcode_payload(gcode: str, id: str | None = None) -> str:
  """
    Creates the JSON RPC payload for sending gcode commands to klipper via the moonraker API.

    Parameters:
      gcode (str): The gcode command to send to the printer.
  """
  return json.dumps({
    "jsonrpc": "2.0",
    "method": "printer.gcode.script",
    "params": {
      "script": gcode
    },
    "id": id or str(uuid4())
  })

def build_gcode_relative_move(axis: str, steps: float) -> str:
  if axis not in STEPPER_MAPPER:
    raise ValueError("Stepper must be either 'x', 'y', or 'z'")

  # Klipper has experimental polar support
  # but it's very early-stage and unreliable
  # it still expects cartesian coordinates
  # r = 2
  # x = r*math.cos(math.radians(steps))
  # y = r*math.sin(math.radians(steps))
  # gcode_command = "G0 X" + str(x) + " Y" + str(y)

  # return f"G0 X{steps} F10000"
  return f"FORCE_MOVE STEPPER=stepper_x DISTANCE={steps} VELOCITY=50"

# {x,y,z}{-,}{angle}
def update_board(conn: connection.Connection):
  """
  Continuously read from the connection and send commands to the board.
  THIS FUNCTION WILL BLOCK THE CURRENT THREAD! USE IT IN A SEPARATE THREAD!

  Parameters:
    conn (connection.Connection): The connection to read commands from.
  """

  # Upon initial connection, we need to "home" klipper
  # since it's not a real 3D printer with endstops, we just
  # force set the position, and everything will be relative to that
  was_homed = False

  while True:
    try:
      print("Initializing websocket connection")
      websocket = create_connection(MOONRAKER_URL)

      if not was_homed:
        # Enable relative movements, and activate the motors
        websocket.send(build_klipper_ws_gcode_payload("""
          SET_KINEMATIC_POSITION X=500 Y=500 Z=180
          G91
          G1 X2 Y2
        """))

        was_homed = True

      while True:
        # Attempt to read a command from the connection
        cmd, *args = conn.recv().split(" ")

        if cmd == "move":
            # parse that string
            z, xy = float(args[0]), float(args[1])

            # build GCode
            # gcode = build_gcode_relative_move(axes, angle)
            # gcode = f"G1 X{xy} Y{xy} Z{z} F10000"
            gcode = f"FORCE_MOVE STEPPER=stepper_z DISTANCE={z} VELOCITY=50"

            # send GCode
            websocket.send(build_klipper_ws_gcode_payload(gcode))
        elif cmd == "shoot":
            gcode = f"""
                SET_SERVO SERVO=trigger ANGLE=180
            """
            # send GCode
            websocket.send(build_klipper_ws_gcode_payload(gcode))
        elif cmd == "noshoot":
            websocket.send(build_klipper_ws_gcode_payload(
                "SET_SERVO SERVO=trigger ANGLE=0"
            ))


        time.sleep(0.01) # if only python was event-driven
    except BrokenPipeError:
        print("oops")
