import pathlib
import json
from json import JSONDecodeError
from rich.progress import track, Progress, SpinnerColumn
import adbutils
from time import sleep
import shutil
from typing import Union
import re
import click

from Utils import *


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
        error('[bold red]You need to provide both network/mask and port or range.[/]')

    # ipv4 validation TODO: may also add ipv6 validation
    if not ipv6:
        socket_components = net.split('/')
        if len((network := socket_components[0]).split('.')) != 4:
            error(f'[bold red]ERROR:[/] {network} is not a valid IPV4 address.')

        components = network.split('.')
        for component in components:
            if 0 > int(component) > 255:
                error(f'[bold red]ERROR:[/] {network} is not a valid IPV4 address.')

        if len(mask := socket_components[1]) > 2:
            error(f'[bold red]ERROR:[/] {mask} is not a valid representation of a bit mask [cyan](example: .../24)[/]')

    with subprocess.Popen(['masscan', net, '-p', port, '-oJ', 'devices.json'], stdout=subprocess.PIPE,
                          bufsize=10000,
                          stderr=subprocess.STDOUT,
                          universal_newlines=True) as p:

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
                    match = re.match(r'\s+', line)
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
        error(f'[bold red]ERROR[/]: {file} does not exist.')

    with open(file, 'r') as f:
        try:
            data = json.load(f)
            log(f'[bold green]SUCCESS[/]: Data got from file {file}')
        except JSONDecodeError:
            error(f'[bold red]ERROR[/]: Unable to read json data from {file} [cyan](empty?)[/]')

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
    connection = None
    if not socket:
        devices = cache_recall('devices')

        if len(devices) == 0:
            error('[bold red]ERROR:[/] there is no device inside the cache file.')

        with console.status('[yellow]Connecting devices[/]', spinner='dots'):
            for addr in devices:
                try:
                    adb.connect(addr, timeout=2.0)
                    success = True
                except adbutils.AdbTimeout:
                    continue
    else:
        try:
            connection = adb.connect(socket, timeout=2.0)
            success = True
        except adbutils.AdbTimeout:
            pass
    if success is True:
        if connection is not None:
            if 'failed' in connection or 'unable' in connection or 'already' in connection:
                error(f'[bold red]ERROR:[/] {connection}')
            else:
                log(f'[bold green]CONNECTED:[/] you\'re now friend of {socket}!')
        else:
            log('[green bold]CONNECTED:[/] wow! You\'re not alone!')
    else:
        error('[bold red]Something went wrong during the connection[/]')


@cli.command('show')
@click.help_option('-h', '--help')
def show_devices() -> None:
    """
    Shows a table with the information of the connected devices.

    :Usage example: python3 main.py show
    """
    log(connected_devices())


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
        error('[bold red]No devices connected.[/]')

    if not command:
        error(f'[bold red]There is no command to execute.[/]')

    output = dict()
    devices = get_by_status('device')

    with console.status('[bold yellow]Executing[/]', spinner='dots'):
        for item in devices:
            device = adb.device(item.serial)
            output[item.serial] = device.shell(command)
    log('[bold green]DONE[/]')

    if len(output) > 0:
        check = False
        for key in output.keys():
            if len(output.get(key)) > 0:
                check = True
                break
        if check:
            while True:
                log('You obtained some results, do you wanna display them? [cyan](Y/n)[/] ', end='')
                answer = console.input()

                if answer == 'Y' or answer == 'y' or answer == 'YES' or answer == 'yes' or answer == '':
                    table = Table(expand=True, show_lines=True)
                    table.add_column("Device", style="cyan bold", justify='center')
                    table.add_column("Output", style="cyan bold", justify='left')

                    for key in output.keys():
                        table.add_row(key, output.get(key))

                    log(table)
                    break

                elif answer == 'N' or answer == 'n' or answer == 'NO' or answer == 'no':
                    break

                else:
                    log('[bold red]Please type only (Y/n) letters.[/]', end='\r')
                    sleep(2)
        else:
            log('[blue]No output returned.[/]')


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
        error('[bold red]No devices connected.[/]')

    found = False
    for item in devices:
        if item.serial == socket:
            found = True

    if not found:
        error(f'[bold red]{socket} not connected.[/]')

    if not command:
        error(f'[bold red]There is no command to execute.[/]')

    output = ''
    try:
        device = adb.device(socket)
        output = device.shell(command)
    except adbutils.AdbError:
        error('[bold red]Something went wrong during the execution.[/]')

    if len(output) > 0:
        log(f'[bold green]OUTPUT:[/] {output}')
    else:
        error('[blue]No output returned.[/]')


