import logging
import os


class Config(object):
    # Logging
    LOG_FILE = "logs/csedu_%s.log" % os.getpid()
    LOG_LEVEL = logging.DEBUG
