import cv2
import sys

def main():
    # Check if a video source is provided
    if len(sys.argv) > 1:
        # Try to open the video file or camera source
        try:
            # Attempt to convert to int in case it's a camera index
            source = int(sys.argv[1])
        except ValueError:
            # If not an integer, treat as a file path
            source = sys.argv[1]
    else:
        # Default to webcam (camera index 0) if no source provided
        source = 0

    # Open the video capture
    cap = cv2.VideoCapture(source)

    # Check if video capture is opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open video source {source}")
        return

    # Window name
    window_name = "Video Display"

    try:
        while True:
            # Read a frame from the video
            ret, frame = cap.read()

            # Break the loop if no frame is read
            if not ret:
                print("End of video or unable to read frame")
                break

            # Display the frame
            cv2.imshow(window_name, frame)

            # Wait for 1ms and check for 'q' key to quit
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

    finally:
        # Release the video capture and close windows
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