@cli.command('push')
@click.help_option('-h', '--help')
@click.argument('local', nargs=1, required=True)
@click.argument('remote', nargs=1, required=True)
@click.option('-s', '--socket', help='Specific device (socket address)')
def push_file(local: str, remote: str, socket: str) -> None:
    """
    Pushes a local file into all the remote machines.
    The remote path has to be absolute.
    If the argument --socket is specified the file
    will be pushed only to that.

    :Usage example: python3 main.py push example.txt /sdcard

    :param local: Local file

    :param remote: Remote destination

    :param socket: Specific device
    """

    if len(adb.device_list()) == 0:
        error('[bold red]No devices connected.[/]')

    if not local or not remote:
        error('[bold red]You need to provide both local and absolute remote path.[/]')

    if not pathlib.PurePath(remote).is_absolute():
        error(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')

    if not remote.endswith(local):
        filename = local.split('/')[-1]
        remote = os.path.join(remote, filename)

    success = False

    if not socket:
        devices = get_by_status('device')

        for item in track(devices, description='Pushing'):
            try:
                device = adb.device(item.serial)
                device.sync.push(str(local), str(remote))
                success = True
            except Union[TypeError, RuntimeError, adbutils.AdbError]:
                continue
    else:
        try:
            device = adb.device(socket)
            device.sync.push(str(local), str(remote))
            success = True
        except Union[TypeError, RuntimeError, adbutils.AdbError]:
            pass

    if success is True:
        who = socket if socket else 'everyone'
        log(f'[bold green]PUSH:[/] your little file is now property of {who}!')
    else:
        error('[bold red]Something went wrong during the transfer[/]')


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
        error('[bold red]No devices connected.[/]')

    found = False
    for item in devices:
        if item.serial == socket:
            found = True

    if not found:
        error(f'[bold red]{socket} not connected.[/]')

    if not pathlib.PurePath(remote).is_absolute():
        error(f'[bold red]PATH ERROR:[/] {remote} is not an absolute path.')

    try:
        device = adb.device(socket)
        device.sync.pull(str(remote), str(local))
    except adbutils.AdbError:
        error('[bold red]Something went wrong during communication.[/]')
    log(f'[bold green]SUCCESS:[/] you stole {remote} -> {local} little file.')


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
        error('[bold red]No devices connected.[/]')

    if not apk:
        error('[bold red]You need to provide an apk file.[/]')

    success = False
    devices = get_by_status('device')

    for item in track(devices, description='[yellow]Installing items[/]'):
        try:
            device = adb.device(item.serial)
            device.install(apk, nolaunch=True, uninstall=True, silent=True)
            success = True
        except Union[RuntimeError, TypeError, BrokenPipeError, adbutils.AdbError, adbutils.AdbInstallError]:
            continue
    if success is True:
        log('[bold green]SUCCESS:[/] your brand new app is now available everywhere!')
    else:
        error('[bold red]Something went wrong during the installation[/]')


@cli.command()
@click.option('-s', '--socket', help='Specific device')
def scrcpy(socket) -> None:
    """
    Launches a textual app with a list of connected sockets.
    Clicking on a socket panel it will automatically start scrcpy for that device

    :Usage example: python3 main.py scrcpy

    :param socket: Specific socket to display
    """

    if not socket:
        Display.run()
    else:
        with console.status('[yellow]Executing[/]', spinner='dots'):
            subprocess.run(['scrcpy', f'--tcpip={socket}'], capture_output=True)
        log('[bold green]DONE[/]')


@cli.command('clear')
@click.help_option('-h', '--help')
def clear_cache() -> None:
    """Removes all the cache elements to free some space."""

    with console.status('[yellow]Cleaning[/]', spinner='dots'):
        if os.path.exists(user_cache_dir(cache_name, cache_author)):
            shutil.rmtree(user_cache_dir(cache_name, cache_author), ignore_errors=True)
    log('[bold green]SUCCESS:[/] there is no more messy around here.')


@cli.command('kill-server')
@click.help_option('-h', '--help')
def kill_server() -> None:
    """Emulates the adb kill-server command. All the devices will be disconnected from this adb session."""

    devices = get_by_status('device')
    with console.status('[yellow]Disconnecting[/]', spinner='dots'):
        for item in devices:
            try:
                adb.disconnect(item.serial)
            except adbutils.AdbError:
                continue
    log('[bold red]DISCONNECTED:[/] everything fine, but now you are alone.')


if __name__ == '__main__':
    cli()
