import subprocess
import os
import json
from json import JSONDecodeError

from adbutils import adb

import click

#   Trovare un modo per generalizzare i comandi da passare alla shell adb
#   possibile shell interattiva?

#   Realizzare una tabella dove mostra i dati dei dispositivi connessi,
#   cliccandoci sopra apre scrcpy

#   Quando il programma viene stoppato con command-C/ctrl-C allora deve
#   effettuare il dump dell'output su file se indicato dalla flag --out

#   Se specificato dalla flag, al termine del programma disconnetti tutti i dispositivi --kill

devices = []


def masscan(scan, port):
    if (scan is None) and (port is None):
        return

    if (scan is None) and port:
        print(f'ADB-GRABBER ERROR: -s/--scan ADDRESS/PORT is required if -p/--port {port} is specified')
        exit(2)
    if scan and (port is None):
        print(f'ADB-GRABBER ERROR: -s/--scan {scan} requires -p/--port PORT')
        exit(2)

    # Masscan sulla rete.
    subprocess.run(
        ['masscan', scan, '-p', port, '-oJ', 'devices.json'],
        capture_output=False
    )


def load(file):
    default_file = 'devices.json'

    if file is None:
        file = default_file

    if not os.path.exists('./' + file):
        print(f'ADB-GRABBER ERROR: ./{file} does not exists.')
        exit(2)

    # Caricamento del dump in memoria.
    with open(file, 'r') as f:
        try:
            data = json.load(f)
        except JSONDecodeError:
            print(f'ADB-GRABBER ERROR: {file} contains no devices.')
            exit(2)

        for d in data:
            # Controlla se il servizio trovato da masscan non è sulla porta adb
            if '5555' == d['ports'][0]['port']:
                continue

            devices.append(f"{d['ip']}:{d['ports'][0]['port']}")


def dump(out):
    pass


def connect():
    # Connette i dispositivi con adb
    for addr in devices:
        adb.connect(addr, timeout=2.0)

    print(adb.device_list())


@click.command()
@click.option('-s', '--scan', help='Rete + maschera per masscan')
@click.option('-p', '--port', help='Porta/e da passare a masscan')
@click.option('-f', '--file', help='File da dove caricare gli ip')
@click.option('-o', '--out', help='File di output')
def main(scan, port, file):
    masscan(scan, port)
    load(file)
    connect()


if __name__ == '__main__':
    main()
