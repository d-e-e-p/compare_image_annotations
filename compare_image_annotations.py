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


sys.tracebacklimit = None

from lib.Bbox    import Bbox 
from lib.Bbox    import BboxList
from lib.Parser  import Parser
from lib.Plotter import Plotter
from lib.constants import VERSION, BUILD_DATE, AUTHOR
from lib.CustomFormatter import CustomFormatter

from libs.labelImg import run_main_gui

__author__      = 'deep@tensorfield.ag'
__copyright__   = 'Copyright (C) 2021 - Tensorfield Ag '
__license__     = 'New BSD License - https://opensource.org/licenses/BSD-3-Clause'
__maintainer__  = 'deep'
__status__      = 'Development'
__appnane__     = 'compare_image_annotations'


def parse_args() -> argparse.Namespace:
    """Parse user command line arguments."""
    parser = argparse.ArgumentParser(
        description='compare annotations in xml format between different image label sets')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--check', choices=['relaxed', 'normal', 'strict'], default='normal')
    parser.add_argument('--img', required=True, help='image directory')
    parser.add_argument('--xml', required=True, help='list of xml directories', nargs='+')
    parser.add_argument('--out', required=True, help='output directory')

    args = parser.parse_args()
    return args

def validate_args(args: argparse.Namespace):

    err = 0
    if not os.path.isdir(args.img):
        logging.error(f' img dir {args.img} does not exist')
        err = 1
    if not os.path.isdir(args.out):
        logging.error(f' out dir {args.out} does not exist')
        err = 1
    for xml in args.xml:
        if not os.path.isdir(xml):
            logging.error(f' xml dir {xml} does not exist')
            err = 1

    return err

def setup_logging(args):

    log = logging.getLogger()

    format_long = logging.Formatter(
    '%(levelname)s | %(module)s | %(funcName)s | %(lineno)d : %(message)s')
    format_short = logging.Formatter('%(levelname)s : %(message)s')

    #logging.basicConfig(level=logging.DEBUG)
    log.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    if args.verbose:
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(CustomFormatter(type='long',color=True))

    else:
        stream_handler.setLevel(logging.WARNING)
        stream_handler.setFormatter(CustomFormatter(type='short',color=True))
    log.addHandler(stream_handler)

    logFilePath = os.path.join(args.out, "debug.log")
    file_handler = logging.FileHandler(filename=logFilePath)
    file_handler.setFormatter(CustomFormatter(type='long',color=False))
    file_handler.setLevel(logging.DEBUG)
    log.addHandler(file_handler)

    return log


def main(): 

    #colorama.init(autoreset=True)
    colorama.init(autoreset=False)

    print()
    print(Style.BRIGHT + Fore.CYAN + Back.BLACK, end='')
    print(f"{__appnane__}: version {VERSION} build {BUILD_DATE}")
    print(Style.RESET_ALL)

    args = parse_args()

    setup_logging(args)
    logging.info(args)

    # return if validate fails to find dirs
    if err := validate_args(args):
        return err

    col = Fore.BLACK + Back.CYAN

    bbl = BboxList()
    print(f"    0/5 {col} loading xml " + Style.RESET_ALL)
    Parser(bbl, args)
    logging.info(bbl)
    bbl.update_stats()
    print(f"    1/5 {col} associating outer with meristem " + Style.RESET_ALL)
    bbl.associate_stem_with_outer()
    print(f"    2/5 {col} computing IOU " + Style.RESET_ALL)
    bbl.compute_iou_for_each_annotation()
    print(f"    3/5 {col} finding potential mis-labels " + Style.RESET_ALL)
    bbl.locate_potential_mislabel()
    print(f"    4/5 {col} saving report plots " + Style.RESET_ALL)
    pl = Plotter(bbl, args)
    print(f"    5/5 {col} loading gui " + Style.RESET_ALL)

    app, _win = run_main_gui(bbl, pl, args)
    return app.exec_()
    print(f"    done " + Style.RESET_ALL)




if __name__ == "__main__":
    sys.exit(main())
