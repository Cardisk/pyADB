# CLIENT CODE

import socket
import subprocess
import time

socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    socket.connect(('localhost', 65535))
except:
    print('starting daemon')
    subprocess.Popen(['python3', './server.py'], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    socket.connect(('localhost', 65535))

socket.sendall('stop'.encode())
print(socket.recv(1024).decode())
