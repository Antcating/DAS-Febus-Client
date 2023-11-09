# DAS Client

## Table of Contents

- [DAS Client](#das-client)
  - [Table of Contents](#table-of-contents)
  - [Abou ](#abou-)
  - [Getting Started ](#getting-started-)
    - [Prerequisites](#prerequisites)
    - [Installing](#installing)
    - [Configuration](#configuration)
      - [Specific configuration](#specific-configuration)
  - [Usage ](#usage-)
    - [Manual use](#manual-use)
      - [Using Python](#using-python)
      - [Using bash](#using-bash)
    - [Keep-alive](#keep-alive)
      - [Configure systemd service](#configure-systemd-service)
      - [Activating service](#activating-service)


## Abou <a name = "about"></a>

DAS client requests ZMQ packets from FEBUS system and saves them as `.h5` files.

## Getting Started <a name = "getting_started"></a>

To set up DAS client, you have to ensure that you have fresh Python installation (>=3.10).

### Prerequisites

This project has keep-alive script, which could help ensure stability over time. Keep-alive implemented using `bash` and `systemd-service`, so it is **UNIX-systems with systemd only**.

### Installing

A step by step series of guide that tell you how to get DAS client running.

**Make sure, that you completed all installation steps described in [README](../README.md).**

Create virtual environment for DAS client:

```
python -m venv .venv_client
```

Activate virtual environment (bash):
```
source .venv_client/bin/activate
```

Install required modules
```
pip install -r requirements_client.txt
```

### Configuration 

#### Specific configuration

Specifically for DAS client `config.ini` contains several parameters: `IP`, `PORT` of the DAS server (which will send packet to client).
If you are using client locally, you can set up local client as in example:

> Example:
```
IP=127.0.0.1
PORT=16667
```

Ensure that you provided properly updated `config.ini` and you ready to go.

## Usage <a name = "usage"></a>

Script will save files locally to `LOCALPATH` directory (provided in `config.ini`) in subdirectories named in `YYYYMMDD` format. For `LOCALPATH` directory script will require read and write (600) permissions.

### Manual use

#### Using Python 

If you want to run project once, you can do this using Python directly:

*Ensure you activated virtual environment*

```
source .venv_client/bin/activate
```
Run DAS client
```
python src/das_client.py
```

#### Using bash 

Project provide `bash` wrapper around Python project, which sets up PATH, virtual environment by itself.  

To use `bash` script, you will have to setup it: 
In the `client.sh` in root directory of the project change `PROJECT_PATH` to **absolute PATH of root directory of this project**.

> Example:
```
# Changing directory to main project directory
pushd /home/earthquake_lover/Projects/DAS-FEBUS-RECEIVER
```

Change `client.sh` permissions to include execute permission (700):
```
> chmod 700 client.sh
``` 

Run the project
```
> bash client.sh
```

### Keep-alive

You can setup keep-alive using cron or any other scheduling software. This repository provide plug-and-play `systemd` service.

If you want to use `systemd-service` Ensure that your system uses systemd:
```
Input:
> systemd --version

Output: 
< systemd 252 (252.17-1~deb12u1)
```

If your system uses you can proceed with scheduling:

**Make sure to complete [Using Bash](#using-bash)**. We will use `client.sh` in your scheduling script.

In the `systemd` directory you can find every `FebusDASClient.service` service

#### Configure systemd service

You have to edit `FebusDASClient.service` by changing `PROJECT_PATH` to create **absolute PATH to `client.sh`** (by default it would be the same PATH you provided in `client.sh`).

> Example:
```
[Service]
ExecStart=/bin/bash /home/earthquake_lover/Projects/DAS-FEBUS-RECEIVER/client.sh
```

#### Activating service

Now you can proceed with providing `systemd` with new service:

Copy service to `/etc/systemd/system` directory:
```
sudo cp systemd/FebusDASClient.service /etc/systemd/system
```

Activate timer using `systemctl`:
```
sudo systemctl enable FebusDASClient.service
sudo systemctl daemon-reload
sudo systemctl start FebusDASClient.service
```

Hooray! Service is set up and will automatically restart DAS client if it fails or locks up. 