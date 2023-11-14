import requests
import telebot
from config import config_dict

def get_bot():
    """Creates Telegram bot to be used

    Returns:
        telebot.bot: Returns created Telegram bot instance
    """
    if config_dict["Telegram"]["token"]:
        token = config_dict["Telegram"]["token"]
        bot = telebot.TeleBot(token=token, parse_mode="None")
    else:
        bot = None
        print("Bot token is not provided")
    return bot


def get_channel():
    """Returns required channel to send errors to

    Returns:
        str: Channel username/id
    """
    if config_dict["Telegram"]["channel"]:
        channel = config_dict["Telegram"]["channel"]
    else:
        print("Channel username/id is required to use Telegram bot")
        channel = None
    return channel


def send_telegram_error(message: str):
    if config_dict["Telegram"]["USE_TELEGRAM"]:
        if config_dict["Telegram"]["USE_TELEGRAM"] == "True":
            bot = get_bot()
            channel = get_channel()
            if bot and channel:
                try:
                    bot.send_message(channel, message)
                except requests.exceptions.ConnectionError:
                    print("Telegram log error failed: No connection established")
    else:
        print("Telegram status is uncertain or not provided")
        return
