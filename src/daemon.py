import socket
from json import JSONEncoder, loads


class Daemon:
    class Encoder(JSONEncoder):
        def default(self, obj):
            return list(obj)

    def __init__(self, host='', port=65535):
        self.socket = socket.socket()
        self.socket.bind((host, port))
        self.socket.listen()
        self.devices = set()
        self.run()

    def get_devices(self):
        return self.devices

    def add_devices(self, devices=[]):
        for device in devices:
            self.devices.add(device)

    def run(self):
        while True:
            conn, addr = self.socket.accept()
            if conn:
                string = conn.recv(1024).decode()
                if string == 'list':
                    conn.sendall(self.Encoder().encode(self.devices).encode())
                elif '[' in string:
                    temp = set(loads(string))
                    for i in temp:
                        self.devices.add(i)
            conn.close()
