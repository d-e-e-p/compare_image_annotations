#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement
from lxml import etree
import codecs
from pathlib import Path

from libs.constants import DEFAULT_ENCODING
from libs.build_stamp import *

import psutil
from datetime import datetime
from collections import Counter
import logging

import hashlib

XML_EXT = '.xml'
ENCODE_METHOD = DEFAULT_ENCODING

from libs.plantData import PLANT_NAMES, TYPE_NAMES, PLANT_TYPE_NAMES, PLANT_COLORS
from libs.plantData import split_name_into_plant_and_type, has_valid_suffix

class FileStats:
    pass

class PascalVocWriter:

    def __init__(self, folder_name, filename, img_size, database_src='Unknown', local_img_path=None):
        self.folder_name = folder_name
        self.filename = filename
        self.database_src = database_src
        self.img_size = img_size
        self.box_list = []
        self.local_img_path = local_img_path
        self.verified = False
        self.xmlfile = ""
        self.filestats = FileStats()

    def prettify(self, elem):
        """
            Return a pretty-printed XML string for the Element.
        """
        rough_string = ElementTree.tostring(elem, 'utf8')
        root = etree.fromstring(rough_string)
        return etree.tostring(root, pretty_print=True, encoding=ENCODE_METHOD).replace("  ".encode(), "\t".encode())
        # minidom does not support UTF-8
        # reparsed = minidom.parseString(rough_string)
        # return reparsed.toprettyxml(indent="\t", encoding=ENCODE_METHOD)

    # see https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
    # yeah we don't really need the optimization overhead for small image files...
    def sha256sum(self, filename, bufsize=128 * 1024):
        h = hashlib.sha256()
        buffer = bytearray(bufsize)
        # using a memoryview so that we can slice the buffer without copying it
        buffer_view = memoryview(buffer)
        with open(filename, 'rb', buffering=0) as f:
            while True:
                n = f.readinto(buffer_view)
                if not n:
                    break
                h.update(buffer_view[:n])
        return h.hexdigest()


    def gen_xml(self):
        """
            Return XML root
        """
        # Check conditions
        if self.filename is None or \
                self.folder_name is None or \
                self.img_size is None:
            return None

        top = Element('annotation')
        if self.verified:
            top.set('verified', 'yes')

        folder = SubElement(top, 'folder')
        folder.text = self.folder_name

        SubElement(top, 'version').text = VERSION
        SubElement(top, 'build_date').text = BUILD_DATE

        dt = datetime.now()
        timestamp = dt.strftime("%Y-%m-%d %H:%M %Z")

        username = psutil.Process().username() 
        filename = self.filename

        SubElement(top, 'timestamp').text = timestamp
        SubElement(top, 'username').text =  username
        SubElement(top, 'filename').text =  filename

        setattr(self.filestats, "username" , username)
        setattr(self.filestats, "timestamp" , timestamp)
        setattr(self.filestats, "filename" , filename)

        cname, cplant, ctype = self.count_objects()
        SubElement(top, 'name_count').text = f"{cname.most_common()}"
        SubElement(top, 'plant_count').text = f"{cplant.most_common()}"
        SubElement(top, 'type_count').text  = f"{ctype.most_common()}"

        if self.xmlfile is not None:
            SubElement(top, 'xmlpath').text = self.xmlfile

        if self.local_img_path is not None:
            SubElement(top, 'imgpath').text = self.local_img_path
            checksum = self.sha256sum(self.local_img_path)
            SubElement(top, 'image_sha256').text = checksum

        source = SubElement(top, 'source')
        database = SubElement(source, 'database')
        database.text = self.database_src

        size_part = SubElement(top, 'size')
        width = SubElement(size_part, 'width')
        height = SubElement(size_part, 'height')
        depth = SubElement(size_part, 'depth')
        width.text = str(self.img_size[1])
        height.text = str(self.img_size[0])
        if len(self.img_size) == 3:
            depth.text = str(self.img_size[2])
        else:
            depth.text = '1'

        segmented = SubElement(top, 'segmented')
        segmented.text = '0'
        return top

    def add_bnd_box(self, x_min, y_min, x_max, y_max, name, note, user, difficult):
        bnd_box = {'xmin': x_min, 'ymin': y_min, 'xmax': x_max, 'ymax': y_max}
        bnd_box['name'] = name
        bnd_box['note'] = note
        bnd_box['user'] = user
        bnd_box['difficult'] = difficult
        self.box_list.append(bnd_box)

    def count_objects(self):
        namelist = []
        for each_object in self.box_list:
            namelist.append(each_object['name'])
    
        cname  = Counter()
        cplant = Counter()
        ctype  = Counter()
        for name in namelist:
            cname[name] += 1
            plant, type = split_name_into_plant_and_type(name)
            cplant[plant] += 1
            ctype[type] += 1

        return cname, cplant, ctype


    def append_objects(self, top):
        for each_object in self.box_list:
            object_item = SubElement(top, 'object')
            name = SubElement(object_item, 'name')
            name.text = each_object['name']
            if each_object['note']:
                note = SubElement(object_item, 'note')
                note.text = each_object['note']
            if each_object['user']:
                user = SubElement(object_item, 'user')
                user.text = each_object['user']
            pose = SubElement(object_item, 'pose')
            pose.text = "Unspecified"
            truncated = SubElement(object_item, 'truncated')
            if int(float(each_object['ymax'])) == int(float(self.img_size[0])) or (int(float(each_object['ymin'])) == 1):
                truncated.text = "1"  # max == height or min
            elif (int(float(each_object['xmax'])) == int(float(self.img_size[1]))) or (int(float(each_object['xmin'])) == 1):
                truncated.text = "1"  # max == width or min
            else:
                truncated.text = "0"
            difficult = SubElement(object_item, 'difficult')
            difficult.text = str(bool(each_object['difficult']) & 1)
            bnd_box = SubElement(object_item, 'bndbox')
            x_min = SubElement(bnd_box, 'xmin')
            x_min.text = str(each_object['xmin'])
            y_min = SubElement(bnd_box, 'ymin')
            y_min.text = str(each_object['ymin'])
            x_max = SubElement(bnd_box, 'xmax')
            x_max.text = str(each_object['xmax'])
            y_max = SubElement(bnd_box, 'ymax')
            y_max.text = str(each_object['ymax'])

    def save(self, target_file=None):

        if target_file is None:
            self.xmlfile = self.filename + XML_EXT
        else:
            self.xmlfile = target_file


        root = self.gen_xml()
        self.append_objects(root)
        prettify_result = self.prettify(root)

        out_file = codecs.open( self.xmlfile, 'w', encoding=ENCODE_METHOD)
        out_file.write(prettify_result.decode('utf8'))
        out_file.close()



