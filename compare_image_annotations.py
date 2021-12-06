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

sys.tracebacklimit = None

from lib.Bbox    import Bbox 
from lib.Bbox    import BboxList
from lib.Parser  import Parser
from lib.Plotter import Plotter

from libs.labelImg import *

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
    parser.add_argument('--tag')
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


def main(): 
    args = parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, force=True)
        logging.basicConfig(format='%(levelname)s %(module)s %(funcName)s %(lineno)d %(message)s', force=True)
        logging.warning(args)
    else:
        logging.basicConfig(level=logging.WARNING)
        logging.basicConfig(format='%(levelname)s %(message)s', force=True)

    logging.debug(args)
    # return if validate fails to find dirs
    if err := validate_args(args):
        return err

    bbl = BboxList()
    print("    0 Loading xml:")
    Parser(bbl, args.xml)
    logging.info(bbl)
    bbl.update_stats()
    print("    1 associating outer with meristem")
    bbl.associate_stem_with_outer()
    print("    2 computing IOU")
    bbl.compute_iou_for_each_annotation()
    print("    3 finding potential mis-labels")
    bbl.locate_potential_mislabel()
    print("    4 saving report plots")
    pl = Plotter(bbl, args.img, args.out)
    print("    5 loading gui")

    app, _win = run_main_gui(bbl, pl, args.img, args.out)
    return app.exec_()




if __name__ == "__main__":
    sys.exit(main())
