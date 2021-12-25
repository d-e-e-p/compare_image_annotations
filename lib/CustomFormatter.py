"""
based on https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
"""

import logging
import colorama
from colorama import Fore, Back, Style
from functools import partial

class CustomFormatter(logging.Formatter):

    col = {}
    col['white']    = Fore.WHITE  + Back.BLACK
    col['green']    = Fore.GREEN + Back.BLACK 
    col['red']      = Fore.RED + Back.LIGHTYELLOW_EX
    col['bold_red'] = Fore.RED  + Back.BLACK + Style.BRIGHT
    col['reset']     = Style.RESET_ALL

    fmt = {}
    fmt['long']  = '%(levelname)s | %(module)s | %(funcName)s | %(lineno)d : %(message)s'
    fmt['short'] = '%(levelname)s : %(message)s'

    FORMATS = {}
    for types in fmt.keys():
        FORMATS[types] = {
            logging.DEBUG:     col['white']     + fmt[types] + col['reset'],
            logging.INFO:      col['green']     + fmt[types] + col['reset'],
            logging.WARNING:   col['red']       + fmt[types] + col['reset'],
            logging.ERROR:     col['bold_red']  + fmt[types] + col['reset'],
            logging.CRITICAL:  col['bold_red']  + fmt[types] + col['reset'],
        }

    def __init__(self, type, color):
        self.type  = type
        self.color = color

    def format(self, record):

        if self.color:
            log_fmt = self.FORMATS[self.type].get(record.levelno)
        else:
            log_fmt = self.fmt[self.type]

        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
