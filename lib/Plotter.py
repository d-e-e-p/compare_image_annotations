###########################################################################################
#                                                                                         #
# Plotter
#                                                                                         #
###########################################################################################

import sys
from collections import defaultdict, OrderedDict
from PIL import Image, ImageDraw, ImageFont
from os.path import exists, join
import logging
import io
from random import choice, randint

from lib.Bbox   import Bbox
from lib.Bbox   import BboxList
from lib.ColorschemeTableau import ColorSchemeTableau


import pudb

class DrawObject(object):
    def __init__(self, image, class_base, ref_user, visible_outer, visible_inner , visible_users, color_scheme):
        self.image = image
        self.class_base = class_base
        self.ref_user = ref_user
        self.visible_outer = visible_outer
        self.visible_inner = visible_inner
        self.visible_users = visible_users
        self.color_scheme  = color_scheme

    def __eq__(self, other): 
        if  self.image         == other.image and         \
            self.class_base    == other.class_base and    \
            self.ref_user      == other.ref_user and      \
            self.visible_outer == other.visible_outer and \
            self.visible_inner == other.visible_inner and \
            self.visible_users == other.visible_users and \
            self.color_scheme  == other.color_scheme:
            return True 
    def __str__(self):
        return f"i={self.image} c={self.class_base} ru={self.ref_user} vo={self.visible_outer} vi={self.visible_inner} vu={self.visible_users} cs={self.color_scheme}"

