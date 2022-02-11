
"""

for outer:
        rgb L H S name
      	["#41faa5",     95,   152,  0.95,          "Hyperpop Green"]    
      	["#0bf507",     94,   119,  0.94,       "Free Speech Green"],   
      	["#f3e9e9",     94,     0,  0.29,         "Mont Blanc Peak"],   
      	["#f9d23c",     90,    48,  0.94,                   "Daisy"],   
      	["#eaa7f7",     83,   290,  0.83,              "Pink Sugar"],   
      	["#faa57d",     81,    19,  0.93,            "Sunset Peach"],   
      	["#79b510",     73,    82,  0.84,           "Green Serpent"],   
      	["#f85f8d",     72,   342,  0.92,               "Rosy Pink"],   
      	["#0ba4f0",     72,   200,  0.91,             "Button Blue"],   
      	["#f407f7",     71,   299,  0.94,            "Piquant Pink"],   
        ["#69b497",     71,   157,  0.33,               "Sainsbury"],   
      	["#f95c0a",     71,    21,  0.95,        "Willpower Orange"],   

for inner:
    "12": [
		["#030826",     4,   231,  0.85,       "Mysterious Depths"],      
		["#1e0f04",     6,    25,  0.76,                "Used Oil"],      
		["#12094d",    10,   248,  0.79,             "Magic Whale"],      
		["#3c0222",    12,   327,  0.94,            "Vienna Roast"],      
		["#0c2507",    13,   110,  0.68,              "Nori Green"],      
		["#480508",    16,   357,  0.87,          "Bulgarian Rose"],      
		["#0a273a",    16,   204,  0.71,         "Midnight Dreams"],      
		["#361d2f",    16,   317,  0.30,              "Sitter Red"],      
		["#382007",    16,    31,  0.78,          "Powdered Cocoa"],      
		["#14204d",    17,   227,  0.59,               "Dark Soul"],      
		["#450540",    17,   305,  0.86,                "Eggplant"],      
		["#05087c",    19,   238,  0.92,               "Navy Blue"]       


"""

PLANT_NAMES = """
    carrot
    carrot_seedling
    spinach
    grass
    mallow
    nettle
    pigweed
    purslane
    shepherds_purse
    weed_other
    unknown
""".split()

TYPE_NAMES = """
    outer
    stem
""".split()


def get_plan_type_names():
    names = []
    for plant in PLANT_NAMES:
        for type in TYPE_NAMES:
            names.append(f"{plant}_{type}")
    return names

PLANT_TYPE_NAMES = get_plan_type_names()


PLANT_COLORS = {
    'carrot_outer'                :	"#41faa5",
    'carrot_seedling_outer'       :	"#0bf507",
    'spinach_outer'               :	"#0bf507",      # repeat!
    'reserved_crop_outer'         : "#79b510",
    'grass_outer'                 :	"#f9d23c",
    'mallow_outer'                :	"#eaa7f7",
    'nettle_outer'                :	"#faa57d",
    'pigweed_outer'               :	"#f3e9e9",
    'purslane_outer'              :	"#f85f8d",
    'shepherds_purse_outer'       :	"#0ba4f0",
    'weed_other_outer'            :	"#f407f7",
    'unknown_outer'               :	"#f95c0a",
    'reserved_outer'              :	"#69b497",

    'carrot_stem'                 :	"#030826",
    'carrot_seedling_stem'        :	"#1e0f04",
    'spinach_stem'                :	"#12094d",
    'grass_stem'                  :	"#3c0222",
    'mallow_stem'                 :	"#0c2507",
    'nettle_stem'                 :	"#480508",
    'pigweed_stem'                :	"#0a273a",
    'purslane_stem'               :	"#361d2f",
    'shepherds_purse_stem'        :	"#382007",
    'weed_other_stem'             :	"#14204d",
    'unknown_stem'                :	"#450540",
    'reserved_stem'               :	"#05087c",
}

def has_valid_suffix(text):
    matches = TYPE_NAMES
    if any(x in text for x in matches):
        return True
    else:
        return False

def split_name_into_plant_and_type(name):

    if has_valid_suffix(name):
        plant, type = name.rsplit('_', 1)
    else:
        plant, type = name, "outer"
        logging.WARNING(f"name missing valid type suffix: {name}")
    return plant, type


