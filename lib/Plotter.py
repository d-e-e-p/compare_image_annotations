###########################################################################################
#                                                                                         #
# Plotter
#                                                                                         #
###########################################################################################

import sys
import collections
from PIL import Image, ImageDraw, ImageFont
from os.path import exists



class Plotter:
    def plot_iou_boxes(self, run_txt, save_path, image_path, iou_data, IOU_threshold=0.5):
        """

        """
        # find all images and class per image
        image_name_to_class = collections.defaultdict(set)
        for item in iou_data:
             iou_value, image_name, cls, golden_box, revised_box = item
             image_name_to_class[image_name].add(cls)

        source_img = dict()
        for image_name, class_list in image_name_to_class.items():        
            file_name = f"{image_path}/{image_name}.jpg"
            if (exists(file_name)):
                source_img[image_name] = Image.open(file_name)
            else:
                print(f"Warning-image file missing: {file_name}")

        # expand images and add info
        #import pdb; pdb.set_trace()

        margin_x = 100
        margin_y = 200
        for image_name in source_img.keys():
            source_img[image_name] = self.add_margin(source_img[image_name],0,margin_x,margin_y,0,(1, 1, 1))

   
        # create destination images
        #TODO: switch based on what is found
        try:
            fnt = ImageFont.truetype('Courier.ttc', 16)
        except OSError:
            try:
                fnt = ImageFont.truetype('courbd.ttf', 16)
            except OSError:
                fnt = ImageFont.truetype('FreeMono.ttf', 16)

        dest_img = dict()
        for image_name, class_list in image_name_to_class.items():        
            if image_name in source_img:
                # sort + uniq
                classes = list(collections.OrderedDict.fromkeys(class_list))
                for cls in classes:
                    key = f"{image_name}_{cls}"
                    dest_img[key] = source_img[image_name].copy() 
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
