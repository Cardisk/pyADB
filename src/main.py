import subprocess
import json
from json import JSONDecodeError
from rich.console import Console
from rich.progress import track, Progress
from rich.table import Table
import adbutils
from adbutils import adb
from time import sleep
import pickle
from appdirs import *
import shutil
from typing import Union, Optional, Set, Any
import re
import click

# VARIABLES

console = Console()
cache_name = 'MIM_Orchestrator'
cache_author = 'Bessi-Cardinaletti'


# UTILS

def cache_save(name: str, obj: object) -> None:
    """
    Saves to a cache file the passed object with pickle module.

    :param name: File name
    :param obj: Object
    :return: None
    """

    if not os.path.exists(user_cache_dir(cache_name, cache_author)):
        os.mkdir(user_cache_dir(cache_name, cache_author))

    mode = 'wb'
    if os.path.exists(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl'):
        mode = 'ab'

    with open(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl', mode) as f:
        pickle.dump(obj, f)
    console.print(f'[green]CACHE[/]: {obj} saved to cache.')


def cache_recall(name: str) -> Optional[Set[Any]]:
    """
    Loads into a set the content of the cache file.

    :param name: File name
    :return: A set
    """

    if not os.path.exists(user_cache_dir(cache_name, cache_author)):
        os.mkdir(user_cache_dir(cache_name, cache_author))

    if not os.path.exists(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl'):
        console.print(f'[red]CACHE[/]: {name} does not exist.')
        return
    with open(user_cache_dir(cache_name, cache_author) + '/' + name + '.pkl', 'rb') as f:
        obj = pickle.load(f)
    console.print(f'[green]CACHE[/]: {obj} loaded from cache.')
    return set(obj)


def get_by_status(status: str) -> list:
    """
    Utility function to get devices by status.

    :param status:
    :return: list
    """

    device_tracker = adb.track_devices()
    devices = []
    for device in [next(device_tracker) for _ in range(len(adb.device_list()))]:
        if device.status == status:
            devices.append(device)
    return devices


# COMMANDS

@click.group()
def cli():
    pass


@cli.command()
@click.option('-n', '--net', help='Where you need to perform you masscan [type: NET/MASK]', required=True)
@click.option('-p', '--port', help='Port range that you want to check [type: X or XX-YY or X,YY-ZZ]', required=True)
def masscan(net: str, port: Union[str, int]) -> None:
    """
    Performs a masscan on the given net (example: 192.168.1.0/24)
    and check if there are services listening to the given port or range.

    :param net: Network/Mask
    :param port: Port or range of port (example1: 80, example2: 80-100, example3: 80,90-100)
    :return: None
    """

    p = subprocess.Popen(['masscan', net, '-p', port, '-oJ', 'devices.json'], stdout=subprocess.PIPE,
                         bufsize=10000,
                         stderr=subprocess.STDOUT,
                         universal_newlines=True)
    with Progress() as progress:
        scan_task = progress.add_task('[yellow bold]Performing masscan', total=100.00)
        while (line := p.stdout.readline()) != '':
            if '%' not in line:
                match = re.match(r'[\s]+', line)
                if match is None:
                    progress.print(f'[cyan bold]SUBPROCESS[/]: {line}', end='')
            else:
                fields = line.split(',')
                if 'waiting' in fields[2]:
                    progress.print(fields[2], end='\r')
                else:
                    progress.print(fields[3].strip())
                progress.update(scan_task, completed=float(fields[1][:fields[1].rfind('%')]))


@cli.command()
@click.option('-f', '--file', help='JSON file containing the result of a masscan search', default='devices.json')
def load(file: str) -> None:
    """
    Loads the sockets found by masscan command into a cache_file.
    It can also load into the same file the content of another masscan JSON output file, given as a parameter.

    :param file: File -- default: devices.json
    :return: None
    """
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
        if '5555' == d['ports'][0]['port']:
            continue
        devices.append(f"{d['ip']}:{d['ports'][0]['port']}")

    cache_save('devices', devices)


@cli.command()
@click.option('-s', '--socket', help='Specific socket address that needs to be connected')
def connect(socket: str) -> None:
    """
    Connects all the devices found int the cache_file to the given adb session.

    :param socket: Socket
    :return: None
    """

    success = False
    if not socket:
        devices = cache_recall('devices')
        with console.status('[yellow]Connecting devices[/]', spinner='dots'):
            for addr in devices:
                try:
                    adb.connect(addr, timeout=2.0)
                    success = True
                except adbutils.AdbTimeout:
                    continue
    else:
        try:
            adb.connect(socket, timeout=2.0)
            success = True
        except adbutils.AdbTimeout:
            pass
    if success is True:
        console.print('[green bold]CONNECTED:[/] wow! You\'re not alone!')
    else:
        console.print('[bold red]Something went wrong during the connection[/]')


@cli.command('show')
def show_devices() -> None:
    """
    Shows a table with the informations of the connected devices.

    :return: None
    """

    table = Table(expand=True, show_lines=True)
    table.add_column("Devices address", style="cyan bold")
    table.add_column("Present", style="cyan bold")
    table.add_column("ADB status", style="cyan bold")

    devices = get_by_status('device')

    for device in track(devices, description='[yellow]Executing[/]'):
        table.add_row(str(device.serial), str(device.present), str(device.status))

    console.print(table)


@cli.command('broad-cmd')
def broadcast_command() -> None:
    """
    Executes a shell command to all the connected devices.

    :return: None
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    output = dict()
    devices = get_by_status('device')

    command = console.input('[cyan]$[/] ')

    if not command:
        console.print(f'[bold red]You need to type something.[/]')
        return

    for item in track(devices):
        device = adb.device(item.serial)
        output[item.serial] = item.serial + 'EOL' + device.shell(command)
    console.print('[bold green]DONE[/]')

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
                    table = Table(expand=True, show_lines=True)
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
                    break

                else:
                    console.print('[bold red]Please type only (Y/n) letters.[/]', end='\r')
                    sleep(2)
        else:
            console.print('[blue]There is no output for your command[/]')


@cli.command('push')
@click.option('-l', '--local', help='File in a local path', required=True)
@click.option('-r', '--remote', help='Remote absolute path', required=True)
def push_file(local: str, remote: str) -> None:
    """
    Pushes a local file into all the remote machines.

    :param local: Local file
    :param remote: Remote destination
    :return: None
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if not remote.startswith('/'):  # TODO: far fare a pathlib
        console.print(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')
        return

    if not remote.endswith(local):  # non mi piace si potrebbe rompere ma meglio di not in
        remote += '/' + local

    success = False
    devices = get_by_status('device')

    for item in track(devices, description='Pushing'):
        try:
            device = adb.device(item.serial)
            device.sync.push(str(local), str(remote))
            success = True
        except Union[TypeError, RuntimeError, adbutils.AdbError]:
            continue
    if success is True:
        console.print('[bold green]PUSH:[/] your little file is now property of everyone!')
    else:
        console.print('[bold red]Something went wrong during the transfer[/]')


@cli.command()
@click.option('-a', '--apk', help='Apk file that has to be installed [type: path/file.apk or url/file.apk]',
              required=True)
def install(apk: str) -> None:
    """
    Performs the installation of the given apk on all the connected devices.

    :param apk: Apk file
    :return: None
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    success = False
    devices = get_by_status('device')

    for item in track(devices, description='[yellow]Installing items[/]'):
        try:
            device = adb.device(item.serial)
            device.install(apk)
            success = True
        except RuntimeError:
            continue
        except TypeError:
            continue
        except adbutils.AdbError:
            continue
    if success is True:
        console.print('[bold green]SUCCESS:[/] your brand new app is now available everywhere!')
    else:
        console.print('[bold red]Something went wrong during the installation[/]')


@cli.command('cache-cls')
def clear_cache() -> None:
    """
    Removes all the cache elements to free some space.

    :return: None
    """

    with console.status('[yellow]Cleaning[/]', spinner='dots'):
        if os.path.exists(user_cache_dir(cache_name, cache_author)):
            shutil.rmtree(user_cache_dir(cache_name, cache_author), ignore_errors=True)
    console.print('[bold green]SUCCESS:[/] there is no more messy around here.')


@cli.command('kill-server')
def kill_server() -> None:
    """
    Emulates the adb kill-server command. All the devices will be disconnected from this adb session.

    :return: None
    """

    devices = get_by_status('device')
    for item in track(devices, description='[yellow]Disconnecting[/]'):
        try:
            adb.disconnect(item.serial)
        except adbutils.AdbError:
            continue
    console.print('[bold red]DISCONNECTED:[/] everything fine, but now you are alone.')


if __name__ == '__main__':
    cli()
