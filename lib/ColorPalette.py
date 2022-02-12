
#
# switch colors based on :
#   number of entries
#   dark/light/mid background
# 
#

from json_tricks import loads
import logging
from os.path import exists, join, isdir, isfile, dirname, abspath
import sys

class ColorPalette():


    def __init__ (self):
        json_file = "resources/json/rgb_70_to_100_color_list.json"
        self.num2colors  = self.read_json_file(json_file)

    def get_app_dir(self):
        """
        https://stackoverflow.com/questions/404744/determining-application-path-in-a-python-exe-generated-by-pyinstaller
        """
        if getattr(sys, 'frozen', False):
            application_path = sys._MEIPASS
        else:
            application_path = dirname(abspath(__file__))
        return application_path


    def read_json_file(self, filename):
        dir = self.get_app_dir()
        filename = join(dir,filename)
        logging.debug(f"read json {filename}")
        if not exists(filename):
            logging.error(f" json file missing : {filename}")
            sys.exit(-1)

        with open(filename,"r+") as f:
            json = f.read()
        items = loads(json)
        return items

    def get_list_of_themes(self):
        return "light dark".split()

    def get_colors_for_palette(self, theme , size_requested):
        size_available = [int(k) for k in self.num2colors.keys()]
        size_granted   =  self.closest(size_available, size_requested)
        col =  self.num2colors[str(size_granted)]
        return col

    # https://www.geeksforgeeks.org/python-find-closest-number-to-k-in-given-list/
    def closest(self, lst, K):
        return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]
      
