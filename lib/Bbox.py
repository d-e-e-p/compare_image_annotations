"""
class that reads xml files and returns a list of bounding boxes annotations
"""
import xml.etree.ElementTree as ET
import os
import math
import time
from collections import defaultdict
from glob import glob
#import pudb
import logging
from random import randint

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
        self.has_associated_inner = False
        self.iou = {}
        self.user = None
        self.warning = None

class Stats:
    def __init__ (self):
        self.image_list =  []
        self.user_list  =  []
        self.dir_list   =  []
        self.user_to_dir_map    = defaultdict(str)
        self.dir_to_user_map    = defaultdict(str)
        self.image_to_class_map = defaultdict(list)
        self.ref_user_map       = defaultdict(defaultdict)


class BboxList:
    def __init__(self):
        self.bbox_obj_list = []
        # after every update to bbox_obj_list , stats needs to be regenerated
        self.stats = Stats()


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

    # prine list based on visible_users dict
    # TODO: check that Stats has been run and db is not dirty
    def filter_visible_users(self, bbox_obj_list, visible_users):
        items = []
        for item in bbox_obj_list:
            if visible_users[item.user]:
                items.append(item)
        return items

    def filter_by_iou_value(self, bbox_obj_list, ref_user, iou_filter_value):
        items = []
        iou_threshold = iou_filter_value / 10.0
        for item in bbox_obj_list:
            if item.user != ref_user:
                #logging.info(f"iou = ref_user = {ref_user} list = {item.iou}")
                if item.iou[ref_user] < iou_threshold: 
                    items.append(item)
        return items

    def update_stats(self):
        self.stats.image_list  = self.get_image_list()
        self.stats.user_to_dir_map, self.stats.dir_to_user_map    = self.get_user_map()
        self.stats.user_list   = self.stats.user_to_dir_map.keys()
        self.stats.dir_list    = self.stats.dir_to_user_map.keys()
        self.stats.image_to_class_map = self.get_image_to_class_map()
        self.update_user_key_in_objects()

    def get_image_list(self):
        """
        return list of images in all annotations
        """
        image_map = defaultdict(lambda: 0)
        for obj in self.bbox_obj_list:
            image_map[obj.image] += 1
        logging.info(f" number of images = {image_map}")
        return image_map.keys()

    def get_user_map(self):
        """
        return tail part of dir (if it's unique)
        """
        # first get list of dirs
        dir = []
        for obj in self.bbox_obj_list:
            dir.append(obj.dir)
        dir = sorted(set(dir))
        user_to_dir_map = self.get_min_path_to_make_unique(dir)
        logging.info(f" user_to_dir_map = {user_to_dir_map}")
        #import pdb; pdb.set_trace()

        dir_to_user_map = defaultdict(str)
        for user,d  in user_to_dir_map.items():
            dir_to_user_map[d] = user

        logging.info(f" map = {dir_to_user_map}")
        return user_to_dir_map, dir_to_user_map


    def get_min_path_to_make_unique(self, dir):

        # what is the longest number of paths in any dir?
        # need to deal with mixed slash paths (cygwin?)

        # count from tail up each dir path..assuming all paths are really about the same
        i = 0
        while True:
            i += 1
            dir_map = defaultdict(lambda: 0)
            for d in dir:
                d = d.replace(os.path.sep,'/')
                tail_list = d.split('/')[-i:]
                tail_str  = '_'.join(tail_list)
                tail_srr  = tail_str.replace(" ", "_")
                logging.info(f" trying {i} tail = {tail_str} for path = {d}")
                dir_map[tail_str] = d
            if len(dir_map) == len(dir):
                return dir_map

    def update_user_key_in_objects(self):
        """
        loop through all objects adding the user attribute
        """
        for obj in self.bbox_obj_list:
            obj.user = self.stats.dir_to_user_map[obj.dir]

    def get_best_ref_user(self, image, class_base):
        ref_user = self.stats.ref_user_map[image][class_base]
        #logging.info(f" ref_user = {ref_user} for {image} {class_base}")
        return ref_user


    def get_image_to_class_map(self):
        """
        active classs in each image
        """
        image_to_class_map = defaultdict(list)
        for obj in self.bbox_obj_list:
            image_to_class_map[obj.image].append(obj.class_base)

        for image in image_to_class_map.keys():
            image_to_class_map[image] = sorted(set(image_to_class_map[image]))

        logging.info(f" image_to_class_map= {image_to_class_map}")
        return image_to_class_map

    def associate_stem_with_outer(self):
        """
        each outer should have corresponding stem
        """
        for obj in self.bbox_obj_list:
            if obj.class_type == 'outer':
                logging.info(f"box is outer = {obj}")
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
            logging.info(f"WARNING: no meristem found for {obj_src.bbox}")
            min_obj = None
        else:
            min_dist = round(min_dist)
            obj_src.has_associated_inner = True

        obj_src.meristem = min_obj

    def compute_iou_for_each_annotation(self):
        """
        compute the iou of each class against one another
        """

        # pass1 : select ref_user based on image with most annotations for a class
        # ref_user[image][class_base]

        num_annotations  =  DeepDict(DeepDict(DeepDict(DeepDict((lambda: 0)))))
        max_annotation   =  DeepDict(DeepDict((lambda: 0)))

        # pass1: for each image/class_base find num of annotations and record ref_user
        for obj in self.bbox_obj_list:
            num_annotations[obj.user][obj.image][obj.class_base][obj.class_type] += 1
                
        for user in num_annotations:
            for image in num_annotations[user]:
                for class_base in num_annotations[user][image]:
                    # count all class_types
                    n = 0
                    for class_type in num_annotations[user][image][class_base]:
                        n +=  num_annotations[user][image][class_base][class_type]
                    if n > max_annotation[image][class_base]:
                        max_annotation[image][class_base] = n
                        self.stats.ref_user_map[image][class_base] = user
            #logging.info(f"ref user= {self.stats.ref_user_map}")

        # pass2: compute iou for each box relative to all others
        for obj_src in self.bbox_obj_list:

            # not matching dir, but matching image/class
            tgt_all_obj_list = self.filter(self.bbox_obj_list, 
                            image      = obj_src.image, 
                            class_base = obj_src.class_base,
                            class_type = obj_src.class_type)
            for user in self.stats.user_list: 
                if user == obj_src.user:
                    continue
                tgt_obj_list = self.filter(tgt_all_obj_list, user = user )
                #logging.info(f" checking filter for {user} filter for list= {tgt_obj_list}")
                obj_src.iou[user], _ = self.compute_iou_obj_list(obj_src, tgt_obj_list)
            #logging.info(f" iou for {obj_src} is {obj_src.iou}")


    def compute_iou_obj_list(self, obj_src, tgt_obj_list):
        """
        compute the intersection over union between obj_src and tgt_obj_list, returning the max value
        """
        iou_max = 0
        max_iou_userclass = None
        for obj_tgt in tgt_obj_list:
            iou = self.compute_iou_bbox_pair(obj_src.bbox, obj_tgt.bbox)
            if iou > iou_max:
                iou_max = iou
                max_iou_userclass = f"{obj_tgt.class_base} by {obj_tgt.user}"

        iou_max = round(iou_max,2)
        #logging.info(f"box_src={obj_src.bbox} bbox_list={tgt_obj_list} iou_max={iou_max}")
        return iou_max, max_iou_userclass

                        


    def compute_iou_bbox_pair(self, bbox_src, bbox_tgt):
        """
        compute Intersection-over-Union between 2 boxes
        """
        if not bbox_tgt:
            return 0


        xmin_src, ymin_src, xmax_src, ymax_src = bbox_src
        xmin_tgt, ymin_tgt, xmax_tgt, ymax_tgt = bbox_tgt
        x_overlap = max(0, min(xmax_src, xmax_tgt) - max(xmin_src, xmin_tgt))
        y_overlap = max(0, min(ymax_src, ymax_tgt) - max(ymin_src, ymin_tgt))
        intersection = x_overlap * y_overlap

        area_src = (xmax_src - xmin_src) * (ymax_src - ymin_src)
        area_tgt = (xmax_tgt - xmin_tgt) * (ymax_tgt - ymin_tgt)
        union = area_src + area_tgt - intersection

        iou = intersection / float(union)
        #logging.info(f"bbox_src={bbox_src} bbox_tgt={bbox_tgt} iou={intersection}/{union} = {iou}")

        return iou


    # ok, now for the higher order error detection
    def locate_potential_mislabel(self):

        # for any outer box with less than 0.3 score but would be 0.6 in another class
        iou_threshold = {}
        iou_threshold['same_class'] = 0.2 
        iou_threshold['diff_class'] = 0.5 

        obj_list = self.filter(self.bbox_obj_list,  class_type = 'outer')

        for image in self.stats.image_list:
            obj_list_f = self.filter(obj_list,  image = image)
            for obj in obj_list_f:

                max_iou_same = max(obj.iou.values())
                if max_iou_same < iou_threshold['same_class']:
                    obj_list_f = self.rfilter(obj_list_f, class_base = obj.class_base)
                    max_iou_diff, max_iou_userclass = self.compute_iou_obj_list(obj, obj_list_f)
                    if max_iou_diff > iou_threshold['diff_class']:
                        # potential mis-label!
                        obj.warning = f"\n{obj.class_base} by {obj.user}\n{max_iou_userclass}"
                        logging.info(obj.warning)
            
    
