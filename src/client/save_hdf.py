import datetime
import json
import os
import h5py
import numpy as np

from config import PATH, SPS, DX
from log.logger import log

DIR_NAME_FORMAT = "{yyyymmdd}"
FILENAME_PREFIX = "das_SR_"  # path for saving files


def save_data(packet):
    """Save data into a file
    see ZMQDASPACKET for details on the packet attributes.
    """
    # set output path and file
    # TODO packet_time to file name
    # Define downsampling time factor
    if SPS:
        time_down_factor = round(packet.sps / SPS)  # factor for desired sampling rate
        if (
            time_down_factor == 0 or packet.tpoints % time_down_factor != 0
        ):  # make sure we can downsample by decimation without interpolation
            time_down_factor = 1
    else:
        time_down_factor = 1
    # Define downsampling space step
    if DX:
        data_step = round(DX / packet.dx)  # factor for desired sampling space
    else:
        data_step = 1
    # resample data in time
    if SPS == 0:  # no downsampling
        data = packet.data
    elif time_down_factor == 1:  # Reshape, no downsample
        data = np.reshape(packet.data, (-1, packet.index[1] + 1))
    else:  # downsample in time axis-0
        data = packet.data.reshape(-1, time_down_factor, packet.spoints).mean(axis=1)
    # resample in space
    data = data[:, ::data_step]  # space decimation

    packet_time = datetime.datetime.fromtimestamp(packet.timestamp, datetime.UTC)
    yyyymmdd = packet_time.strftime("%Y%m%d")
    save_dir = f"{DIR_NAME_FORMAT.format(yyyymmdd=yyyymmdd)}"
    file_name = f"{FILENAME_PREFIX}{packet.timestamp:.5f}.h5"

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


def path_check(outputdir):
    """Make sure output path is available"""
    if not os.path.exists(outputdir):
        try:
            os.makedirs(outputdir)
        except Exception as err:
            print(f"Cannot create folder {outputdir}: {err}")
            raise RuntimeError("Output path issues") from err
    return True
