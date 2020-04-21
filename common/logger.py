import logging
import os
from logging.handlers import TimedRotatingFileHandler


def get_logger():
    log_file = os.path.join('logs', 'tailored.log')
    if os.path.dirname(log_file):
        if not os.path.exists(os.path.dirname(log_file)):
            os.mkdir(os.path.dirname(log_file))

    logger = logging.getLogger('tailored')
    ch = logging.StreamHandler()
    fh = TimedRotatingFileHandler(log_file, when='W0')
    logger.addHandler(ch)
    logger.addHandler(fh)

    logger.setLevel(logging.DEBUG)
    format = logging.Formatter(
        "%(asctime)s [%(filename)-10s:%(lineno)-5s:%(funcName)-30s] (%(levelname)s) : %(message)s")

    ch.setFormatter(format)
    fh.setFormatter(format)

    return logger


log = get_logger()
