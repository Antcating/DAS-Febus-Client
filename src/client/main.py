import array
import datetime
import json
from struct import unpack
import numpy as np
import pytz
import zmq
import os
import h5py
from config import IP, PORT, SPS, DX, PATH
from log.main_logger import logger as log

DIR_NAME_FORMAT = "{yyyymmdd}"
FILENAME_PREFIX = "das_SR_"  # path for saving files

class ZMQClient:
    """
    A class to create a ZMQ client and send message to the server.

    ...

    Attributes
    ----------
    context : zmq.Context
        ZMQ context object.
    client : zmq.Socket
        ZMQ socket object.
    last_timestamp : float
        Timestamp of the last message sent to the server.
    attempts : int
        Number of attempts to connect to the server.

    Methods
    -------
    create_socket():
        Create a ZMQ socket.
    send_message():
        Send message to the server.
    run():
        Continuously send message to the server.
    """

    def __init__(self):
        """
        Constructs all the necessary attributes for the ZMQClient object.
        """
        self.context = zmq.Context()
        self.client = None

        self.last_timestamp = 0
        self.attempts = 3

        self.create_socket()

    def create_socket(self):
        """
        Create a ZMQ socket.
        """
        self.client = self.context.socket(zmq.REQ)
        self.client.setsockopt(zmq.IMMEDIATE, 1)
        self.client.setsockopt(zmq.LINGER, 0)
        self.client.setsockopt(zmq.RCVTIMEO, 3000)
        self.client.setsockopt(zmq.SNDTIMEO, 3000)
        self.client.connect(f"tcp://{IP}:{PORT}")

    def send_message(self):
        """
        Send message to the server.
        """
        log.info(f"Sending message to server, {self.last_timestamp}")
        try:
            self.client.send(array.array("d", [self.last_timestamp]))
            response = self.client.recv_multipart()
            print("Message received from server")
            packet = ZMQDASPACKET(response)
            if self.last_timestamp != packet.timestamp:
                packet.save_data()
                self.last_timestamp = packet.timestamp
            self.attempts = 3
        except zmq.error.Again as e:
            log.error(f"Timeout: {e}")
            self.client.close()
            self.attempts -= 1
            if self.attempts == 0:
                log.error("Server is not responding, resetting connection")
                self.last_timestamp = 0
                self.context.term()
                self.context = zmq.Context()
                self.attempts = 3
            self.create_socket()
        except Exception as e:
            log.exception(f"Error: {e}")
        except KeyboardInterrupt:
            log.info("Exiting")
            exit(0)

    def run(self):
        """
        Continuously send message to the server.
        """
        while True:
            self.send_message()

    def __del__(self):
        """
        Close the ZMQ connection.
        """
        log.info("Closing connection")
        self.client.close()
        self.context.term()


class ZMQDASPACKET:
    """
    A class to unpack data received from the ZMQ server and save it to a file.

    ...

    Attributes
    ----------
    numb_of_set : int
        Number of sets.
    timestamp : float
        Timestamp of the data.
    spacing : list
        Spacing of the data.
    origin : list
        Origin of the data.
    index : list
        Index of the data.
    unit_size : int | float
        Unit size of the data.
    data : np.array
        Numpy array of float32.
    unpacked : bool
        Whether the data is unpacked or not.

    Methods
    -------
    unpack(buffer):
        Unpack data received from the ZMQ server.
    save_data():
        Save data into a file.
    """

    def __init__(self, buffer=None):
        """
        Constructs all the necessary attributes for the ZMQDASPACKET object.

        Parameters
        ----------
        buffer : list, optional
            List of data received from the ZMQ server (default is None).
        """
        self.numb_of_set: int = None
        self.timestamp: float = None
        self.spacing: list = None
        self.origin: list = None
        self.index: list = None
        self.unit_size: int | float = None
        self.data: np.array = None
        self.unpacked: bool = False
        if buffer is not None:
            self.unpack(buffer)

    def unpack(self, buffer):
        """
        Unpack data received from the ZMQ server.

        Parameters
        ----------
        buffer : list
            List of data received from the ZMQ server.
        """
        self.numb_of_set, self.timestamp = unpack(
            "=id", buffer[0]
        )
        time_stamp = datetime.datetime.fromtimestamp(
            self.timestamp, tz=pytz.UTC
        )
        attributes = unpack(
            "ddddddiiiiiii", buffer[1]
        )
        self.spacing = list(attributes[:3])
        self.origin = list(attributes[3:6])
        self.index = list(attributes[6:12])
        self.unit_size = attributes[12]
        self.unpacked = True
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

    def save_data(self):
        """
        Save data into a file.
        """
        if SPS:
            time_down_factor = round(
                self.sps / SPS
            )
            if (
                time_down_factor == 0 or self.tpoints % time_down_factor != 0
            ):
                time_down_factor = 1
        else:
            time_down_factor = 1
        if DX:
            data_step = round(
                DX / self.dx
            )
        else:
            data_step = 1
        if SPS == 0:
            data = self.data
        elif time_down_factor == 1:
            data = np.reshape(self.data, (-1, self.index[1] + 1))
        else:
            data = self.data.reshape(-1, time_down_factor, self.spoints).mean(axis=1)
        data = data[:, ::data_step]

        packet_time = datetime.datetime.fromtimestamp(
            self.timestamp, datetime.UTC
        )
        yyyymmdd = packet_time.strftime("%Y%m%d")
        save_dir = f"{DIR_NAME_FORMAT.format(yyyymmdd=yyyymmdd)}"
        file_name = f"{FILENAME_PREFIX}{self.timestamp:.5f}.h5"

        path_check(os.path.join(PATH, save_dir))

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
                f"Saving {len(self.data)} data points @ {save_dir}{os.sep}{file_name}"
            )
        else:
            log.warning(f"Cannot save data for packet {self.timestamp}")

        if not os.path.isfile(os.path.join(PATH, save_dir, "attrs.txt")):
            with open(
                os.path.join(PATH, save_dir, "attrs.json"), "w", encoding="UTF-8"
            ) as attrs_file:
                attrs_file.write(
                    json.dumps(
                        {
                            "spacing": self.spacing,
                            "origin": self.origin,
                            "index": self.index,
                            "packet_time": self.timestamp,
                            "down_factor_time": time_down_factor,
                            "down_factor_space": data_step,
                            "unit_size": self.unit_size,
                        }
                    )
                )

    @property
    def spoints(self):
        """
        Number of spatial points.
        """
        if self.unpacked:
            return self.index[1] + 1
        else:
            return None

    @property
    def tpoints(self):
        """
        Number of time samples.
        """
        if self.unpacked:
            return self.index[3] + 1
        else:
            return None

    @property
    def dx(self):
        """
        Spatial spacing in meters.
        """
        if self.unpacked:
            return self.spacing[0]
        else:
            return None

    @property
    def dt(self):
        """
        Temporal spacing in seconds.
        """
        if self.unpacked:
            return self.spacing[1] / 1000.0
        else:
            return None

    @property
    def sps(self):
        """
        Samples per seconds.
        """
        if self.unpacked:
            return int(1 / self.dt)
        else:
            return None


def path_check(outputdir):
    """
    Make sure output path is available.

    Parameters
    ----------
    outputdir : str
        Output directory path.

    Returns
    -------
    bool
        True if the output path is available, False otherwise.
    """
    if not os.path.exists(outputdir):
        try:
            os.makedirs(outputdir)
        except Exception as err:
            print(f"Cannot create folder {outputdir}: {err}")
            raise RuntimeError("Output path issues") from err
    return True