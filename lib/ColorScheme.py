
#
# use palettable
# 
#

import palettable

class ColorScheme():


    def __init__ (self):
        self.pallet =  palettable.cartocolors.qualitative
        self.names_and_lengths = getattr(self.pallet, '_NAMES_AND_LENGTHS')
        self.palletname_list    = self.get_list_of_palletnames()

    def get_list_of_palletnames(self):

        palletname_list = []
        for name, _ in self.names_and_lengths:
            if name not in palletname_list:
                palletname_list.append(name)

        for name, _ in self.names_and_lengths:
            name += "_reverse"
            if name not in palletname_list:
                palletname_list.append(name)

        return palletname_list

    def get_colors_for_pallet(self, palletname , size_requested):

        key = palletname.split('_')[0]
           
        size_list = []
        for name, size in self.names_and_lengths:
            if key == name:
                size_list.append(size)

        size_granted =  self.closest(size_list, size_requested)
        key += f"_{size_granted}"

        # assume after _ it means reverse
        if len(palletname.split('_')) > 1:
            key += "_r"

        map = getattr(self.pallet, key)
        col =  getattr(map, 'hex_colors')
        return col

    # https://www.geeksforgeeks.org/python-find-closest-number-to-k-in-given-list/
    def closest(self, lst, K):
        return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]
      
