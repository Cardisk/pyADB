# MIM_Orchestrator

## Introduction

This tool is written entirely in python and it represent a wrapper for ADB from platform-tools.
The idea came out when we was playing with an interactive whiteboard and we found out that is based on Android.

**THE USAGE OF THIS TOOL IS NOT INTENDED TO DAMAGE NO ONE AND WE DON'T TAKE ANY RESPONSIBILITY FOR ITS BAD USAGE.**


## Commands

There are various commands that wrap the functionality implemented by ADB itself.

* masscan
* load
* connect
* show
* broad-cmd
* push
* install
* clear
* kill-server


## Masscan

Masscan is a powerful tool that can easily scan a net on a specified port or range of ports.
If any service is found listening on the given parameters it will print it at the end of the execution.
For more details you can go to this repository: [masscan](https://github.com/robertdavidgraham/masscan).

This command wrapper takes two arguments:
* `--net/-n network/subnetmask`
* `--port/-p port/s`

First of all open a terminal.

    $ python3 main.py masscan --net 192.168.1.0/24 --port 80-100,5555

This command will:
* scan the net `192.168.1.0` with a subnet mask of 24 bits `(255.255.255.0)`
* scan the devices on the net on the range of ports `80-100` and on `5555` port
* output the result on a file named `devices.json`


## Load

This command allows you to load into a cache file all the devices situated in `devices.json` that the program found during `masscan`.
If a diffrent file is passed to this command, it will check its existance and then do the same job of the default one.

This command wrapper takes only one optional argument:
* `--file/-f file_name`

In a terminal:

    $ python3 main.py load

This line will:
* check the existance of the file, in this case `devices.json`
* reads from it all the content
* extracts only the information requiered (socket address)
* iterate on a list to check if the sockets are opened on port `5555`, if not it will discard the item
* saves the information on a cache file


## Connect

With this command the program tries to connect to all the devices loaded into the cache file.

It can also take one argument:
* `--socket/-s socket_address`

In a terminal:

    $ python3 main.py connect

This command will:
* read the data present into the cache file
* try to connect to all the devices
* print the result

If the option `--socket/-s socket_address` was present, this command had try to connect only to that.


## Show

The `show` command will display a table of all the connected devices.

In a terminal:

    $ python3 main.py show

The content of the table represent all the device information that can be retrieved with [adbutils](https://github.com/openatx/adbutils) module.


## Broad-cmd

This command name stands for `broadcast-command`. It will execute the given command to all the devices connected.

In a terminal:

    $ python3 main.py broad-cmd
    
This command will:
* wait for a user command throught the input() python function
* iterate on all the devices connected and pass the command to them
* if at least a device returned a result it will ask to the user if he want to see the results
* if the answer is yes (default) it will print a table with the output


## Push

By default `adb` api has the possibility to push files into a remote directory. This command wrapper does just this.

It takes two arguments:
* `--local/-l local_file`
* `--remote/-r remote_absolute_path`

In a terminal:

    $ python3 main.py push -l some_funny_text.txt -r /sdcard/some_funny_text.txt
    
This will:
* check if the remote directory is an absolute path
* check if the remote directory path contains the local file name, if not it will just appends it
* push the file into all the devices


## Install

The `install` command will push and install a `file.apk` into all the connected devices.

The command wrapper require only an argument:
* `--apk/-a path/to/file.apk`

In a terminal:

    $ python3 main.py install path/to/file.apk
    
This will:
* check if there are devices connected
* install the apk file into all the devices

Note: `path/to/file.apk` can also be an `url/to/file.apk` just like [adbutils](https://github.com/openatx/adbutils) documentation says.


## Clear

This command is not a wrapper for any `adb` functionality. It just removes the cache directory and all its content.

In a terminal:

    $ python3 main.py clear
    

## Kill-server

This command wrapper emulates the functionality of `adb kill-server`. Its job is not to kill adb daemon but only to disconnect all the devices.

In a terminal:

    $ python3 main.py kill-server

