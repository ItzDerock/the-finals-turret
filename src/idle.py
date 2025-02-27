from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from multiprocessing import Process, Pipe
from send import KlipperWebSocketClient
from cli import options
from random import randint
from time import sleep

parent_conn, child_conn = Pipe(duplex=True)
client = KlipperWebSocketClient(True)
p = Process(target=client.start, args=(child_conn,))
if not options.dry_run:
  p.start()
  print("[i] Spawned communication thread")

while True:
  print("doing random move")
  angle = randint(90, 270)
  speed = randint(1000, 4000)
  parent_conn.send(f"move {angle} {speed}")
  sleep(randint(2000, 5000) / 1000)
