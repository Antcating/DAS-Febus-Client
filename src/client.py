from client.main import main
from log.telegram import send_telegram_error
from log.main_logger import logger as log

try:
    main()
except Exception as err:
    log.exception(f"Unexpected error in client: {err}")
    send_telegram_error("Unexpected error in client: \n\n" + str(err))
