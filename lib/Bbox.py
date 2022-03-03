"""
Bbox
"""
# from https://stackoverflow.com/questions/2600790/multiple-levels-of-collection-defaultdict-in-python
from collections import defaultdict
import os

class DeepDict(defaultdict):
    def __call__(self):
        return DeepDict(self.default_factory)

class Bbox:
    def __init__ (self, dir, file, image,  class_base, class_type, difficult, bbox):
        self.dir  = dir.replace(os.path.sep,'/')
        self.file = file
        self.image = image
        self.class_base = class_base
        self.class_type = class_type
        self.difficult  = difficult
        self.bbox = bbox
        self.meristem = None
        self.has_associated_inner = False
        self.iou = {}
        self.associated_user = defaultdict(float)
        self.user = None
        self.warning = None

    def __str__(self):
        return str(self.__dict__)
