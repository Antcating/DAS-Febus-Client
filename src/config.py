import configparser
from os.path import isdir

config_dict = configparser.ConfigParser()
config_dict.read("config.ini", encoding="UTF-8")

# PACKET CHARACTERISTICS
SPS = int(config_dict["CONSTANTS"]["SPS"])
DX = float(config_dict["CONSTANTS"]["DX"])

#
# CLIENT CHARACTERISTICS
#
IP = config_dict["CLIENT"]["IP"]
PORT = config_dict["CLIENT"]["PORT"]

# PATHs to files and save
LOCALPATH = config_dict["PATH"]["LOCALPATH"]

if isdir(LOCALPATH):
    PATH = LOCALPATH
else:
    raise Exception("PATH is not accessible!")