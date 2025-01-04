import websocket
import time
import json
from multiprocessing import connection
from threading import Thread
from uuid import uuid4
import os

MOONRAKER_URL = os.getenv("MOONRAKER_WS_URL")
STEPPER_MAPPER = {
  "x": "stepper_x",
  "y": "stepper_y",
  "z": "stepper_z"
}

def steps_needed(delta_angle: float, step_angle: float, driven_teeth: float, driving_teeth: float):
  gear_ratio = driven_teeth / driving_teeth
  degrees_per_step_driven = step_angle / gear_ratio
  steps = delta_angle / degrees_per_step_driven
  return steps

def build_klipper_ws_gcode_payload(gcode: str, id: str | None = None) -> str:
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
  return f"FORCE_MOVE STEPPER=stepper_x DISTANCE={steps} VELOCITY=100"

class KlipperWebSocketClient:
  def __init__(self):
    self.was_homed = False
    self.ws = None

  def on_message(self, ws, message):
    pass
    # print(f"Received message: {message}")

  def on_error(self, ws, error):
    print(f"WebSocket error: {error}")

  def on_close(self, ws, close_status_code, close_msg):
    print("WebSocket closed")

  def on_open(self, ws):
    print("WebSocket connection opened")
    if not self.was_homed:
      gcode = """
        SET_KINEMATIC_POSITION X=500 Y=500 Z=180
        G91
        G1 X2 Y2
      """
      ws.send(build_klipper_ws_gcode_payload(gcode))
      self.was_homed = True

  def update_board(self):
    while True:
      try:
        # Read commands from the connection
        cmd, *args = self.conn.recv().split(" ")

        if cmd == "move":
          z, xy = float(args[0]), float(args[1])
          gcode = f"FORCE_MOVE STEPPER=stepper_z DISTANCE={z} VELOCITY=50"
        elif cmd == "shoot":
          gcode = f"SET_SERVO SERVO=trigger ANGLE=180"
        elif cmd == "noshoot":
          gcode = "SET_SERVO SERVO=trigger ANGLE=0"

        self.ws.send(build_klipper_ws_gcode_payload(gcode))

        time.sleep(0.01)
      except Exception as e:
        print(f"Error processing commands: {e}")

  def start(self, conn: connection.Connection):
    self.conn = conn
    self.ws = websocket.WebSocketApp(
      MOONRAKER_URL,
      on_open=self.on_open,
      on_message=self.on_message,
      on_error=self.on_error,
      on_close=self.on_close
    )

    # Run forever in separate thread
    # self.ws.run_forever(reconnect=0)
    self.wst = Thread(target=self.ws.run_forever, kwargs={"reconnect": 0})
    self.wst.start()
    self.update_board()
