
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
        col = ['#fa8174', '#81b1d2', '#bc82bd', '#ccebc4', '#ffed6f']
        col = ['#fa8174', '#81b1d2', '#fdb462', '#b3de69', '#bc82bd']
        col = ['#FFA700', '#FFF700', '#32CD32']
        col = "#c8a999  #bdc0c8  #00fdc2  #8caeff  #00ff00  #ff9248  #f97eff  #ffe7a1  #ff908e".split()
        col = ['#B0BF1A', '#3DDC84', '#FF91AF', '#66FF00', '#FFAA1D'] # de=21
        col = """
#10E7FC
#FFB9FF
#B2FF18
#F3FF12
#FFC81C
#17FF57
""".split()
        return col

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
      
