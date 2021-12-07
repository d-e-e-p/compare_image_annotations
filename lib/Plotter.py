###########################################################################################
#                                                                                         #
# Plotter
#                                                                                         #
###########################################################################################

import sys
from collections import defaultdict, OrderedDict
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from os.path import exists, join
import logging
import io
import math
from random import choice, randint

from lib.Bbox   import Bbox, DeepDict
from lib.Bbox   import BboxList
from lib.ColorScheme import ColorScheme


import pudb

class DrawObject(object):
    def __init__(self, image, class_base, ref_user, visible_types, visible_users, iou_filter_value,
            color_pallet, adjust_background, adjust_foreground):
        self.image = image
        self.class_base = class_base
        self.ref_user = ref_user
        self.visible_types = visible_types
        self.visible_users = visible_users
        self.iou_filter_value = iou_filter_value
        self.color_pallet  = color_pallet
        self.adjust_background  = adjust_background
        self.adjust_foreground  = adjust_foreground
        self.overlay_stats =  DeepDict(DeepDict((lambda: 0)))


    # yeah not reccomended but works in this case...
    def __eq__(self, other): 

        if not isinstance(other, DrawObject):
            return False

        for attr in self.__dict__ :
            if getattr(self, attr) != getattr(other, attr):
                return False

        return True


    def __str__(self):
        return f"i={self.image} c={self.class_base} ru={self.ref_user} vt={self.visible_types} vu={self.visible_users} cs={self.color_pallet} ab={self.adjust_background} af={self.adjust_foreground}"

