from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-d', '--dry-run', action='store_true')
parser.add_argument('-q', '--quantize', action='store_true')
parser.add_argument('-v', '--video', default='/dev/video32')
parser.add_argument('-V', '--verbose', action='store_true')
parser.add_argument('-m', '--model', default='yolov8n.pt')
parser.add_argument('-r', '--resolution', default='1920x1080')
parser.add_argument('-H', '--hailo', action='store_true')
options = parser.parse_args()

# Let user know of certain flags
if options.dry_run:
  print("[!] Dry-run mode. Commands will not be sent.")

# Break options.resolution into width and height
options.resolution = options.resolution.split('x')
options.resolution = (int(options.resolution[0]), int(options.resolution[1]))
