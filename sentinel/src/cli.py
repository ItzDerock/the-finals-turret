from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true')
parser.add_argument('-v', '--video', default='/dev/video32')
parser.add_argument('-V', '--verbose', action='store_true')
parser.add_argument('-m', '--hef', default='model/yolov8s_pose.hef')
parser.add_argument('-b', '--board', default='/dev/ttyUSB0')
options = parser.parse_args()

# Let user know of certain flags
if options.dry_run:
  print("[!] Dry-run mode. Commands will not be sent.")
