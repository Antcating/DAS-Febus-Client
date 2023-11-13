from client.main import main
from log.telegram import send_telegram_error

try:
    main()
except Exception as err:
    send_telegram_error("Unexpected error in client: \n\n" + str(err))
