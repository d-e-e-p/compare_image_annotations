#!/usr/bin/env python3
#
# compare_image_annotations.py
#
# compare annotations in xml format between different image label sets
# the iou is computed assuming the first set is golden and all other sets of xml
# annotation have incorrect offsets.  
#
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import argparse
import logging
import colorama
from colorama import Fore, Back, Style
import shlex
from pathlib import Path
import tempfile

from PySide6.QtWidgets import (QLineEdit, QPushButton, QApplication, QVBoxLayout, QDialog)

sys.tracebacklimit = None

from lib.Bbox     import Bbox 
from lib.BboxList import BboxList
from lib.Parser   import Parser
from lib.Plotter  import Plotter
from lib.constants import VERSION, BUILD_DATE, AUTHOR
from lib.CustomFormatter import CustomFormatter

from libs.labelImg import run_main_gui

from libs.argsDialog import ArgsDialog, Results

__author__      = 'deep@tensorfield.ag'
__copyright__   = 'Copyright (C) 2021 - Tensorfield Ag '
__license__     = 'New BSD License - https://opensource.org/licenses/BSD-3-Clause'
__maintainer__  = 'deep'
__status__      = 'Development'
__appname__     = 'compare_image_annotations'


def parse_args() -> argparse.Namespace:
    """Parse user command line arguments."""
    parser = argparse.ArgumentParser(
        description='compare annotations in xml format between different image label sets')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--prune',   action='store_true')
    parser.add_argument('--check', choices=['relaxed', 'normal', 'strict'], default='normal')
    parser.add_argument('--data', required=False, help='xml and image directories', nargs='+')
    parser.add_argument('--out', required=False, help='output directory')

    return parser

def validate_args(args: argparse.Namespace):

    valid = True
    if not args.data:
        valid = False
    else:
        for data in args.data:
            if not os.path.isdir(data):
                valid = False
                logging.error(f' data dir {data} does not exist')

    return valid

def setup_logging(args):

    log = logging.getLogger()


    stream_handler = logging.StreamHandler()
    if args.verbose:
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(CustomFormatter(type='long',color=True))

    else:
        stream_handler.setLevel(logging.WARNING)
        stream_handler.setFormatter(CustomFormatter(type='short',color=True))
    log.addHandler(stream_handler)


    log_file_path = os.path.join(args.out, "debug.log")
    print(f"saving debug log to {log_file_path}")
    Path(log_file_path).unlink(missing_ok=True)

    file_handler = logging.FileHandler(filename=log_file_path)
    file_handler.setFormatter(CustomFormatter(type='long',color=False))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)
    log.setLevel(logging.DEBUG)
    log.removeHandler(log.handlers[0])  # key to avoid seeing double!

    return log

def run_args_gui():
    app = QApplication(sys.argv)
    res = Results()
    args_dialog  = ArgsDialog( text="Enter Args", res=res )
    args_dialog.show()
    app.exec()
    app.exit()
    if hasattr(res, "args"):
        return res.args
    else:
        return None

def main(): 

    #colorama.init(autoreset=True)
    colorama.init(autoreset=False)

    print()
    print(Style.BRIGHT + Fore.CYAN + Back.BLACK, end='')
    print(f"{__appname__}: version {VERSION} build {BUILD_DATE}")
    print(Style.RESET_ALL)


    parser = parse_args()
    args = parser.parse_args()
    # use gui if invalid args, otherwise proceed
    if not validate_args(args):
        argString = run_args_gui()
        if argString is None:
            print(Style.BRIGHT + Fore.GREEN + Back.BLACK, end='')
            print(f"cancel--existing")
            print(Style.RESET_ALL)
            sys.exit(0)

        args = parser.parse_args(shlex.split(argString))

    # if .out is not specified, just pick tempdir

    if not args.out:
        args.out = tempfile.mkdtemp()

    setup_logging(args)
    logging.info(args)

    # return if validate fails to find dirs
    #if err := validate_args(args):
    #    return err

    col = Fore.BLACK + Back.CYAN

    bbl = BboxList(args)
    print(f"     {col} checking xml " + Style.RESET_ALL)
    print(f"     {col} loading gui " + Style.RESET_ALL)
    app, _win = run_main_gui(bbl, args)
    print(f"     {col} display xml " + Style.RESET_ALL)

    return app.exec()
    print(f"    done " + Style.RESET_ALL)




if __name__ == "__main__":
    sys.exit(main())
