#!/usr/bin/env python3
import os
import sys
import array
import h5py
import datetime
import numpy as np
from struct import unpack
import signal
import zmq
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
import json
import pytz

from config import PATH, SPS, DX, IP, PORT

_LOG_LEVEL_STRINGS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
formatter = logging.Formatter(
    fmt="%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# DEFAULT PARAMETERS

VERBOSE = False
LOG_FILE = None
LOG_LEVEL = "CRITICAL"
log = logging.getLogger("DASCLIENT")
log.setLevel(LOG_LEVEL)  # set at default log level

DIR_NAME_FORMAT = "{yyyymmdd}"
FILENAME_PREFIX = "das_SR_"  # path for saving files

parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="""Client for DAS ZMQ server""",
    epilog="""Created by Ran Novitsky Nof (ran.nof@gmail.com), 2023 @ GSI""",
)
parser.add_argument("-H", "--host", help=f"ZMQ server IP (Default: {IP})", default=IP)
parser.add_argument(
    "-P", "--port", help=f"ZMQ server port (Default: {PORT})", default=PORT
)
parser.add_argument(
    "-v",
    help="verbose - print messages to screen?",
    action="store_true",
    default=VERBOSE,
)
parser.add_argument(
    "-l",
    "--log_level",
    choices=_LOG_LEVEL_STRINGS,
    default=LOG_LEVEL,
    help="Log level (Default: {LOG_LEVEL})".format(LOG_LEVEL=LOG_LEVEL),
)
parser.add_argument(
    "--logfile", metavar="log file name", help="log to file", default=LOG_FILE
)
parser.add_argument(
    "-p",
    "--prefix",
    metavar="file_prefix",
    help=f"Prefix for the output dir(s) (Default: {DIR_NAME_FORMAT}).",
    type=str,
    default=DIR_NAME_FORMAT,
)
parser.add_argument(
    "-t",
    "--time_sps",
    default=SPS,
    help=f"Output sampling rate (Hz). 0 for no time resampling (default {SPS}).",
)
parser.add_argument(
    "-d",
    "--distance_step",
    default=DX,
    help=f"Output sample distance (m). 0 for no resampling (default {DX}).",
)


class ZMQDASPACKET:
    def __init__(self, buffer=None):
        self.numb_of_set = None  # number of sets: 1
        self.timestamp = None  # timestamp: 1690449193.0428836
        self.spacing = None  # spacing: [4.800000000000001, 2.5, 1.0] [distance, time, ]
        self.origin = None  # origin: [0.0, 0.0, 0.0]
        self.index = None  # index: [0, 3333, 0, 1599, 0, 0]
        self.unit_size = None  # unit size: 4
        self.data = None  # numpy array of float32
        self.unpacked = False  # do we have data?
        if buffer is not None:
            self.unpack(buffer)

    def unpack(self, buffer):
        """Unpack data received from the ZMQ server"""
        self.numb_of_set, self.timestamp = unpack(
            "=id", buffer[0]
        )  # row number? and timestamp
        time_stamp = datetime.datetime.fromtimestamp(
            self.timestamp, tz=pytz.UTC
        )  # convert timestamp to datetime
        attributes = unpack(
            "ddddddiiiiiii", buffer[1]
        )  # unpack the attributes values following the example code
        self.spacing = list(attributes[:3])
        self.origin = list(attributes[3:6])
        self.index = list(attributes[6:12])
        self.unit_size = attributes[12]
        self.unpacked = True  # we have data!
        try:
            self.data = np.frombuffer(buffer[2], dtype=np.float32).reshape(
                self.tpoints, -1
            )
        except ValueError as err:
            log.exception(
                f"Data matrix and shape info mismatched {self.timestamp} {err}"
            )
            self.unpacked = False
        log.debug(
            f"\
Received {np.multiply(*self.data.shape)} data points @ {time_stamp} ({self.timestamp})"
        )

    @property
    def spoints(self):
        """Number of spatial points"""
        if self.unpacked:
            return self.index[1] + 1
        else:
            return None

    @property
    def tpoints(self):
        """Number of time samples"""
        if self.unpacked:
            return self.index[3] + 1
        else:
            return None

    @property
    def dx(self):
        """Spatial spacing in meters"""
        if self.unpacked:
            return self.spacing[0]
        else:
            return None

    @property
    def dt(self):
        """Temporal spacing in seconds"""
        if self.unpacked:
            return self.spacing[1] / 1000.0
        else:
            return None

    @property
    def sps(self):
        """Samples per seconds"""
        if self.unpacked:
            return int(1 / self.dt)
        else:
            return None