class Plotter:
    def __init__(self, bbl, img_dir, out_dir):

        self.bbl = bbl
        self.margin_x = 100
        self.margin_y = 200
        self.color_scheme  = 'Tableau10'
        self.user_to_color = {}
        self.source_img = defaultdict(lambda: None)
        self.img_list = bbl.get_image_list();
        self.read_images(img_dir)
        self.add_margins()
        self.assign_colors_to_users()
        self.plot_iou_boxes(bbl, out_dir)

    # make sure all images exist in img_dir
    def read_images(self, img_dir):
        img_ext = ".jpg"
        for image in self.img_list:
            file_name = join(img_dir, image + img_ext)
            if (exists(file_name)):
                try:
                    self.source_img[image] = Image.open(file_name)
                except IOError:
                    logging.warning(f" image file not actually an image: {file_name}")

            else:
                logging.warning(f" image file missing: {file_name}")

    def add_margins(self):
        for image_name in self.img_list:
            self.source_img[image_name] = \
                    self.add_margin(self.source_img[image_name],0,self.margin_x,self.margin_y,0,(1, 1, 1))

    def get_font(self):
        #TODO: switch based on what is found
        try:
            fnt = ImageFont.truetype('Courier.ttc', 16)
        except OSError:
            try:
                fnt = ImageFont.truetype('courbd.ttf', 16)
            except OSError:
                try:
                    fnt = ImageFont.truetype('FreeMono.ttf', 16)
                except OSError:
                    try:
                        fnt = ImageFont.truetype('/c/Windows/Fonts/courbd.ttf', 16)
                    except OSError:
                        logging.error("Can't find any font")
                        raise Exception("font error")
        return fnt

    def assign_colors_to_users(self):

        logging.info(f" - color_scheme = {self.color_scheme}") 
        c = ColorSchemeTableau()
        color_list = c.get_colors_list(self.color_scheme)
        logging.info(f" color_list = {color_list}")

        i = 0
        for user in self.bbl.stats.user_list:
            self.user_to_color[user] = color_list[i]
            i += 1
            if i == len(color_list):
                i = 0


    def plot_iou_boxes(self, bbl, out_dir):
        """
        loop thru each image and any annotations on that image to create a report
        """
        fnt = self.get_font();

        # find all classes per image
        image_name_to_class = defaultdict(set)
        for obj in bbl.bbox_obj_list:
             class_name = f"{obj.class_base}_{obj.class_type}"
             image_name_to_class[obj.image].add(class_name)

        # create all destination images
        dest_img = dict()
        for image_name, class_list in image_name_to_class.items():
            if image_name in self.source_img:
                # sort + uniq
                classes = list(OrderedDict.fromkeys(class_list))
                for cls in classes:
                    key = f"{image_name}_{cls}"
                    dest_img[key] = self.source_img[image_name].copy() 
                    width, height = dest_img[key].size
                    txt = f"""
image = {image_name} class = {cls}
"""
                    img1 = ImageDraw.Draw(dest_img[key])
                    img1.multiline_text((10,height-self.margin_y), txt , font=fnt, fill=(255, 255, 255))

        # loop thru all boxes and draw them on dest
        #fnt = ImageFont.truetype('cour.ttf', 14)
        for obj in bbl.bbox_obj_list:
            key = f"{obj.image}_{obj.class_base}_{obj.class_type}"
            if key in dest_img:
                img1 = ImageDraw.Draw(dest_img[key])
                iou_value = obj.iou
                txt = f"iou={iou_value}"
                x1, y1, x2, y2 = obj.bbox
                img1.text((x1+10,y1+10), txt , font=fnt, fill=(0, 0, 0))
                img1.rounded_rectangle(obj.bbox, radius=10, fill=None, outline=(0,255,0,128), width=2)
                #img1.rounded_rectangle(revised_box, radius=10, fill=None, outline=(255,0,0,128), width=2)

        # save destination images
        for key in dest_img.keys():
            file_name = f"{out_dir}/{key}.jpg"
            dest_img[key].save(file_name)
        

    def fetch_overlay_image(self, dset):
       
        # what's the size of thie image?
        width, height = self.source_img[dset.image].size
        imgobj = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        #imgobj = Image.new('RGB', (width, height), ( 0, 0, 0))
        img = ImageDraw.Draw(imgobj)
        fnt = self.get_font();

        # first filter based on matching image/class
        filter_criteria = {}
        filter_criteria['image']      = dset.image
        filter_criteria['class_base'] = dset.class_base

        if dset.visible_outer and not dset.visible_inner:
            filter_criteria['class_type'] = 'outer'
        if not dset.visible_outer and dset.visible_inner:
            filter_criteria['class_type'] = 'meristem'
        # must be both on...both off wouldn't have reached this far

        # ok update color scheme
        if self.color_scheme != dset.color_scheme:
            self.color_scheme = dset.color_scheme
            self.assign_colors_to_users()


        obj_list = self.bbl.filter(self.bbl.bbox_obj_list, **filter_criteria)
        # only select boxes matching dset
        for obj in obj_list:
            user = self.bbl.stats.dir_to_user_map[obj.dir]

            if  dset.visible_users[user]:
                color = self.user_to_color[user]
                if user == dset.ref_user:
                    txt = 'R'
                else:
                    iou_value = obj.iou[dset.ref_user]
                    txt = f"iou={iou_value}"

                xloc, yloc = self.get_random_loc(obj.bbox);

                x1, y1, x2, y2 = obj.bbox
                img.text((xloc,yloc), txt , font=fnt, fill=color)
                img.rounded_rectangle(obj.bbox, radius=10, fill=None, outline=color, width=2)

        bytes_img = io.BytesIO()
        imgobj.save(bytes_img, format='PNG')
        return bytes_img.getvalue()

    def get_random_loc(self, bbox):
        """
        position labels in different places
        """
        range = 20
        x1, y1, x2, y2 = bbox
        xbase = choice([x1,x2])
        ybase = choice([y1,y2])
        xloc = xbase + randint(-range, range)
        yloc = ybase + randint(-range, range)
        return xloc, yloc


    # from https://note.nkmk.me/en/python-pillow-add-margin-expand-canvas/
    @staticmethod
    def add_margin(pil_img, top, right, bottom, left, color):
        width, height = pil_img.size
        new_width = width + right + left
        new_height = height + top + bottom
        result = Image.new(pil_img.mode, (new_width, new_height), color)
        result.paste(pil_img, (left, top))
        return result
