import subprocess
import json
from json import JSONDecodeError

from time import sleep

import pickle

from rich.console import Console
from rich.table import Table

import adbutils
from adbutils import adb

from appdirs import *

import click

#   Realizzare una tabella dove mostra i dati dei dispositivi connessi,
#   cliccandoci sopra apre scrcpy (parzialmente completato)

# VARIABLES

console = Console()
cache_name = 'MIM_Orchestrator'
cache_author = 'Bessi-Cardinaletti'


def cache_save(name, obj):
    if not os.path.exists(user_cache_dir(cache_name, cache_author)):
        os.mkdir(user_cache_dir(cache_name, cache_author))

    mode = 'wb'
    if os.path.exists(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl'):
        mode = 'ab'

    with open(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl', mode) as f:
        pickle.dump(obj, f)
    console.print(f'[green]CACHE[/]: {obj} saved to cache.')


def cache_recall(name):
    if not os.path.exists(user_cache_dir(cache_name, cache_author)):
        os.mkdir(user_cache_dir(cache_name, cache_author))

    if not os.path.exists(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl'):
        console.print(f'[red]CACHE[/]: {name} does not exist.')
        return
    with open(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl', 'rb') as f:
        obj = pickle.load(f)
    console.print(f'[green]CACHE[/]: {obj} loaded from cache.')
    return set(obj)


@click.group()
def cli():
    pass


@cli.command()
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


@cli.command()
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


@cli.command()
@click.option('-s', '--socket', help='Socket ip specifico da connettere')
def connect(socket):
    success = False
    if not socket:
        devices = cache_recall('devices')
        with console.status('[yellow]Connecting devices[/]', spinner='dots'):
            # sleep(5) # metti sta sleep e goditi lo spettacolo
            # Connette i dispositivi con adb
            for addr in devices:
                try:
                    adb.connect(addr, timeout=2.0)
                    success = True
                except adbutils.AdbTimeout:
                    pass
    else:
        try:
            adb.connect(socket, timeout=2.0)
            success = True
        except adbutils.AdbTimeout:
            pass
    if success is True:
        console.print('[green bold]CONNECTED[/]')
    else:
        console.print('[bold red]Something went wrong during connection[/]')


@cli.command('show')
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


@cli.command('broad-cmd')
def broadcast_command():
    output = dict()
    devices = adb.track_devices()

    command = console.input('[cyan]$[/] ')

    if not command:
        console.print(f'[bold red]You need to type something[/]')
        return

    with console.status('[yellow]Executing[/]', spinner='dots'):
        for item in [next(devices) for _ in range(len(adb.device_list()))]:
            device = adb.device(item.serial)
            output[item.serial] = item.serial + 'EOL' + device.shell(command)
    console.print('[bold green]COMPLETED[/]')

    # Se anche solo un dispositivo torna output prova a stamparlo
    if len(output) > 0:
        check = False
        for key in output:
            if len(output[key].split("EOL")[1]) > 0:
                check = True
                break
        if check:
            while True:
                console.print('You obtained some results, do you wanna display them? [cyan](Y/n)[/] ', end='')
                answer = console.input()

                if answer == 'Y' or answer == 'y' or answer == 'YES' or answer == 'yes':
                    # Stampa l'output come tabella (seriale -> output)
                    table = Table()
                    table.add_column("Device", style="cyan bold", justify='center')
                    table.add_column("Output", style="cyan bold", justify='left')

                    for key in output:
                        group = output[key].split('EOL')
                        if len(group) > 2:
                            continue
                        table.add_row(group[0], group[1])

                    console.print(table)
                    break

                elif answer == 'N' or answer == 'n' or answer == 'NO' or answer == 'no':
                    # Ignora
                    break

                else:
                    # Richiede nuovamente all'utente
                    console.print('[bold red]Please type only (Y/n) letters.[/]', end='\r')
                    sleep(2)
        else:
            console.print('[blue]There is no output for your command[/]')


@cli.command('push')
@click.option('-l', '--local', help='File locale', required=True)
@click.option('-r', '--remote', help='Dove metterlo sul dispositivo remoto', required=True)
def push_file(local: str, remote: str):
    if not remote.startswith('/'):
        console.print(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')
        return

    success = False
    devices = adb.track_devices()
    with console.status('[yellow]Pushing items', spinner='dots'):
        for item in [next(devices) for _ in range(len(adb.device_list()))]:
            try:
                device = adb.device(item.serial)
                device.sync.push(local, remote)
                success = True
            except RuntimeError:
                continue
            except TypeError:
                continue
            except adbutils.AdbError:
                continue
    if success is True:
        console.print('[bold green]PUSH COMPLETED[/]')
    else:
        console.print('[bold red]Something went wrong during the transfer[/]')


@cli.command('kill-server')
def kill_server():
    devices = adb.track_devices()
    with console.status('[yellow]Disconnecting', spinner='dots'):
        for item in [next(devices) for _ in range(len(adb.device_list()))]:
            try:
                adb.disconnect(item.serial)
            except adbutils.AdbError:
                continue
    console.print('[bold red]DISCONNECTED[/]')


# Con il try-except tecnicamente non dovrebbe crashare con CTRL-C. Per scrupolo sarebbe da aggiungere ovunque.
if __name__ == '__main__':
    try:
        cli()
    except KeyboardInterrupt:
        pass
