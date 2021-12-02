"""
class that reads xml files and returns a list of bounding boxes annotations
"""
import xml.etree.ElementTree as ET
import os
from collections import defaultdict
from glob import glob
import logging

from lib.Bbox   import Bbox
from lib.Bbox   import BboxList

class Parser:
    def __init__(self, bbl, xml_paths) :
        self.parse_xml_dirs(bbl, xml_paths)


    def parse_xml_dirs(self, bbl,  xml_path):
        """
        get the object in each xml file under xml_path
        """
        xml_ext = ".xml"
        for path in xml_path:
            for xml in glob(os.path.join(path, '*' + xml_ext)):
                logging.info(f"-> parsing xml file: {xml}")
                bbl.bbox_obj_list.extend(self.parse_xml_file(path, xml))



    def parse_xml_file(self, dir, file):
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
        image    = root.find('filename').text.rsplit('.', 1)[0]
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
            class_base, class_type = class_name.rsplit('_', 1)
            if class_type == 'outer' or class_type == 'meristem':     
                bbox = Bbox(dir, file, image,  class_base, class_type, difficult, [xmin, ymin, xmax, ymax])
                bbox_list.append(bbox)

            else:
                print(f"ERROR: class name should end in _outer or _meristem: {class_name}")
                print(f"ERROR: look at file: {file}")
        return bbox_list

    
