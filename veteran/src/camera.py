import os
HFOV_DEFAULT = int(os.getenv("CAMERA_HFOV", 170))
VFOV_DEFAULT = int(os.getenv("CAMERA_VFOV", -1))

def pixel_to_angle(x, y, width=1920, height=1080, hfov=HFOV_DEFAULT, vfov=VFOV_DEFAULT):
  """
  Maps a pixel position on the frame to the real-world horizontal and vertical angles.

  Parameters:
  x (int): The x-coordinate of the pixel on the frame.
  y (int): The y-coordinate of the pixel on the frame.
  width (int): The width of the frame in pixels (default 1920 for 1080p).
  height (int): The height of the frame in pixels (default 1080 for 1080p).
  hfov (float): The horizontal field of view of the camera in degrees (default 78.0 for C920).
  vfov (float): The vertical field of view of the camera in degrees. If -1, it will be calculated based on aspect ratio.

  Returns:
  (float, float): Tuple containing the horizontal angle and vertical angle in degrees.
  """

  # Calculate the vertical field of view if not provided, assuming the aspect ratio of the frame
  if vfov == -1:
    vfov = hfov * (height / width)

  # Calculate the center of the frame
  cx, cy = width / 2, height / 2

  # Calculate angle per pixel for horizontal and vertical
  angle_per_pixel_x = hfov / width
  angle_per_pixel_y = vfov / height

  # Calculate the offset from the center
  delta_x = x - cx
  delta_y = y - cy

  # Map to real-world angles
  horizontal_angle = delta_x * angle_per_pixel_x
  vertical_angle = delta_y * angle_per_pixel_y

  return horizontal_angle, vertical_angle
