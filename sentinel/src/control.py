from multiprocessing.connection import Connection
import serial
from PID_Py.PID import PID

class Control:
    pid_tilt: PID
    pid_pan: PID

    def __init__(self, port: str | None):
        if port == 'sim' or port is None:
            self.serial = serial.Serial()
        else:
            self.serial = serial.Serial(port, 115200)

        self.pid_tilt = PID(kp=4, ki=0, kd=8)
        self.pid_pan = PID(kp=4, ki=0, kd=8)

    def updateLoop(self, pipe: Connection):
        while True:
            pan_error, tilt_error = pipe.recv()
            self.update(pan_error, tilt_error)
            print(pan_error, tilt_error)


    # Runs single update
    def update(self, pan_error, tilt_error):
        pan_correction = self.pid_pan(setpoint=0, processValue=pan_error)
        tilt_correction = self.pid_tilt(setpoint=0, processValue=tilt_error)
        self.panVelocity(pan_correction)
        self.tiltVelocity(tilt_correction)

    # Low level communication
    def send(self, data):
        if self.serial.is_open:
            self.serial.write(data)

    def receive(self):
        return self.serial.read()

    def panVelocity(self, velocity):
        self.send('v0' + str(velocity))

    def tiltVelocity(self, velocity):
        self.send('v1' + str(velocity))

    def trigger(self, active):
        self.send('t' + str(active).lower())
