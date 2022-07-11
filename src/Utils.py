import os
import sys
import subprocess
from rich.align import Align
from rich.panel import Panel
from textual.widget import Widget
from textual.app import App
from textual.reactive import Reactive
from textual.events import *
import pickle
from rich.console import RenderableType, Console
from rich.progress import Column, Text, StyleType, Task, JustifyMethod, ProgressColumn
from typing import Optional, Set, Any
from appdirs import *
from adbutils import adb
from rich.table import Table

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
        console.print(f'[red]CACHE[/]: {name}.pkl does not exist.')
        sys.exit()

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


class Device(Widget):
    """Widget that displays a device"""

    title = Reactive('')
    mouse_over = Reactive(False)

    def __init__(self, title: str, hover_color: str, text_color: str):
        super(Device, self).__init__('')
        self.title = title
        self.hover_color = hover_color
        self.text_color = text_color

    def on_enter(self) -> None:
        self.mouse_over = True

    def on_leave(self) -> None:
        self.mouse_over = False

    def on_click(self, event: Click) -> None:
        if '5555' in self.title:
            subprocess.run(['scrcpy', f'--tcpip={self.title}'], capture_output=True)
        else:
            pass

    def render(self) -> RenderableType:
        obj = Align.center(Text(self.title), style=self.text_color, vertical='middle')
        return Panel(obj, style=(self.hover_color if self.mouse_over else ''))


class Display(App):
    """App run when scrcpy command is launched"""

    async def on_load(self) -> None:
        await self.bind('q', 'quit')

    async def on_mount(self) -> None:
        connected = get_by_status('device')
        if len(connected) > 0:
            devices = (Device(item.serial, hover_color='on red', text_color='bold green') for item in connected)
            await self.view.dock(*devices, edge='top')
        else:
            await self.view.dock(
                Device('No devices connected. Press \'Q\' to exit.', hover_color='', text_color='bold red'),
                edge='top'
            )


def error(string: str) -> None:
    """Error printing"""

    console.print(string)
    sys.exit(1)


def log(string: Any, end: str = '\n') -> None:
    """Log printing"""

    console.print(string, end=end)
