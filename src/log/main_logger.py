import logging
import os
from config import PATH, config_dict

# Create logger object
if config_dict["LOG"]["LOG_LEVEL"]:
    LOG_LEVEL = config_dict["LOG"]["LOG_LEVEL"]
else:
    LOG_LEVEL = "INFO"

logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

# Create file handler
file_handler = logging.FileHandler(os.path.join(PATH, "log"))
file_handler.setLevel(logging.DEBUG)

# Create stream handler if CONSOLE_LOG is True
CONSOLE_LOG = config_dict["LOG"]["CONSOLE_LOG"]
if CONSOLE_LOG == "True":
    if config_dict["LOG"]["CONSOLE_LOG_LEVEL"]:
        CONSOLE_LOG_LEVEL = config_dict["LOG"]["CONSOLE_LOG_LEVEL"]
    else:
        CONSOLE_LOG_LEVEL = "INFO"
    
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(CONSOLE_LOG_LEVEL)
else:
    stream_handler = None

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s.%(msecs)03d | %(name)s | %(levelname)s | %(message)s',
                              datefmt="%Y-%m-%dT%H:%M:%S")

# Set formats and add the handlers to the logger
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

if stream_handler:
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

