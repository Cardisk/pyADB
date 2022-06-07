import subprocess
import os
import json
from json import JSONDecodeError
import pickle

from time import sleep

from rich.console import Console
from rich.table import Table

from adbutils import adb

import Pyro4
import Pyro4.errors
import Pyro4.naming

import click

#   Trovare un modo per generalizzare i comandi da passare alla shell adb
#   possibile shell interattiva?

#   Realizzare una tabella dove mostra i dati dei dispositivi connessi,
#   cliccandoci sopra apre scrcpy

#   Quando il programma viene stoppato con command-C/ctrl-C allora deve
#   effettuare il dump dell'output su file se indicato dalla flag --out

#   Se specificato dalla flag, al termine del programma disconnetti tutti i dispositivi --kill


console = Console()


def cache_save(name, obj):
    if os.path.exists('./cache/' + name + '.pkl'):
        console.print(f'[red]CACHE[/]: {name} exists already, try a different name or delete it from directory.')
        return
    with open('./cache/' + name + '.pkl', 'wb') as f:
        pickle.dump(obj, f)
    console.print(f'[green]CACHE[/]: {obj} saved to cache.')


def cache_recall(name):
    if not os.path.exists('./cache/' + name + '.pkl'):
        console.print(f'[red]CACHE[/]: {name} does not exist.')
        return
    with open('./cache/' + name + '.pkl', 'rb') as f:
        obj = pickle.load(f)
    console.print(f'[green]CACHE[/]: {obj} loaded from cache.')
    return obj


# def proxy(uri):
#     return Pyro4.Proxy(uri)


@click.group()
def cli():
    # daemon = proxy('PYRONAME:mimdaemon')
    # try:
    #     daemon.check()
    # except Pyro4.errors.NamingError:
    #     subprocess.run(
    #         ['python3', 'server.py'], capture_output=True
    #     )
    #     daemon = proxy('PYRONAME:mimdaemon')
    pass


@click.command()
@click.option('-n', '--net', help='Rete + maschera per masscan', required=True)
@click.option('-p', '--port', help='Porta/e da passare a masscan', required=True)
def masscan(net, port):
    # Masscan sulla rete.
    with console.status('[yellow]Performing mass scan[/]', spinner='dots'):
        scan_res = subprocess.run(
            ['masscan', net, '-p', port, '-oJ', 'devices.json'],
            capture_output=True
        )
    if scan_res.returncode != 0:
        console.print(f'[bold red]ERROR[/]: Failed to execute mass scan [cyan](permission error?)[/]')
        console.print(f'[bold cyan]GOT[/]: [red]{scan_res.stderr}[/]')


@click.command()
@click.option('-f', '--file', help='File da dove caricare gli ip', default='devices.json')
def load(file):
    if not os.path.exists('./' + file):
        console.print(f'[bold red]ERROR[/]: {file} does not exist.')
        return

    with open(file, 'r') as f:
        try:
            data = json.load(f)
            console.print(f'[bold green]SUCCESS[/]: Data got from file {file}')
        except JSONDecodeError:
            console.print(f'[bold red]ERROR[/]: Unable to read json data from {file} [cyan](empty?)[/]')
            return

    devices = []
    for d in data:
        # Controlla se il servizio trovato da masscan non è sulla porta adb
        if '5555' == d['ports'][0]['port']:
            continue
        devices.append(f"{d['ip']}:{d['ports'][0]['port']}")

    cache_save('devices', devices)


def dump(out):
    pass


@click.command()
def connect():
    devices = cache_recall('devices')
    with console.status('[yellow]Connecting devices[/]', spinner='dots'):
        # sleep(5) # metti sta sleep e goditi lo spettacolo
        # Connette i dispositivi con adb
        for addr in devices:
            adb.connect(addr, timeout=2.0)
    console.print('[green bold]CONNECTED[/]')


@click.command('show')
def show_devices():
    table = Table()
    table.add_column("Devices address", style="cyan bold")
    table.add_column("Present", style="cyan bold")
    table.add_column("ADB status", style="cyan bold")
    devices = adb.track_devices()

    # Da generatore a lista per i primi n elementi,
    # adb.track_devices() non termina ma continua ad ascoltare cambiamenti
    for device in [next(devices) for _ in range(len(adb.device_list()))]:
        table.add_row(str(device.serial), str(device.present), str(device.status))

    console.print(table)


cli.add_command(masscan)
cli.add_command(load)
cli.add_command(show_devices)
cli.add_command(connect)

if __name__ == '__main__':
    cli()
