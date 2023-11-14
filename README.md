# DAS Client

## Table of Contents

- [DAS Client](#das-client)
  - [Table of Contents](#table-of-contents)
  - [About ](#about-)
  - [Getting Started ](#getting-started-)
    - [Installing](#installing)
    - [Configuration](#configuration)
  - [Usage ](#usage-)
    - [Manual use](#manual-use)
      - [Using Python](#using-python)
      - [Using bash](#using-bash)
    - [Keep-alive](#keep-alive)
      - [Configure systemd service](#configure-systemd-service)
      - [Activating service](#activating-service)


## About <a name = "about"></a>

This section provides a brief overview of the DAS client, which requests ZMQ packets from FEBUS system and saves them as `.h5` files.

## Getting Started <a name = "getting_started"></a>

This section provides instructions on how to set up the DAS client. It is important to note that a fresh Python installation (>=3.10) is required to run this project. Additionally, this project ships with optional keep-alive script that helps ensure stability over time. The keep-alive script is implemented using `bash` and `systemd-service`, so it is only compatible with UNIX-systems with systemd.

### Installing

A step by step series of guide that tell you how to get DAS client running.

Clone this project

```
git clone https://github.com/Antcating/DAS-Febus-Client.git
cd DAS-Febus-Client
```

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

All configuration is done through `config.ini` file located at the root of the project. 

**LOCALPATH**

- `LOCALPATH` is **absolute** PATH to the LOCAL directory where DAS Client will store hdf5 files. 

> Example:
> ```
> LOCALPATH=/home/earthquake_lover/DAS_DATA
> ```
DAS client will write packets to `LOCALPATH/YYYYMMDD`.

**SPS and DX**

- `SPS` is expected time frequency after data downsampling (in Hz). By default 100. 

- `DX` is expected spatial spacing after data downsampling (in m). By default 9.6 

**IP and PORT**

Used for connection to ZMQ server for receiving packets.
If you are using client locally, you can set up local client as in example:

> Example:
> ```
> IP=127.0.0.1
> PORT=16667
> ```

**LOG**

Used for configuring internal logger. Logger file is located in `LOCALPATH/log`.

- `LOG_LEVEL` variable defines the log level of the file logger, and is set to `INFO` by default.

- `CONSOLE_LOG` is a boolean (True/False) that defines whether console output should be logged. It is set to True by default.

- `CONSOLE_LOG_LEVEL` defines the log level of the console logger. If not provided, it defaults to `INFO`.

**Telegram**

Enables exception logging to Telegram using TelegramBotAPI

- `USE_TELEGRAM` a boolean (True/False) that enables or disables Telegram logging.

- `token` a string that represents the token provided by Telegram to operate the bot.

- `channel` a string that represents the Telegram channel where notifications will be sent.

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
python src/client.py
```

#### Using bash 

Project provide `bash` wrapper around Python project, which sets up PATH, virtual environment by itself.  

To use `bash` script, you will have to setup it: 
In the `client.sh` in root directory of the project change `PROJECT_PATH` to **absolute PATH of root directory of this project**.

> Example:
```
# Changing directory to main project directory
pushd /home/earthquake_lover/Projects/DAS-Febus-Client
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