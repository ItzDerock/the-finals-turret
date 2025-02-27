import serial
import keyboard
import time

# Open the serial connection
device_path = '/dev/serial/by-id/usb-DerocksCoolProducts_Warden-if00'
ser = serial.Serial(device_path, 9600)  # Adjust baud rate if needed

def send_command(command):
    print(f"Sending: {command}")
    ser.write(f"{command}\n".encode())  # Add newline and encode to bytes

try:
    # Define key press handlers
    def w_pressed(e):
        send_command("v1500")

    def s_pressed(e):
        send_command("v1-500")

    def a_pressed(e):
        send_command("v0500")

    def d_pressed(e):
        send_command("v0-500")

    # Define key release handlers
    def vertical_released(e):
        send_command("v10")

    def horizontal_released(e):
        send_command("v00")

    # Register the key handlers
    keyboard.on_press_key("w", w_pressed)
    keyboard.on_press_key("s", s_pressed)
    keyboard.on_press_key("a", a_pressed)
    keyboard.on_press_key("d", d_pressed)

    keyboard.on_release_key("w", vertical_released)
    keyboard.on_release_key("s", vertical_released)
    keyboard.on_release_key("a", horizontal_released)
    keyboard.on_release_key("d", horizontal_released)

    print("Control script running. Press Ctrl+C to exit.")
    print("W: forward, S: backward, A: left, D: right")

    # Keep the script running
    keyboard.wait("esc")  # Exit when Escape key is pressed

except KeyboardInterrupt:
    print("Script terminated by user")
finally:
    # Clean up
    ser.close()
    print("Serial connection closed")
