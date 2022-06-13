import pathlib
import subprocess
import json
from json import JSONDecodeError
from rich.console import Console, RenderableType
from rich.progress import track, Progress, Column, Text, StyleType, Task, JustifyMethod, ProgressColumn, SpinnerColumn
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

    :param status: Status
    :return: A list
    """

    device_tracker = adb.track_devices()
    devices = []
    for device in [next(device_tracker) for _ in range(len(adb.device_list()))]:
        if device.status == status:
            devices.append(device)
    return devices


def connected_devices() -> Table:
    """
    Creates a table containing all the devices connected.

    :return: A table
    """

    table = Table(expand=True, show_lines=True)
    table.add_column("Devices address", style="cyan bold")
    table.add_column("Present", style="cyan bold")
    table.add_column("ADB status", style="cyan bold")

    devices = get_by_status('device')

    with console.status('[yellow]Executing[/]', spinner='dots'):
        for device in devices:
            table.add_row(str(device.serial), str(device.present), str(device.status))

    return table


class UpdatableTextColumn(ProgressColumn):
    """
    This special type of column represent an extension for the original TextColumn
    provided from rich. With this class you can instantiate an object and call the
    setter method to update the displayable text.
    """

    def __init__(self, text: str = '',
                 table_column: Optional[Column] = None,
                 style: StyleType = "none",
                 justify: JustifyMethod = "left"
                 ):
        self.text = text
        self.style = style
        self.justify = justify
        super().__init__(table_column=table_column)

    def set_text(self, new_text: str) -> None:
        self.text = new_text

    def render(self, task: "Task") -> RenderableType:
        text = Text(self.text, style=self.style, justify=self.justify)
        return text


# COMMANDS

@click.group()
def cli():
    pass


@cli.command()
@click.help_option('-h', '--help')
@click.argument('net', nargs=1, required=True)
@click.argument('port', nargs=1, required=True)
@click.option('--ipv6', help='IPV6 flag', is_flag=True)
def masscan(net: str, port: Union[str, int], ipv6: bool) -> None:
    """
    Performs a masscan on the given net (example: 192.168.1.0/24)
    and check if there are services listening to the given port or range
    (example1: 80; example2: 80-100; example3: 80,90-100).
    It can accept both ipv4 and ipv6 addresses but if you want to use the
    second type, you need to specify --ipv6 flag.
    When typing the address, the network mask has to be specified with its
    bit representation, like in the example above.

    :Usage example: python3 main.py masscan 192.168.1.0/24 80

    :param net: Network/Mask

    :param port: Port or range of ports

    :param ipv6: Flag to know if the passed address is ipv6
    """

    if not net or not port:
        console.print('[bold red]You need to provide both network/mask and port/s[/]')
        return

    # ipv4 validation TODO: may also add ipv6 validation
    if not ipv6:
        socket_components = net.split('/')
        if len((network := socket_components[0]).split('.')) != 4:
            console.print(f'[bold red]ERROR:[/] {network} is not a valid IPV4 address.')
            return

        if len(mask := socket_components[1]) > 2:
            console.print(
                f'[bold red]ERROR:[/] {mask} is not a valid representation of a bit mask [cyan](example: .../24)[/]'
            )
            return

    p = subprocess.Popen(['masscan', net, '-p', port, '-oJ', 'devices.json'], stdout=subprocess.PIPE,
                         bufsize=10000,
                         stderr=subprocess.STDOUT,
                         universal_newlines=True)

    found_column = UpdatableTextColumn("", justify='center', style='bold green')
    waiting_column = UpdatableTextColumn("", justify='center', style='bold blue')
    with Progress(
            SpinnerColumn(spinner_name='dots', finished_text='✔'),
            *Progress.get_default_columns(),
            found_column,
            waiting_column
    ) as progress:
        scan_task = progress.add_task('[yellow bold]Performing masscan', total=100.00)
        while (line := p.stdout.readline()) != '':
            if '%' not in line:
                match = re.match(r'[\s]+', line)
                if match is None:
                    progress.console.print(f'[cyan bold]SUBPROCESS[/]: {line}', end='')
            else:
                fields = line.split(',')
                if 'waiting' in fields[2]:
                    waiting_column.set_text(fields[2].strip().replace('-secs', 's'))
                else:
                    found_column.set_text(fields[3].strip().replace('\n', '').upper())
                progress.update(scan_task, completed=float(fields[1][:fields[1].rfind('%')]))


@cli.command()
@click.help_option('-h', '--help')
@click.option('-f', '--file', help='JSON file containing the result of a masscan search', default='devices.json')
def load(file: str) -> None:
    """
    Loads the sockets found by masscan command into a cache_file.
    You can also provide a different file specifying the path/to/file.json with --file option.
    Note that only sockets with ADB port open will be considered.

    :Usage example: python3 main.py load

    :param file: File (default: devices.json)
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
@click.help_option('-h', '--help')
@click.option('-s', '--socket', help='Specific socket address')
def connect(socket: str) -> None:
    """
    Connects all the devices found into the cache_file to the given adb session.

    :Usage example: python3 main.py connect

    :param socket: Specific socket to connect
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
@click.help_option('-h', '--help')
def show_devices() -> None:
    """
    Shows a table with the information of the connected devices.

    :Usage example: python3 main.py show
    """
    console.print(connected_devices())


@cli.command('broad-cmd')
@click.help_option('-h', '--help')
@click.argument('command', nargs=-1, required=True)
def broadcast_command(command: str) -> None:
    """
    Executes a shell command to all the connected devices.
    If at least one device returned an output, the user can choose
    if he wants to see it or not.

    :Usage example: python3 main.py broad-cmd <command>

    :param command: Command
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if not command:
        console.print(f'[bold red]There is no command to execute.[/]')
        return

    output = dict()
    devices = get_by_status('device')

    for item in track(devices, description='[bold yellow]Executing[/]'):
        device = adb.device(item.serial)
        output[item.serial] = device.shell(command)
    console.print('[bold green]DONE[/]')

    if len(output) > 0:
        check = False
        for key in output.keys():
            if len(output.get(key)) > 0:
                check = True
                break
        if check:
            while True:
                console.print('You obtained some results, do you wanna display them? [cyan](Y/n)[/] ', end='')
                answer = console.input()

                if answer == 'Y' or answer == 'y' or answer == 'YES' or answer == 'yes' or answer == '':
                    table = Table(expand=True, show_lines=True)
                    table.add_column("Device", style="cyan bold", justify='center')
                    table.add_column("Output", style="cyan bold", justify='left')

                    for key in output.keys():
                        table.add_row(key, output.get(key))

                    console.print(table)
                    break

                elif answer == 'N' or answer == 'n' or answer == 'NO' or answer == 'no':
                    break

                else:
                    console.print('[bold red]Please type only (Y/n) letters.[/]', end='\r')
                    sleep(2)
        else:
            console.print('[blue]No output returned.[/]')


