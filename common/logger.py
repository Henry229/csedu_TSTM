import logging
import os
from logging.handlers import TimedRotatingFileHandler

from .config import Config


def get_logger(log_file, log_level):
    if os.path.dirname(log_file):
        if not os.path.exists(os.path.dirname(log_file)):
            os.mkdir(os.path.dirname(log_file))

    logger = logging.getLogger('__name__')
    ch = logging.StreamHandler()
    fh = TimedRotatingFileHandler(log_file, when='W0')
    logger.addHandler(ch)
    logger.addHandler(fh)

    logger.setLevel(log_level)

    if log_level == logging.DEBUG:
        format = logging.Formatter(
            "%(asctime)s [%(filename)-10s:%(lineno)-5s:%(funcName)-30s] (%(levelname)s) : %(message)s")
    else:
        format = logging.Formatter("%(asctime)s (%(levelname)s)\t: %(message)s")

    ch.setFormatter(format)
    fh.setFormatter(format)

    return logger


def get_file_logger(log_file, log_level=logging.DEBUG):
    if os.path.dirname(log_file):
        if not os.path.exists(os.path.dirname(log_file)):
            os.mkdir(os.path.dirname(log_file))

    file_logger = logging.getLogger('__name__')
    file_handle = TimedRotatingFileHandler(log_file, when='W0')
    file_logger.addHandler(file_handle)

    file_logger.setLevel(log_level)

    if log_level == logging.DEBUG:
        format = logging.Formatter(
            "%(asctime)s [%(filename)-10s:%(lineno)-5s:%(funcName)-30s] (%(levelname)s) : %(message)s")
    else:
        format = logging.Formatter("%(asctime)s (%(levelname)s)\t: %(message)s")

    file_handle.setFormatter(format)

    return file_logger


log = get_logger(Config.LOG_FILE, Config.LOG_LEVEL)
