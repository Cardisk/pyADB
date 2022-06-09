# MIM_Orchestrator

## Introduction

This tool is written entirely in python and it represent a wrapper for ADB from platform-tools.
The idea came out when we was playing with an interactive whiteboard and we found that is based on Android.
The usage of this tool is not intended to damage no one and we don't take any responsibility for its bad usage.

## Commands

There are various commands that wrap the functionality implemented by ADB itself.

- masscan
- load
- connect
- show
- broad-cmd
- push
- cache-cls
- kill-server

---
### MASSCAN

Masscan is a powerful tool that can easily scan a net on a specified port or range of ports.
If any service is found listening on the given parameters it will print it at the end of the execution.

This command wrapper takes two arguments:
- --net/-n
- --port/-p

First of all open a terminal.
Then you can start your research by only typing this and changing the arguments.

`python3 main.py masscan --net 192.168.1.0/24 --port 5555`

