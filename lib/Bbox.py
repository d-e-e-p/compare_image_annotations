"""
class that reads xml files and returns a list of bounding boxes annotations
"""
import xml.etree.ElementTree as ET
import os
import numpy as np
import copy
import time
from collections import defaultdict
from glob import glob
import numpy as np
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


class BboxList:
    def __init__(self, xml_paths, tag, verbose, img_ext='.jpg', xml_ext='.xml') :

        self.tag = tag
        self.verbose = verbose
        self.img_ext = img_ext
        self.xml_ext = xml_ext
        self.bbox_obj_list = []
        
        self.parse_xml_dirs(xml_paths)
        self.compute_centers()
        self.compute_iou()

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
                bbox   = obj.bbox
                dir    = obj.dir
                image  = obj.image
                inner_obj_list = self.get_inner_objects(obj) 
                self.compute_center(obj, inner_obj_list)
                # get all objects not matching dir but matching image, type, 


    def get_inner_objects(self, obj_src):
        obj_list = []                
        for obj in self.bbox_obj_list:
            if  (obj.dir == obj_src.dir) and \
                (obj.image == obj_src.image) and \
                (obj.class_base == obj_src.class_base) and \
                (obj.class_type == 'meristem'):
                obj_list.append(obj)

        return obj_list

    def compute_center(self, obj_src, inner_obj_list):
        """
        compute the closest meristem to the center of the outer bbox
        """
        
        xmin, ymin, xmax, ymax = obj_src.bbox
        x_center = (xmin + xmax) / 2
        y_center = (ymin + ymax) / 2
        min_dist = np.inf
        for obj in inner_obj_list:
            xmin_inner, ymin_inner, xmax_inner, ymax_inner = obj.bbox
            x_center_inner = (xmin_inner + xmax_inner) / 2
            y_center_inner = (ymin_inner + ymax_inner) / 2
            if (xmin <= x_center_inner <= xmax) and (ymin <= y_center_inner <= ymax):
                dist = np.sqrt((x_center - x_center_inner)**2 + (y_center - y_center_inner)**2)
                if dist < min_dist:
                    min_dist = dist
                    min_obj  = obj

        if min_dist == np.inf:
            self.vprint(f"WARNING: no meristem found for {obj_src.bbox}")
            min_obj = None
        else:
            min_dist = round(min_dist)

        obj_src.meristem = min_obj

    def compute_iou(self):
        """
        compute the iou of each outer against all other annotations of that same class
        """
        iou_rms = defaultdict(lambda: defaultdict(defaultdict))
        # pass1: compute iou for each class
        for obj_src in self.bbox_obj_list:
            obj_list = get_potential_iou_matches(obj_src)
            iou = self.compute_iou_bbox(bbox, bbox_tgt)



        for dir_src in self.cbox_map:
            for image in self.cbox_map[dir_src]:
                for class_base in self.cbox_map[dir_src][image]:
                    cboxes = self.cbox_map[dir_src][image]
                    for class_base in cboxes:
                        bboxes = cboxes[class_base]
                        for bbox in bboxes:
                            # ok, now loop over all similar boxes in other images looking for the closest on
                            iou_list = []
                            for dir_tgt in self.cbox_map:
                                if dir_tgt == dir_src:
                                    continue
                                bbox_tgt = self.cbox_map[dir_tgt][image][class_base]
                                iou = self.compute_iou_bbox(bbox, bbox_tgt)
                                iou_list.append(iou)

                        iou_rms[dir_src][image][class_base] = np.sqrt(np.mean(iou_list))
                        self.vprint(f"{dir_src} {image} {class_base} ioulist {iou_list} {iou_rms[dir_src][image][class_base]}")
                        #pu.db

        # pass2: now record the iou against only the golden standard
        iou_min = DeepDict(DeepDict((lambda: np.inf)))
        golden_dir = DeepDict(DeepDict(str))
        for dir_src in iou_rms:
            for image in iou_rms[dir_src]:
                for class_base in self.bbox_map[dir_src][image]:
                    iou = iou_rms[dir_src][image][class_base]
                    if iou < iou_min[image][class_base]:
                        iou_min[image][class_base] = iou
                        golden_dir[image][class_base] = dir_src


        for image in iou_min:
            for class_base in iou_min[image]:
                self.vprint(f" image={image} class={class_base} iou_min={iou_min[image][class_base]} golden_dir={golden_dir[image][class_base]}")

        # pass3: now compute actual iou against the golden standard for each box
        for dir_src in self.cbox_map:
            for image in self.cbox_map[dir_src]:
                for class_base in self.cbox_map[dir_src][image]:
                    dir_tgt = golden_dir[image][class_base]
                    cboxes = self.cbox_map[dir_src][image]
                    rboxes = defaultdict(list)
                    for class_base in cboxes:
                        if not cboxes[class_base]:
                            continue
                        for bbox in cboxes[class_base]:
                            self.vprint(f"one box={bbox}")
                            if bbox is None:
                                continue
                            else:
                                bbox_tgt = self.cbox_map[dir_tgt][image][class_base]
                                iou = self.compute_iou_bbox(bbox, bbox_tgt)
                                bbox.append(iou)
                                rboxes[class_base].append(bbox)
                            self.vprint(f"{dir_src} {image} {class_base} iou={iou}")
                    self.cbox_map[dir_src][image] = rboxes
                        

    def compute_iou_bbox(self, bbox_src, bbox_list):
        """
        compute the intersection over union between bbox_src and bbox_list, returning the min value
        """
        iou_list = []
        self.vprint(f"bbox_src={bbox_src} bbox_list={bbox_list}")
        for bbox_tgt in bbox_list:
            self.vprint(f"bbox_src={bbox_src} bbox_tgt={bbox_tgt}")
            iou = self.compute_iou_bbox_pair(bbox_src[0], bbox_tgt[0])
            iou_list.append(iou)

        if not iou_list:
            return 0
        else:
            return min(iou_list)

    def compute_iou_bbox_pair(self, bbox_src, bbox_tgt):
        """
        compute Intersection-over-Union between 2 boxes
        """
        if not bbox_tgt:
            return 0

        self.vprint(f"bbox_src={bbox_src} bbox_tgt={bbox_tgt}")
        xmin_src, ymin_src, xmax_src, ymax_src, _ = bbox_src
        xmin_tgt, ymin_tgt, xmax_tgt, ymax_tgt, _ = bbox_tgt
        x_overlap = max(0, min(xmax_src, xmax_tgt) - max(xmin_src, xmin_tgt))
        y_overlap = max(0, min(ymax_src, ymax_tgt) - max(ymin_src, ymin_tgt))
        intersection = x_overlap * y_overlap
        area_src = (xmax_src - xmin_src) * (ymax_src - ymin_src)
        area_tgt = (xmax_tgt - xmin_tgt) * (ymax_tgt - ymin_tgt)
        union = area_src + area_tgt - intersection
        return intersection / union




    
