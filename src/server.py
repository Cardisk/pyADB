import Pyro4.errors
import subprocess

class MimDaemon(object):
    devices = []

    @Pyro4.expose
    def get_list(self):
        return self.devices

    @Pyro4.expose
    def set_list(self, devices):
        self.devices = devices

    @Pyro4.expose
    def check(self):
        pass


def publish():
    Pyro4.Daemon.serveSimple(
        {
            MimDaemon: 'mimdaemon'
        },
        ns=True, verbose=False
    )

try:
    publish()
except Pyro4.errors.NamingError:
    subprocess.run(['python3', '-m', 'Pyro4.naming'], capture_output=True)
    publish()