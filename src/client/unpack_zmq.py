#!/usr/bin/env python3
import datetime
import numpy as np
from struct import unpack
import pytz

from log.logger import log

DIR_NAME_FORMAT = "{yyyymmdd}"
FILENAME_PREFIX = "das_SR_"  # path for saving files


class ZMQDASPACKET:
    def __init__(self, buffer=None):
        self.numb_of_set: int = None  # number of sets: 1
        self.timestamp: float = None  # timestamp: 1690449193.0428836
        self.spacing: list = None  # spacing: [4.80...01, 2.5, 1.0] [distance, time, ]
        self.origin: list = None  # origin: [0.0, 0.0, 0.0]
        self.index: list = None  # index: [0, 3333, 0, 1599, 0, 0]
        self.unit_size: int | float = None  # unit size: 4
        self.data: np.array = None  # numpy array of float32
        self.unpacked: bool = False  # do we have data?
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
