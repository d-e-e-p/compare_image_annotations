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

from exitstatus import ExitStatus

from lib.Bbox import Bbox 
from lib.Bbox import BboxList

__author__      = 'deep@tensorfield.ag'
__copyright__   = 'Copyright (C) 2021 - Tensorfield Ag '
__license__     = 'New BSD License - https://opensource.org/licenses/BSD-3-Clause'
__maintainer__  = 'deep'
__status__      = 'Development'


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
    if not os.path.isdir(args.img):
        raise Exception(f'img dir {args.img} does not exist')
    if not os.path.isdir(args.out):
        raise Exception(f'out dir {args.out} does not exist')
    for xml in args.xml:
        if not os.path.isdir(xml):
            raise Exception(f'xml dir {xml} does not exist')



def main() -> ExitStatus:
    args = parse_args()
    if args.verbose:
        print(args)

    validate_args(args)
    b = BboxList(args.xml, args.tag, args.verbose)
    print(b)

    # opt.execute(args, operations,  solvers)
    # xml.read_data()
    # 

    return ExitStatus.success


if __name__ == "__main__":
    sys.exit(main())
