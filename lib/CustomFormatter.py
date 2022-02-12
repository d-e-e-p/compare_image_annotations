"""
based on https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
"""

import logging
import colorama
from colorama import Fore, Back, Style

colorama.init(autoreset=False)

class CustomFormatter(logging.Formatter):



    col = {}
    col['white']    = Fore.WHITE  + Back.BLACK
    col['green']    = Fore.GREEN + Back.BLACK 
    col['red']      = Fore.RED + Back.LIGHTYELLOW_EX
    col['bold_red'] = Fore.RED  + Back.BLACK + Style.BRIGHT
    col['reset']     = Style.RESET_ALL

    fmta = {}
    fmta['long']  = '%(levelname)s | %(module)s | %(funcName)s | %(lineno)d : %(message)s'
    fmta['short'] = '%(levelname)s : %(message)s'

    fmti = {}
    fmti['long']  = fmta['long']
    fmti['short'] = '%(message)s'

    FORMATS = {}
    for types in fmta.keys():
        FORMATS[types] = {
            logging.DEBUG:     col['white']     + fmta[types] + col['reset'],
            logging.INFO:      col['green']     + fmti[types] + col['reset'],
            logging.WARNING:   col['red']       + fmta[types] + col['reset'],
            logging.ERROR:     col['bold_red']  + fmta[types] + col['reset'],
            logging.CRITICAL:  col['bold_red']  + fmta[types] + col['reset'],
        }

    def __init__(self, type, color):
        self.type  = type
        self.color = color

    def format(self, record):

        if self.color:
            log_fmt = self.FORMATS[self.type].get(record.levelno)
        else:
            log_fmt = self.fmta[self.type]

        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
