# MIM_Orchestrator

## Introduction

This tool is written entirely in python, and it represents a wrapper for ADB from platform-tools.
The idea came out when we were playing with an interactive whiteboard, so we found out that is based on Android.

**THE USAGE OF THIS TOOL IS NOT INTENDED TO DAMAGE NO ONE AND WE DON'T TAKE ANY RESPONSIBILITY FOR ITS BAD USAGE.**


## Commands

There are various commands that wrap the functionality implemented by ADB itself.

* [masscan](#masscan)
* [load](#load)
* [connect](#connect)
* [show](#show)
* [broad-cmd](#broad-cmd)
* [exec](#exec)
* [push](#push)
* [pull](#pull)
* [install](#install)
* [scrcpy](#scrcpy)
* [clear](#clear)
* [kill-server](#kill-server)

For all the commands is present a help page accessible by typing:

    $ python3 main.py <command> --help/-h

## Masscan

Masscan is a powerful tool that can easily scan a net on a specified port or range of ports.
If any service is found listening on the given parameters it will print it at the end of the execution.
For more details you can go to this repository: [masscan](https://github.com/robertdavidgraham/masscan).

This command wrapper takes a max of three parameters:
* first: `network/mask`
* second: `port or range`
* third (optional): `--ipv6`

If `--ipv6` flag is set, you can use an ipv6 network/mask address.

Usage:

    $ python3 main.py masscan 192.168.1.0/24 80-100,5555

This command will:
* scan the net `192.168.1.0` with a subnet mask of 24 bits `(255.255.255.0)`
* scan the devices on the net on the range of ports `80-100` and on `5555`
* output the result on a file named `devices.json`

[Back](#commands)


## Load

This command allows you to load into a cache file all the devices situated in `devices.json` that the program found during `masscan`.
If a different file is passed to this command, it will check its existence and then do the same job of the default one.

This command wrapper takes only one optional argument:
* `--file/-f file_name`

Usage:

    $ python3 main.py load

This line will:
* check the existence of the file, in this case `devices.json`
* reads from it all the content
* extracts only the information required (socket address)
* iterate on a list to check if the sockets are opened on port `5555`, if not it will discard the item
* saves the information on a cache file

[Back](#commands)


## Connect

With this command the program tries to connect to all the devices loaded into the cache file.

It can also take one argument:
* `--socket/-s socket_address`

Usage:

    $ python3 main.py connect

This command will:
* read the data present into the cache file
* try to connect to all the devices
* print the result

If the option `--socket/-s socket_address` was present, this command had tried to connect only to that.

[Back](#commands)


## Show

This command will display a table of all the connected devices.

Usage:

    $ python3 main.py show

The content of the table represent all the device information that can be retrieved with [adbutils](https://github.com/openatx/adbutils) module.

[Back](#commands)


## Broad-cmd

This command name stands for `broadcast-command`. It will execute the given command to all the devices connected.

Usage:

    $ python3 main.py broad-cmd <command>
    
This command will:
* iterate on all the devices connected and pass the command to them
* if at least a device returned a result it will ask the user if he wants to see the results
* if the answer is yes (default) it will print a table with the output

[Back](#commands)


## Exec

This will execute the given command to the given remote device.

This wrapper takes two arguments:
* first: **socket_address**
* second: **command**

Usage:

    $ python3 main.py exec 192.168.1.10:5555 <command>

This will:
* check if the remote host is connected
* executes the command to the given host
* if an output is returned it will print it out

[Back](#commands)


## Push

By default, adb api has the possibility to push files into a remote directory. This command wrapper does just this.

This command wrapper takes a max of three parameters:
* first: `local_file`
* second: `remote/absolute/path`
* third: `--socket/-s socket_address`

If the third option is specified, the local_file will be pushed only to that.

Usage:

    $ python3 main.py push some_funny_text.txt /sdcard
    
This will:
* check if the remote directory is an absolute path
* check if the remote directory path string contains the local file name, if not it will just append it
* push the file into all the devices

[Back](#commands)


## Pull

By default, adb api has also the possibility to pull files from a remote directory. This command wrapper does just this.

This command wrapper takes three parameters:
* first: `host:port`
* second: `remote/absolute/path/to/file`
* third: `local_file_name`

Usage:
    
    $ python3 main.py pull 192.168.1.10:5555 /sdcard/remote.txt local.txt
    
This command will:
* check if the remote host is connected
* check if the remote path is absolute
* pull the remote file into the local machine

[Back](#commands)


## Install

This command will push and install an apk into all the connected devices.

The command wrapper require only an argument:
* `path/to/file.apk`

Usage:

    $ python3 main.py install path/to/file.apk
    
This will:
* check if there are devices connected
* install the apk file into all the devices

Note: `path/to/file.apk` can also be an `url/to/file.apk` just like [adbutils](https://github.com/openatx/adbutils) documentation says.

[Back](#commands)


## Scrcpy

Scrcpy is a powerful tool that allow you to copy the source of a screen from a remote device.
You can find more information about it, [here](https://github.com/Genymobile/scrcpy).

This command launches a [textual](https://github.com/Textualize/textual) app that displays all the devices connected.
Clicking on a device, automatically, scrcpy starts sourcing the screen device.

This command can take a parameter:
* `--socket/-s socket_address`

Usage:

    $ python3 main.py scrcpy

This line will:
* check if a specific socket address has been passed
* run the textual app
* if a device is clicked launches the respective scrcpy
* wait for 'Q' to be pressed to stop the execution of the command

If a specific socket is provided, it will only display the corresponding scrcpy.

[Back](#commands)


## Clear

This command is not a wrapper for any adb functionality. It just removes the cache directory and all its content.

Usage:

    $ python3 main.py clear

[Back](#commands)


## Kill-server

This command wrapper emulates the functionality of `adb kill-server`. Its job is not to kill adb's daemon but only to disconnect all the devices.

Usage:

    $ python3 main.py kill-server

[Back](#commands)
