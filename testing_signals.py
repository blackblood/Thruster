import os
import signal
import time

def parent_int_handler(signum, frame):
    print("parent_int_handler")

def child_int_handler(signum, frame):
    print("child_int_handler")

signal.signal(signal.SIGINT, parent_int_handler)

for _ in range(5):
    pid = os.fork()

    if pid == 0:
        signal.signal(signal.SIGINT, child_int_handler)
        time.sleep(10)
        os._exit(0)
    else:
        print("created process pid: %d" % pid)

try:
    while os.wait() != -1:
        continue
except OSError as exp:
    print(exp)
    
print("after wait")