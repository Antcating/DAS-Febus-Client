from client.main import ZMQClient
from log.main_logger import logger as log

try:
    ZMQClient().run()
except Exception as err:
    log.exception(f"Unexpected error in client: {err}")