class DASREADER:
    def __init__(
        self, ip=IP, port=PORT, save_dir_format=DIR_NAME_FORMAT, sps=SPS, dx=DX
    ):
        self.ip = ip
        self.port = port
        self.zmqurl = f"tcp://{ip}:{port}"
        self.output_prefix = save_dir_format
        self.sps = sps
        self.dx = dx
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.connected = False
        self.last_timestamp = 0
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def connect(self):
        """Conenct to ZMQ server."""
        try:
            self.socket.connect(self.zmqurl)
            self.connected = True
        except zmq.ZMQError as err:
            log.exception(f"Error connecting to ZMQ server on {self.zmqurl}: {err}")
            return False
        except Exception as err:
            log.exception(f"Unknown Error: {err}")
            return False
        log.info("Connected to ZMQ server")
        return True

    def disconnect(self):
        if self.connected:
            try:
                self.connected = False
                self.socket.close()
                self.context.term()
            except Exception as err:
                log.exception(f"Unknown Error: {err}")
                return False
            log.info("Disconnected from ZMQ server")
        return True

    def stop(self, signum, frame):
        log.critical(f"Got Term signal: {signum}")
        self.disconnect()

    def get_data(self):
        while self.connected:
            reply = None
            try:
                request = array.array(
                    "d", [self.last_timestamp]
                )  # prepare a request. should be time.time()?
                self.socket.send(request)  # Send the request to the zmq.REP server
                reply = (
                    self.socket.recv_multipart()
                )  # get the reply. In the example it is multipart
                # reply in example is 3 parts.
                # part 1 is enumerator and timestamp,
                # part 2 is parameters,
                # part 3 is data
            except zmq.ZMQError as err:
                if self.connected:
                    log.exception(f"Error with ZMQ: {err}")
                    self.disconnect()
            if reply is not None:
                packet = ZMQDASPACKET()
                try:
                    packet.unpack(reply)
                except Exception as err:
                    log.warning(f"Error unpacking data: {err}. Skipped")
                # make sure it's a new data.
                # Current implementation is not very efficient
                if packet.unpacked and packet.timestamp != self.last_timestamp:
                    # try:
                    self.save_data(packet)
                    self.last_timestamp = packet.timestamp
                    self.last_packet = packet
                    # except Exception as err:
                    #    if self.connected:
                    #        log.warning(f'Error saving data: {err}')
                    #        self.disconnect()

    def path_check(self, outputdir):
        """Make sure output path is available"""
        if not os.path.exists(outputdir):
            try:
                os.makedirs(outputdir)
            except Exception as err:
                log.exception(f"Cannot create folder {outputdir}: {err}")
                raise RuntimeError("Output path issues") from err
        return True

    def save_data(self, packet: ZMQDASPACKET):
        """Save data into a file
        see ZMQDASPACKET for details on the packet attributes.
        """
        # set output path and file
        # TODO packet_time to file name
        # Define downsampling time factor
        if self.sps:
            time_down_factor = round(
                packet.sps / self.sps
            )  # factor for desired sampling rate
            if (
                time_down_factor == 0 or packet.tpoints % time_down_factor != 0
            ):  # make sure we can downsample by decimation without interpolation
                time_down_factor = 1
        else:
            time_down_factor = 1
        # Define downsampling space step
        if self.dx:
            data_step = round(self.dx / packet.dx)  # factor for desired sampling space
        else:
            data_step = 1
        # resample data in time
        if self.sps == 0:  # no downsampling
            data = packet.data
        elif time_down_factor == 1:  # Reshape, no downsample
            data = np.reshape(packet.data, (-1, packet.index[1] + 1))
        else:  # downsample in time axis-0
            data = packet.data.reshape(-1, time_down_factor, packet.spoints).mean(
                axis=1
            )
        # resample in space
        data = data[:, ::data_step]  # space decimation

        packet_time = datetime.datetime.fromtimestamp(packet.timestamp, datetime.UTC)
        yyyymmdd = packet_time.strftime("%Y%m%d")
        save_dir = f"{self.output_prefix.format(yyyymmdd=yyyymmdd)}"
        file_name = f"{FILENAME_PREFIX}{packet.timestamp:.5f}.h5"

        self.path_check(os.path.join(PATH, save_dir))

        try:
            f = h5py.File(os.path.join(PATH, save_dir, file_name), "x")
        except FileExistsError as err:
            log.exception(f"File Exists {save_dir}{os.sep}{file_name}: {err}")
        except Exception as err:
            log.exception(f"Cannot save file {save_dir}{os.sep}{file_name}: {err}")
        if f is not None:
            f.create_dataset("data_down", data=data)
            f.close()
            log.debug(
                f"Saving {len(packet.data)} data points @ {save_dir}{os.sep}{file_name}"
            )
        else:
            log.warning(f"Cannot save data for packet {packet.timestamp}")

        if not os.path.isfile(os.path.join(PATH, save_dir, "attrs.txt")):
            with open(
                os.path.join(PATH, save_dir, "attrs.json"), "w", encoding="UTF-8"
            ) as attrs_file:
                attrs_file.write(
                    json.dumps(
                        {
                            "spacing": packet.spacing,
                            "origin": packet.origin,
                            "index": packet.index,
                            "packet_time": packet.timestamp,
                            "down_factor_time": time_down_factor,
                            "down_factor_space": data_step,
                            "unit_size": packet.unit_size,
                        }
                    )
                )


def set_logger(log, verbose=VERBOSE, log_level=LOG_LEVEL, logfile=LOG_FILE):
    log.setLevel(log_level)
    if verbose:
        # create console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        ch.setFormatter(formatter)
        if logging.StreamHandler not in [h.__class__ for h in log.handlers]:
            log.addHandler(ch)
        else:
            log.warning("log Stream handler already applied.")
    if logfile:
        # create file handler
        fh = TimedRotatingFileHandler(logfile, when="midnight", utc=True)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        if TimedRotatingFileHandler not in [h.__class__ for h in log.handlers]:
            log.addHandler(fh)
        else:
            log.warning("Log file handler already applied.")
        log.info(f"Log file is: {logfile}")
    else:
        log.debug("No Log file was set")


def das_client_entry():
    args = parser.parse_args()
    set_logger(log, args.v, args.log_level, args.logfile)
    log.info(f"ZMQ: {args.host}:{args.port}")
    log.info(f"Prefix for file(s): {args.prefix}")
    client = DASREADER(args.host, args.port, args.prefix)
    if client.connect():
        client.get_data()  # should run endlessly
    client.disconnect()


if __name__ == "__main__":
    das_client_entry()
