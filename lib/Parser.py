"""
class that reads xml files and returns a list of bounding boxes annotations
"""
import xml.etree.ElementTree as ET
import os
from collections import defaultdict
from glob import glob
import logging
import sys
from pathlib import Path
import filecmp


from lib.Bbox   import Bbox
from lib.Bbox   import BboxList

class Parser:
    def __init__(self, bbl, args) :
        xml_ext = ".xml"
        jpg_ext = ".jpg"
        self.bbl = bbl

        stem2xmls = self.get_files_with_mutiple_versions(args.data, xml_ext, args.prune)
        stem2jpgs = self.get_files_with_mutiple_versions(args.data, jpg_ext, False     )

        self.parse_xml_dirs(stem2xmls, args.check)
        self.bbl.update_stats()

        self.parse_jpg_dirs(stem2jpgs)


    def get_files_with_mutiple_versions(self, root_dir, ext, prune):
        """
        same xml or jpg has more than 1 version
        """
        files = []
        stem2files = defaultdict(list)
        for rdir in root_dir:
            logging.info(f"{rdir} in {root_dir}")
            for dir, _, files in os.walk(rdir, followlinks=True):
                logging.info(f"{dir} {_} {files}")
                for file in files:
                    if file.endswith(ext): 
                        filename = os.path.join(dir, file)
                        stem = Path(filename).stem
                        stem2files[stem].append(filename)
        logging.info(f"{stem2files}")

        # remove entries with only 1 xml
        if prune:
            stem2files = dict(filter(lambda elem: len(elem[1]) > 1, stem2files.items()))

        logging.info(f"{prune} : {stem2files}")

        #sys.exit(0)
        return stem2files


    def parse_xml_dirs(self, stem2xmls, check_level):
        """
        get the object in each xml file under xml_path
        """
        for stem, files in stem2xmls.items():
            for file in files:
                print(f"     -> loading: {file}", end='')
                bbox_list = self.parse_xml_file(stem, file, check_level)
                self.bbl.bbox_obj_list.extend(bbox_list)
                print(f" ({len(bbox_list)} boxes)")

    def parse_jpg_dirs(self, stem2jpgs):
        """
        get the object in each jpg file under jpg_path
        """
        err_exit = False
        image_list = self.bbl.stats.image_list
        for stem, files in stem2jpgs.items():
            if stem in image_list:
                self.bbl.stem2jpgs[stem] = files[0]
                if len(files) > 1:
                    for file in files[1:]:
                        if not filecmp.cmp(files[0], file):
                            logging.error(f"clash between multiple jpg files that are not the same: ")
                            logging.error(f"clash     {files[0]}")
                            logging.error(f"clash     {file}")
                            err_exit = True

        if err_exit:
            exit(-1)
        logging.debug(self.bbl.stem2jpgs)


    def collapse_class_names(self, class_base):
        """
        easy mode
        """
        known_types = "carrot spinach unknown".split()
        for type in known_types:
            if type in class_base:
                return type

        # not a known type? must be a weed
        return 'weed'

    def parse_xml_file(self, stem, file, check_level):
#    """
#    parse xml file that looks like:
#
#            <annotation>
#        <folder>Review</folder>
#        <filename>img0002901.jpg</filename>
#        <path>/tmp/test/img0002901.jpg</path>
#        <source>
#            <database>Unknown</database>
#        </source>
#        <size>
#            <width>1456</width>
#            <height>1088</height>
#            <depth>3</depth>
#        </size>
#        <segmented>0</segmented>
#        <object>
#            <name>carrot_outer</name>
#            <pose>Unspecified</pose>
#            <truncated>0</truncated>
#            <difficult>0</difficult>
#            <bndbox>
#                <xmin>650</xmin>
#                <ymin>55</ymin>
#                <xmax>847</xmax>
#                <ymax>208</ymax>
#            </bndbox>
#        </object>
#
#    """
        
        tree = ET.parse(file)
        root = tree.getroot()
        bbox_list = []

        folder   = root.find('folder').text
        #image    = root.find('filename').text.rsplit('.', 1)[0]
        image    = stem
        path     = root.find('path').text
        img_size = root.find('size')
        objects  = root.findall('object')
        bboxes = defaultdict(lambda: defaultdict(list))
        for obj in objects:
            class_name = obj.find('name').text
            class_name = class_name.replace(' ','_').lower()
            difficult = int(obj.find('difficult').text)
            bbox = obj.find('bndbox')
            xmin = int(bbox.find('xmin').text)
            ymin = int(bbox.find('ymin').text)
            xmax = int(bbox.find('xmax').text)
            ymax = int(bbox.find('ymax').text)

            # carrot_outer -> carrot , outer
            if '_' in class_name:
                class_base, class_type_name = class_name.rsplit('_', 1)
            else:
                logging.warning(f"class name should end in _outer or _meristem: {class_name}")
                logging.warning(f"look at file: {file}")
                class_base = class_name
                class_type_name = 'outer'

            if class_type_name != 'outer' and class_type_name != 'meristem':     
                logging.error(f"class name should end in _outer or _meristem: {class_name}")
                logging.error(f"look at file: {file}")
            else:
                class_type = class_type_name
                if class_type_name == "meristem":
                    class_type = "inner"

                if check_level == "relaxed": 
                    class_base = self.collapse_class_names(class_base)

                dir = str(Path(file).parent)
                bbox = Bbox(dir, file, image,  class_base, class_type, difficult, [xmin, ymin, xmax, ymax])
                bbox_list.append(bbox)

        return bbox_list

    
