import pickle
import os
import sys


class Settings(object):
    def __init__(self):
        # Be default, the home will be in the same folder as labelImg
        home = os.path.expanduser("~")
        self.data = {}
        self.path = os.path.join(home, '.compare_image_annotations_settings.pkl')

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        return default

    def save(self):
        if self.path:
            print(f" saving window settings to :      {self.path}")
            with open(self.path, 'wb') as f:
                pickle.dump(self.data, f, pickle.HIGHEST_PROTOCOL)
                return True
        return False

    def load(self):
        try:
            if os.path.exists(self.path):
                print(f" restoring window settings from:  {self.path}")
                with open(self.path, 'rb') as f:
                    self.data = pickle.load(f)
                    return True
        except:
            print('Loading setting failed')
        return False

    def reset(self):
        if os.path.exists(self.path):
            os.remove(self.path)
            print(f" removed settings file {self.path}")
        self.data = {}
        self.path = None
