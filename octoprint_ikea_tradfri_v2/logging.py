import logging
from logging import config


def init():
    print("Initialize logging....")
    try:
        config.fileConfig('./plugin_logging.conf')
    except Exception:
        logging.getLogger(__name__).warning(
            "Failed to load logger config from: './plugin_logging.conf'. Probably running in OctoPrint itself.")
    print("Logging initialized")


def get_logger(name: str):
    return logging.getLogger(name)


if __name__ == "__main__":
    print("Nothing to be run as main here! Only to be imported!")
else:
    init()