class Plotter:
    def __init__(self, bbl, img_dir, out_dir):

        self.bbl = bbl
        self.margin_x = 100
        self.margin_y = 200
        self.color_scheme  = ColorScheme()
        self.color_pallet  = "Bold" # initial pallet
        self.user_to_color = {}
        self.source_img = defaultdict(lambda: None)
        self.img_list = bbl.get_image_list();
        self.read_images(img_dir)
        self.add_margins()
        self.assign_colors_to_users()
        self.fnt = self.get_font();
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
                logging.error(f" image file missing: expecting {file_name}")
                exit(-1)

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

        logging.info(f" - color_pallet = {self.color_pallet}") 
        num_users = len(self.bbl.stats.user_list)
        color_list = self.color_scheme.get_colors_for_pallet(self.color_pallet, num_users)
        logging.info(f" color_list = {color_list}")

        # cycle thru color_list is num_users > color_list
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
                    img1.multiline_text((10,height-self.margin_y), txt , font=self.fnt, fill=(255, 255, 255))

        # loop thru all boxes and draw them on dest
        #fnt = ImageFont.truetype('cour.ttf', 14)
        for obj in bbl.bbox_obj_list:
            key = f"{obj.image}_{obj.class_base}_{obj.class_type}"
            if key in dest_img:
                img1 = ImageDraw.Draw(dest_img[key])
                img1.rounded_rectangle(obj.bbox, radius=10, fill=None, outline=(0,255,0,128), width=2)
                ref_user = bbl.get_best_ref_user(obj.image, obj.class_base)
                if ref_user != obj.user:
                    iou_value = obj.iou[ref_user]
                    txt = f"iou={iou_value:.2f}"
                    x1, y1, x2, y2 = obj.bbox
                    img1.text((x1+10,y1+10), txt , font=self.fnt, fill=(0, 0, 0))
                #img1.rounded_rectangle(revised_box, radius=10, fill=None, outline=(255,0,0,128), width=2)

        # save destination images
        for key in dest_img.keys():
            file_name = f"{out_dir}/{key}.jpg"
            dest_img[key].save(file_name)
        

    def fetch_overlay_image(self, dset):
       
        # what's the size of thie image?
        width, height = self.source_img[dset.image].size
        imgobj = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        # pad with margin
        #imgobj = self.add_margin(imgobj,0,0,self.margin_y,0,(1, 1, 1))
        img = ImageDraw.Draw(imgobj)

        # draw a black rectangle on gutters
        bbox = [0, height - self.margin_y, width, height]
        img.rectangle(bbox, fill='black', outline='white', width=1)

        bbox = [width - self.margin_x, height - self.margin_y , width, 0]
        img.rectangle(bbox, fill='black', outline='white', width=1)


        # first filter based on matching image/class
        filter_criteria = {}
        filter_criteria['image']      = dset.image
        filter_criteria['class_base'] = dset.class_base
        obj_list = self.bbl.filter(self.bbl.bbox_obj_list, **filter_criteria)

        # now visible users only
        obj_list = self.bbl.filter_visible_users(obj_list, dset.visible_users)

        # if iou filter then prune here
        if dset.iou_filter_value < 10:
            obj_list = self.bbl.filter_by_iou_value(obj_list, dset.ref_user,  dset.iou_filter_value)


        # ok now update color pallet
        if self.color_pallet != dset.color_pallet:
            self.color_pallet = dset.color_pallet
            self.assign_colors_to_users()

        # reset stats
        dset.overlay_stats['outer_assoc']['associated'] = 0
        dset.overlay_stats['outer_assoc']['not_associated'] = 0
        
        # handle the 3 class_type: outer inner inout
        for class_type in self.bbl.stats.class_type_list:
            if class_type == 'inout':
                continue

            obj_list_f = self.bbl.filter(obj_list, class_type = class_type)
            self.collect_overlay_stats(dset, obj_list_f)
            if dset.visible_types[class_type]:
                self.draw_boxes_for_object(img, obj_list_f, dset.ref_user, class_type)
            # handle inout class type on 'outer' loop
            if class_type == 'outer' and dset.visible_types['inout']:
                self.draw_boxes_for_object(img, obj_list_f, dset.ref_user, 'inout')
        


        # draw a key on top left
        self.draw_left_legend_for_overlay(img, dset)
        self.draw_right_legend_for_overlay(img, dset)

        # factor : 0.5 darkens to 1.5 lightens:  adjust_foreground is from 0 to 10
        # map a number from 0 to 10 to 0.5 to 1.5
        factor =  (dset.adjust_foreground / 5.0) 
        enhancer = ImageEnhance.Brightness(imgobj)
        imgobj = enhancer.enhance(factor)

        bytes_img = io.BytesIO()
        imgobj.save(bytes_img, format='PNG')
        return bytes_img.getvalue()

    def get_text_for_report_line(self, ref_user, iou_min, iou_max, u_count, user):

        txt = f" {iou_min:.2f}\t{iou_max:.2f}\t"
        for class_type in self.bbl.stats.class_type_list:
            txt += f"{u_count[class_type]}\t"
        txt += f"{user}"
        txt = txt.replace("-inf"," -  ")
        txt = txt.replace("inf", " -  ")
        txt = txt.expandtabs(4)
        if user == ref_user:
            txt += " <--REF"
        return txt

    def draw_box_text(self, img, txt, xloc, yloc, cell_width, cell_height, linespace, color, width):
        img.text((xloc,yloc), txt , font=self.fnt, fill=color)
        yloc -= (linespace - cell_height)/2
        bbox = [xloc, yloc, xloc + cell_width, yloc + linespace]
        img.rounded_rectangle(bbox, radius=2, fill=None, outline=color, width=width)

    def draw_right_legend_for_overlay(self, img, dset):
        """
        a table of shown values
        """
        width, height = self.source_img[dset.image].size

        # find longest name user and assume user is ref
        max_username = max(dset.visible_users.keys())
        u_count =  defaultdict(lambda: 0)
        txt = self.get_text_for_report_line(max_username, 0, 0, u_count, max_username)
        cell_width, cell_height = img.textsize(txt, self.fnt)
        max_txt_len = len(txt) # needed much later

        # ok, now compute total needed space based on that
        linespace = 1.5 * cell_height

        num_visible_users = sum(dset.visible_users.values())
        nun_lines_extra = 2
        num_lines = num_visible_users + nun_lines_extra

        xspace_needed = cell_width
        yspace_needed = num_lines * linespace

        xloc = width - xspace_needed - self.margin_x / 2
        yloc = height - cell_height


        # bottom up
        v_users = sorted(dset.visible_users.keys(), reverse=True)
        for user in v_users:
            if dset.visible_users[user]:
                yloc -= linespace
                color = self.user_to_color[user]

                iou_min = dset.overlay_stats['iou_min'][user]
                iou_max = dset.overlay_stats['iou_max'][user]
                u_count =  defaultdict(lambda: 0)
                for class_type in self.bbl.stats.class_type_list:
                    userclass = f"{user}_{class_type}"
                    u_count[class_type] = dset.overlay_stats['userclass'][userclass]

                #logging.info(f"tats_count = {dset.overlay_stats['userclass']}")
                #logging.info(f"u_count = {u_count}")
                txt = self.get_text_for_report_line(dset.ref_user, iou_min, iou_max, u_count, user)
                logging.info(f"txt={txt}")
                self.draw_box_text(img, txt, xloc, yloc, cell_width, cell_height, linespace, color, 1)


        # banner
        yloc -= linespace
        txt = f"iou_min iou_max (out, in, inout) count  user"
        txt = txt.expandtabs(4)
        color = 'white'
        logging.info(f"txt={txt}")
        self.draw_box_text(img, txt, xloc, yloc, cell_width, cell_height, linespace, color, 1)



    def draw_left_legend_for_overlay(self, img, dset):
        """
        tile and stuff
        """
        width, height = self.source_img[dset.image].size
        xloc = 100
        yloc = height - self.margin_y 
        header_txt = f"{dset.class_base} on {dset.image}"
        underline_txt = '-' * len(header_txt)


        txt = f"""

    {header_txt}
    {underline_txt}
      Associated outer = {dset.overlay_stats['outer_assoc']['associated']}  
      Floating outer   = {dset.overlay_stats['outer_assoc']['not_associated']}  
"""
        color = 'white'
        img.multiline_text((xloc,yloc), txt , font=self.fnt, fill=color)




    # look thru boxes counting user/type stats
    def collect_overlay_stats(self, dset, obj_list):


        for obj in obj_list:
            # fist mark class_types
            userclass = f"{obj.user}_{obj.class_type}"
            dset.overlay_stats['userclass'][userclass] += 1
            userclass = f"{obj.user}_total"
            dset.overlay_stats['userclass'][userclass] += 1

            dset.overlay_stats['class_type'][obj.class_type] += 1
            #if obj.class_type == 'outer':
            #    logging.info(f"count[{obj.class_type}] = {dset.overlay_stats['class_type'][obj.class_type]} bbox={obj.bbox}")

            # handle inout case when called as outer
            if obj.class_type == 'outer' and obj.has_associated_inner:
                userclass = f"{obj.user}_inout"
                dset.overlay_stats['userclass'][userclass] += 1
                dset.overlay_stats['class_type']['inout'] += 1
            
            if obj.class_type == 'outer':
                if obj.has_associated_inner:
                    dset.overlay_stats['outer_assoc']['associated'] += 1
                else:
                    dset.overlay_stats['outer_assoc']['not_associated'] += 1

        # reset from default 0 to inf
        for user in self.bbl.stats.user_list:
            dset.overlay_stats['iou_min'][user] = math.inf
            dset.overlay_stats['iou_max'][user] = -math.inf

        # get iou stats
        for obj in obj_list:
            user = obj.user
            if user != dset.ref_user:
                iou_value = obj.iou[dset.ref_user]
                if iou_value > dset.overlay_stats['iou_max'][user] :
                    dset.overlay_stats['iou_max'][user] = iou_value
                if iou_value < dset.overlay_stats['iou_min'][user] :
                    dset.overlay_stats['iou_min'][user] = iou_value
                #logging.info(f" iou[{dset.ref_user}] for {user} = {iou_value} min={ dset.overlay_stats['iou_min'][user]} max={dset.overlay_stats['iou_max'][user]}")

        logging.info(f" stats = {dset.overlay_stats}")
        #import pdb; pdb.set_trace()

                    

    def draw_boxes_for_object(self, img, obj_list, ref_user, type):

        # already removed all invalid boxes (non visible users etc)

        # inout lines don't need text or rect
        if type != "inout": 
            for obj in obj_list:
                color = self.user_to_color[obj.user]
                img.rounded_rectangle(obj.bbox, radius=10, fill=None, outline=color, width=2)

                if obj.user == ref_user:
                    txt = 'R'
                else:
                    iou_value = obj.iou[ref_user]
                    txt = f"iou={iou_value}"
                #logging.info(f" calc: user={user} ref={ref_user} iou = {obj.iou}")
                xloc, yloc = self.get_random_nearby_loc(obj.bbox);
                img.text((xloc,yloc), txt , font=self.fnt, fill=color)
                if obj.warning is not None:
                    txt = f"potential mis-label!\n{obj.warning}"
                    xloc, yloc = self.get_location_for_text(img, obj, txt)
                    img.text((xloc,yloc), txt , font=self.fnt, fill='red')

                # inout # mark difficult objects
                if obj.difficult:
                    xloc, yloc = self.get_random_nearby_loc(obj.bbox);
                    color = 'red'
                    img.text((xloc, yloc), 'D' , font=self.fnt, fill=color)

        # ok now handle the inout case
        else:
            logging.info(f" handling 'inout' case")
            for obj in obj_list:
                if obj.has_associated_inner :

                    color = self.user_to_color[obj.user]

                    # draw connector from stem to outer
                    x1o, y1o, x2o, y2o = obj.bbox
                    x1i, y1i, x2i, y2i = obj.meristem.bbox
                    shape = [(x1i, y1i), (x1o, y1o)] ; img.line(shape, fill=color, width = 2)
                    shape = [(x1i, y2i), (x1o, y2o)] ; img.line(shape, fill=color, width = 2)
                    shape = [(x2i, y2i), (x2o, y2o)] ; img.line(shape, fill=color, width = 2)
                    shape = [(x2i, y1i), (x2o, y1o)] ; img.line(shape, fill=color, width = 2)


    def get_location_for_text(self, img, obj, txt):
        """
        center text first, and then adjust of off screen
        """
        x1, y1, x2, y2 = obj.bbox
        xloc = (x1+x2) / 2
        yloc = (y1+y2) / 2
        width, height = self.source_img[obj.image].size
        textwidth, textheight = img.textsize(txt, self.fnt)
        xloc -= round(textwidth / 2)
        yloc -= round(textheight / 2)
        if xloc + textwidth > width:
            xloc = width - textwidth
        if yloc + textheight > height:
            yloc = height - textheight
        return xloc, yloc

    def get_random_nearby_loc(self, bbox):
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
        #logging.info(f" pil = {pil_img}")
        width, height = pil_img.size
        new_width = width + right + left
        new_height = height + top + bottom
        result = Image.new(pil_img.mode, (new_width, new_height), color)
        result.paste(pil_img, (left, top))
        return result
