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

from lib.Bbox   import Bbox
from lib.Bbox   import BboxList


class Plotter:
    def __init__(self, bbl, img_dir, out_dir):

        self.margin_x = 100
        self.margin_y = 200
        self.source_img = defaultdict(lambda: None)
        self.img_list = bbl.get_image_list();
        self.read_images(img_dir)
        self.add_margins()
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

    def plot_iou_boxes(self, bbl, out_dir):
        """
        loop thru each image and any annotations on that image to create a report
        """
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
        


    def plot_iou_boxes2(self, run_txt, save_path, image_path, iou_data, IOU_threshold=0.5):
        """

        """
        # find all images and class per image
        image_name_to_class = defaultdict(set)
        for item in iou_data:
             iou_value, image_name, cls, golden_box, revised_box = item
             image_name_to_class[image_name].add(cls)

        self.source_img = dict()
        for image_name, class_list in image_name_to_class.items():        
            file_name = f"{image_path}/{image_name}.jpg"
            if (exists(file_name)):
                self.source_img[image_name] = Image.open(file_name)
            else:
                print(f"Warning-image file missing: {file_name}")

        # expand images and add info
        #import pdb; pdb.set_trace()


   
        # create destination images

        dest_img = dict()
        for image_name, class_list in image_name_to_class.items():        
            if image_name in self.source_img:
                # sort + uniq
                classes = list(OrderedDict.fromkeys(class_list))
                for cls in classes:
                    key = f"{image_name}_{cls}"
                    dest_img[key] = self.source_img[image_name].copy() 
                    width, height = dest_img[key].size
                    txt = run_txt + f"""
image = {image_name} class = {cls}
"""
                    img1 = ImageDraw.Draw(dest_img[key])
                    img1.multiline_text((10,height-margin_y), txt , font=fnt, fill=(255, 255, 255))

        # loop thru all boxes and draw them on dest
        #fnt = ImageFont.truetype('cour.ttf', 14)
        for item in iou_data:
            iou_value, image_name, cls, golden_box, revised_box = item
            key = f"{image_name}_{cls}"
            if key in dest_img:
                img1 = ImageDraw.Draw(dest_img[key])
                if not golden_box == '[missing]':
                   #img1.rounded_rectangle(golden_box, radius=10, fill=(0,255,0,1), outline=(0,255,0,200), width=2)
                   x1, y1, x2, y2 = golden_box
                   txt = f"iou={iou_value}"
                   img1.text((x1+10,y1+10), txt , font=fnt, fill=(0, 0, 0))
                   img1.rounded_rectangle(golden_box, radius=10, fill=None, outline=(0,255,0,128), width=2)

                if not revised_box == '[missing]':
                   #img1.rounded_rectangle(revised_box, radius=10, fill=(255,0,0,1), outline=(0,255,0,200), width=2)
                   img1.rounded_rectangle(revised_box, radius=10, fill=None, outline=(255,0,0,128), width=2)

        
        # save destination images
        for key in dest_img.keys():
            file_name = f"{save_path}/{key}.jpg"
            dest_img[key].save(file_name)





    # from https://note.nkmk.me/en/python-pillow-add-margin-expand-canvas/
    @staticmethod
    def add_margin(pil_img, top, right, bottom, left, color):
        width, height = pil_img.size
        new_width = width + right + left
        new_height = height + top + bottom
        result = Image.new(pil_img.mode, (new_width, new_height), color)
        result.paste(pil_img, (left, top))
        return result
