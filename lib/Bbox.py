"""
class that reads xml files and returns a list of bounding boxes annotations
"""
import xml.etree.ElementTree as ET
import os
import math
import time
from collections import defaultdict
from glob import glob
import pudb

# from https://stackoverflow.com/questions/2600790/multiple-levels-of-collection-defaultdict-in-python
class DeepDict(defaultdict):
    def __call__(self):
        return DeepDict(self.default_factory)

class Bbox:
    def __init__ (self, dir, file, image,  class_base, class_type, difficult, bbox):
        self.dir  = dir
        self.file = file
        self.image = image
        self.class_base = class_base
        self.class_type = class_type
        self.difficult  = difficult
        self.bbox = bbox
        self.meristem = None
        self.iou = 'U'


class BboxList:
    def __init__(self, xml_paths, tag, verbose, img_ext='.jpg', xml_ext='.xml') :

        self.tag = tag
        self.verbose = verbose
        self.img_ext = img_ext
        self.xml_ext = xml_ext
        self.bbox_obj_list = []
        self.golden_dir = defaultdict(defaultdict)
        
        self.parse_xml_dirs(xml_paths)
        self.compute_centers()
        self.compute_iou()

    # TODO: combine filter functions 

    # search objects with NOT matching parameters
    def rfilter(self, bbox_obj_list,  **kwargs):
        items = []
        for item in bbox_obj_list:
            if all(item.__dict__[k] != v for k, v in kwargs.items()):
                items.append(item)
        return items

    # search objects with matching parameters
    def filter(self, bbox_obj_list,  **kwargs):
        items = []
        for item in bbox_obj_list:
            if all(item.__dict__[k] == v for k, v in kwargs.items()):
                items.append(item)
        return items



    # TODO: replace with logger
    def vprint(self, string):
        if self.verbose:
            print(string)
    
    def parse_xml_dirs(self, xml_path):
        """
        get the list of bboxes
        """
        for path in xml_path:
            for xml in glob(os.path.join(path, '*' + self.xml_ext)):
                self.vprint(f"-> parsing xml file: {xml}")
                self.bbox_obj_list.extend(self.parse_xml_file(path, xml))



    def parse_xml_file(self, dir, file):
#   parse xml file that looks like:
#
#            <annotation>
#        <folder>Review</folder>
#        <filename>img0002901.jpg</filename>
#        <path>C:\Users\CFGuest\Desktop\Review\img0002901.jpg</path>
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

    def compute_centers(self):
        """
        create new box elements with centers
        """
        for obj in self.bbox_obj_list:
            if obj.class_type == 'outer':
                self.vprint(f"box is outer = {obj}")
                inner_obj_list = self.filter(self.bbox_obj_list, 
                        dir        = obj.dir,
                        image      = obj.image, 
                        class_base = obj.class_base,
                        class_type = 'meristem')
                self.compute_center(obj, inner_obj_list)




    def compute_center(self, obj_src, inner_obj_list):
        """
        compute the closest meristem to the center of the outer bbox
        """
        
        xmin, ymin, xmax, ymax = obj_src.bbox
        x_center = (xmin + xmax) / 2
        y_center = (ymin + ymax) / 2
        min_dist = math.inf
        for obj in inner_obj_list:
            xmin_inner, ymin_inner, xmax_inner, ymax_inner = obj.bbox
            x_center_inner = (xmin_inner + xmax_inner) / 2
            y_center_inner = (ymin_inner + ymax_inner) / 2
            if (xmin <= x_center_inner <= xmax) and (ymin <= y_center_inner <= ymax):
                dist = math.sqrt((x_center - x_center_inner)**2 + (y_center - y_center_inner)**2)
                if dist < min_dist:
                    min_dist = dist
                    min_obj  = obj

        if min_dist == math.inf:
            self.vprint(f"WARNING: no meristem found for {obj_src.bbox}")
            min_obj = None
        else:
            min_dist = round(min_dist)

        obj_src.meristem = min_obj

    def compute_iou(self):
        """
        compute the iou of each outer against all other annotations of that same class
        """

        # pass1 : select golden_dir based on image with most annotations for a class
        # golden_dir[image][class_base]

        num_annotations  =  DeepDict(DeepDict(DeepDict(DeepDict((lambda: 0)))))
        max_annotation   =  DeepDict(DeepDict((lambda: 0)))

        # pass1: for each image/class_base find num of annotations and record golden dir
        for obj in self.bbox_obj_list:
            num_annotations[obj.dir][obj.image][obj.class_base][obj.class_type] += 1
                
        for dir in num_annotations:
            for image in num_annotations[dir]:
                for class_base in num_annotations[dir][image]:
                    # count all class_types
                    n = 0
                    for class_type in num_annotations[dir][image][class_base]:
                        n +=  num_annotations[dir][image][class_base][class_type]
                    if n > max_annotation[image][class_base]:
                        max_annotation[image][class_base] = n
                        self.golden_dir[image][class_base] = dir
            self.vprint(f"golden dir = {self.golden_dir}")

        # pass2: compute iou for each box relative to golden
        for obj_src in self.bbox_obj_list:
            gdir = self.golden_dir[obj_src.image][obj_src.class_base]
            if obj_src.dir == gdir:
                continue
            tgt_obj_list = self.filter(self.bbox_obj_list, 
                            dir        = gdir,
                            image      = obj_src.image, 
                            class_base = obj_src.class_base,
                            class_type = obj_src.class_type)
            obj_src.iou = self.compute_iou_obj_list(obj_src, tgt_obj_list)


    def compute_iou_obj_list(self, obj_src, tgt_obj_list):
        """
        compute the intersection over union between obj_src and tgt_obj_list, returning the min value
        """
        iou_min = 0
        self.vprint(f"box_src={obj_src.bbox} bbox_list={tgt_obj_list}")
        for obj_tgt in tgt_obj_list:
            iou = self.compute_iou_bbox_pair(obj_src.bbox, obj_tgt.bbox)
            if iou < iou_min:
                iou_min = iou

        return iou_min

                        


    def compute_iou_bbox_pair(self, bbox_src, bbox_tgt):
        """
        compute Intersection-over-Union between 2 boxes
        """
        if not bbox_tgt:
            return 0

        self.vprint(f"bbox_src={bbox_src} bbox_tgt={bbox_tgt}")

        xmin_src, ymin_src, xmax_src, ymax_src = bbox_src
        xmin_tgt, ymin_tgt, xmax_tgt, ymax_tgt = bbox_tgt
        x_overlap = max(0, min(xmax_src, xmax_tgt) - max(xmin_src, xmin_tgt))
        y_overlap = max(0, min(ymax_src, ymax_tgt) - max(ymin_src, ymin_tgt))
        intersection = x_overlap * y_overlap

        area_src = (xmax_src - xmin_src) * (ymax_src - ymin_src)
        area_tgt = (xmax_tgt - xmin_tgt) * (ymax_tgt - ymin_tgt)
        union = area_src + area_tgt - intersection

        return intersection / union




    