@cli.command('exec')
@click.help_option('-h', '--help')
@click.argument('socket', nargs=1, required=True)
@click.argument('command', nargs=-1, required=True)
def execute(socket: str, command: str) -> None:
    """
    Execute the given command to the given remote device.
    If an output is returned it will print it.

    :Usage example: python3 main.py 192.168.1.10:5555 <command>

    :param socket: Socket address

    :param command: Command
    """

    devices = get_by_status('device')

    if len(devices) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if socket not in devices:
        console.print(f'[bold red]{socket} not connected.[/]')
        return

    if not command:
        console.print(f'[bold red]There is no command to execute.[/]')
        return

    try:
        device = adb.device(socket)
        output = device.shell()
    except adbutils.AdbError:
        console.print('[bold red]Something went wrong during the execution.[/]')

    if len(output > 0):
        console.print(f'[bold green]OUTPUT:[/] {output}')
    else:
        console.print('[blue]No output returned.[/]')


@cli.command('push')
@click.help_option('-h', '--help')
@click.argument('local', nargs=1, required=True)
@click.argument('remote', nargs=1, required=True)
def push_file(local: str, remote: str) -> None:
    """
    Pushes a local file into all the remote machines.
    The remote path has to be absolute.

    :Usage example: python3 main.py push example.txt /sdcard

    :param local: Local file

    :param remote: Remote destination
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if not local or not remote:
        console.print('[bold red]You need to provide both local and absolute remote path.[/]')
        return

    if not pathlib.PurePath(remote).is_absolute():
        console.print(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')
        return

    if not remote.endswith(local):
        filename = local.split('/')[-1]
        remote = os.path.join(remote, filename)

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


@cli.command('pull')
@click.help_option('-h', '--help')
@click.argument('socket', nargs=1, required=True)
@click.argument('remote', nargs=1, required=True)
@click.argument('local', nargs=1, required=True)
def pull_file(socket: str, remote: str, local: str) -> None:
    """
    Pull a file from the specified remote device into the local one.

    :Usage example: python3 main.py pull 192.168.1.10:5555 /sdcard/remote.txt local.txt

    :param socket: Socket address

    :param remote: Remote path/to/file

    :param local: Local path/to/file
    """

    devices = get_by_status('device')

    if len(devices) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if socket not in devices:
        console.print(f'[bold red]{socket} not connected.[/]')
        return

    if not pathlib.PurePath(remote).is_absolute():
        console.print(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')
        return

    try:
        device = adb.device(socket)
        device.sync.pull(str(remote), str(local))
    except adbutils.AdbError:
        console.print('[bold red]Something went wrong during communication.[/]')
    console.print(f'[bold green]SUCCESS:[/] you stole {remote} -> {local} little file.')


@cli.command()
@click.help_option('-h', '--help')
@click.argument('apk', nargs=1, required=True)
def install(apk: str) -> None:
    """
    Performs the installation of the given apk on all the connected devices.
    The apk can be bot a path/to/file.apk and url/to/file.apk

    :Usage example: python3 main.py install application.apk

    :param apk: Apk file
    """

    if len(adb.device_list()) == 0:
        console.print('[bold red]No devices connected.[/]')
        return

    if not apk:
        console.print('[bold red]You need to provide an apk file.[/]')
        return

    success = False
    devices = get_by_status('device')

    for item in track(devices, description='[yellow]Installing items[/]'):
        try:
            device = adb.device(item.serial)
            device.install(apk)
            success = True
        except Union[RuntimeError, TypeError, adbutils.AdbError, adbutils.AdbInstallError]:
            continue
    if success is True:
        console.print('[bold green]SUCCESS:[/] your brand new app is now available everywhere!')
    else:
        console.print('[bold red]Something went wrong during the installation[/]')


@cli.command('clear')
@click.help_option('-h', '--help')
def clear_cache() -> None:
    """Removes all the cache elements to free some space."""

    with console.status('[yellow]Cleaning[/]', spinner='dots'):
        if os.path.exists(user_cache_dir(cache_name, cache_author)):
            shutil.rmtree(user_cache_dir(cache_name, cache_author), ignore_errors=True)
    console.print('[bold green]SUCCESS:[/] there is no more messy around here.')


@cli.command('kill-server')
@click.help_option('-h', '--help')
def kill_server() -> None:
    """Emulates the adb kill-server command. All the devices will be disconnected from this adb session."""

    devices = get_by_status('device')
    for item in track(devices, description='[yellow]Disconnecting[/]'):
        try:
            adb.disconnect(item.serial)
        except adbutils.AdbError:
            continue
    console.print('[bold red]DISCONNECTED:[/] everything fine, but now you are alone.')


if __name__ == '__main__':
    cli()
