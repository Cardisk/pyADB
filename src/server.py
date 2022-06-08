import socket


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


class Daemon:
    def __init__(self, host='', port=65535):
        self.socket = socket.socket()
        self.socket.bind((host, port))
        self.socket.listen(1)
        self.devices = set()
        self.run()

    def get_devices(self):
        return list(self.devices)

    def add_devices(self, devices=[]):
        for device in devices:
            self.devices.add(device)

    def run(self):
        while True:
            conn, addr = self.socket.accept()
            if conn:
                string = conn.recv(1024).decode()

                if 'stop' in string:
                    self.socket.close()
                    break

                if 'list' in string:
                    conn.sendall(stringify(list(self.devices)).encode())
                elif '[' in string:
                    temp = reverse_stringify(string)
                    for i in temp:
                        self.devices.add(i)

            conn.close()


Daemon()