class PascalVocReader:

    def __init__(self, file_path):
        # shapes type:
        # [labbel, [(x1,y1), (x2,y2), (x3,y3), (x4,y4)], color, color, difficult]
        self.shapes = []
        self.file_path = file_path
        self.verified = False
        self.filestats = FileStats()
        self.parse_xml()

    def get_shapes(self):
        return self.shapes

    def add_shape(self, label, bnd_box, note, user, difficult):
        x_min = int(float(bnd_box.find('xmin').text))
        y_min = int(float(bnd_box.find('ymin').text))
        x_max = int(float(bnd_box.find('xmax').text))
        y_max = int(float(bnd_box.find('ymax').text))
        points = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
        self.shapes.append((label, points, None, None, note, user, difficult))



    def fix_labels(self, file, text):
        """
        fix common problems with labels!
        """
        text = text.lower()
        basename = Path(file).name
        logging.debug(f" {basename}: fixing  {text}")
        if '-' in text:
            out = text.replace('-','_')
            logging.info(f" {basename}: replaced dash so {text} -> {out}")
            text = out

        if '_meristem' in text:
            out = text.replace('_meristem','_stem')
            #logging.info(f" {basename}: replaced meristem so {text} -> {out}")
            text = out

        if not has_valid_suffix(text):
            out = text + "_outer"
            logging.info(f" {basename}: missing valid type suffix so assuming {text} -> {out}")
            text = out

        if text not in PLANT_TYPE_NAMES:
            logging.warning(f" {basename}: label {text} not in standard label types: {PLANT_TYPE_NAMES}")

        logging.debug(f" {basename}: returning  {text}")
        return text
        


    def parse_xml(self):
        logging.debug(f"parsing {self.file_path}")
        assert self.file_path.endswith(XML_EXT), "Unsupported file format"
        parser = etree.XMLParser(encoding=ENCODE_METHOD)
        xml_tree = ElementTree.parse(self.file_path, parser=parser).getroot()
        filename = xml_tree.find('filename').text
        self.filestats.filename = filename
        try:
            verified = xml_tree.attrib['verified']
            if verified == 'yes':
                self.verified = True
        except KeyError:
            self.verified = False

        attr = "username timestamp image_sha256".split()
        for key in attr:
            if xml_tree.find(key) is not None:
                value = xml_tree.find(key).text
            else:
                value = None
            setattr(self.filestats, key, value)


        for object_iter in xml_tree.findall('object'):
            bnd_box = object_iter.find("bndbox")
            label = object_iter.find('name').text
            label = self.fix_labels(self.file_path, label)
            logging.debug(f"fix_label = {label}")
            if object_iter.find('note') is not None:
                note = object_iter.find('note').text
            else:
                note = None
            if object_iter.find('user') is not None:
                user = object_iter.find('user').text
            else:
                user = None

            # Add chris
            difficult = False
            if object_iter.find('difficult') is not None:
                difficult = bool(int(object_iter.find('difficult').text))
            self.add_shape(label, bnd_box, note, user, difficult)

        return True
