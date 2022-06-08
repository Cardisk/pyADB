# CLIENT CODE

import socket
import subprocess
import time


def stringify(arr: list):
    space = ' '
    return space.join(arr)


def reverse_stringify(string: str):
    temp = string.split(' ')
    for i in temp:
        i = i.replace('\'', '')
        i = i.replace(',', '')
        i = i.replace('[', '')
        i = i.replace(']', '')
    return temp


def send(sock):
    s = input()
    sock.sendall(s.encode())
    print(sock.recv(1024).decode())


host = 'localhost'
port = 65535
connected = True

try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        send(s)
except ConnectionRefusedError:
    connected = False
    print('starting daemon')
    subprocess.Popen(['python3', './server.py'], shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
finally:
    if not connected:
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, port))
            send(s)
