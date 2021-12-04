
#from : https://github.com/nagix/chartjs-plugin-colorschemes

class ColorSchemeTableau():

    def __init__ (self):
  
        self.color_schemes = {

	'Tableau10' : ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC'],
	'Tableau20' : ['#4E79A7', '#A0CBE8', '#F28E2B', '#FFBE7D', '#59A14F', '#8CD17D', '#B6992D', '#F1CE63', '#499894', '#86BCB6', '#E15759', '#FF9D9A', '#79706E', '#BAB0AC', '#D37295', '#FABFD2', '#B07AA1', '#D4A6C8', '#9D7660', '#D7B5A6'],
	'ColorBlind10' : ['#1170aa', '#fc7d0b', '#a3acb9', '#57606c', '#5fa2ce', '#c85200', '#7b848f', '#a3cce9', '#ffbc79', '#c8d0d9'],
	'SeattleGrays5' : ['#767f8b', '#b3b7b8', '#5c6068', '#d3d3d3', '#989ca3'],
	'Traffic9' : ['#b60a1c', '#e39802', '#309143', '#e03531', '#f0bd27', '#51b364', '#ff684c', '#ffda66', '#8ace7e'],
	'MillerStone11' : ['#4f6980', '#849db1', '#a2ceaa', '#638b66', '#bfbb60', '#f47942', '#fbb04e', '#b66353', '#d7ce9f', '#b9aa97', '#7e756d'],
	'SuperfishelStone10' : ['#6388b4', '#ffae34', '#ef6f6a', '#8cc2ca', '#55ad89', '#c3bc3f', '#bb7693', '#baa094', '#a9b5ae', '#767676'],
	'NurielStone9' : ['#8175aa', '#6fb899', '#31a1b3', '#ccb22b', '#a39fc9', '#94d0c0', '#959c9e', '#027b8e', '#9f8f12'],
	'JewelBright9' : ['#eb1e2c', '#fd6f30', '#f9a729', '#f9d23c', '#5fbb68', '#64cdcc', '#91dcea', '#a4a4d5', '#bbc9e5'],
	'Summer8' : ['#bfb202', '#b9ca5d', '#cf3e53', '#f1788d', '#00a2b3', '#97cfd0', '#f3a546', '#f7c480'],
	'Winter10' : ['#90728f', '#b9a0b4', '#9d983d', '#cecb76', '#e15759', '#ff9888', '#6b6b6b', '#bab2ae', '#aa8780', '#dab6af'],
	'GreenOrangeTeal12' : ['#4e9f50', '#87d180', '#ef8a0c', '#fcc66d', '#3ca8bc', '#98d9e4', '#94a323', '#c3ce3d', '#a08400', '#f7d42a', '#26897e', '#8dbfa8'],
	'RedBlueBrown12' : ['#466f9d', '#91b3d7', '#ed444a', '#feb5a2', '#9d7660', '#d7b5a6', '#3896c4', '#a0d4ee', '#ba7e45', '#39b87f', '#c8133b', '#ea8783'],
	'PurplePinkGray12' : ['#8074a8', '#c6c1f0', '#c46487', '#ffbed1', '#9c9290', '#c5bfbe', '#9b93c9', '#ddb5d5', '#7c7270', '#f498b6', '#b173a0', '#c799bc'],
	'HueCircle19' : ['#1ba3c6', '#2cb5c0', '#30bcad', '#21B087', '#33a65c', '#57a337', '#a2b627', '#d5bb21', '#f8b620', '#f89217', '#f06719', '#e03426', '#f64971', '#fc719e', '#eb73b3', '#ce69be', '#a26dc2', '#7873c0', '#4f7cba'],
	'OrangeBlue7' : ['#9e3d22', '#d45b21', '#f69035', '#d9d5c9', '#77acd3', '#4f81af', '#2b5c8a'],
	'RedGreen7' : ['#a3123a', '#e33f43', '#f8816b', '#ced7c3', '#73ba67', '#44914e', '#24693d'],
	'GreenBlue7' : ['#24693d', '#45934d', '#75bc69', '#c9dad2', '#77a9cf', '#4e7fab', '#2a5783'],
	'RedBlue7' : ['#a90c38', '#e03b42', '#f87f69', '#dfd4d1', '#7eaed3', '#5383af', '#2e5a87'],
	'RedBlack7' : ['#ae123a', '#e33e43', '#f8816b', '#d9d9d9', '#a0a7a8', '#707c83', '#49525e'],
	'GoldPurple7' : ['#ad9024', '#c1a33b', '#d4b95e', '#e3d8cf', '#d4a3c3', '#c189b0', '#ac7299'],
	'RedGreenGold7' : ['#be2a3e', '#e25f48', '#f88f4d', '#f4d166', '#90b960', '#4b9b5f', '#22763f'],
	'SunsetSunrise7' : ['#33608c', '#9768a5', '#e7718a', '#f6ba57', '#ed7846', '#d54c45', '#b81840'],
	'OrangeBlueWhite7' : ['#9e3d22', '#e36621', '#fcad52', '#ffffff', '#95c5e1', '#5b8fbc', '#2b5c8a'],
	'RedGreenWhite7' : ['#ae123a', '#ee574d', '#fdac9e', '#ffffff', '#91d183', '#539e52', '#24693d'],
	'GreenBlueWhite7' : ['#24693d', '#529c51', '#8fd180', '#ffffff', '#95c1dd', '#598ab5', '#2a5783'],
	'RedBlueWhite7' : ['#a90c38', '#ec534b', '#feaa9a', '#ffffff', '#9ac4e1', '#5c8db8', '#2e5a87'],
	'RedBlackWhite7' : ['#ae123a', '#ee574d', '#fdac9d', '#ffffff', '#bdc0bf', '#7d888d', '#49525e'],
	'OrangeBlueLight7' : ['#ffcc9e', '#f9d4b6', '#f0dccd', '#e5e5e5', '#dae1ea', '#cfdcef', '#c4d8f3'],
	'Temperature7' : ['#529985', '#6c9e6e', '#99b059', '#dbcf47', '#ebc24b', '#e3a14f', '#c26b51'],
	'BlueGreen7' : ['#feffd9', '#f2fabf', '#dff3b2', '#c4eab1', '#94d6b7', '#69c5be', '#41b7c4'],
	'BlueLight7' : ['#e5e5e5', '#e0e3e8', '#dbe1ea', '#d5dfec', '#d0dcef', '#cadaf1', '#c4d8f3'],
	'OrangeLight7' : ['#e5e5e5', '#ebe1d9', '#f0ddcd', '#f5d9c2', '#f9d4b6', '#fdd0aa', '#ffcc9e'],
    }

    def get_color_schemes(self):
        return self.color_schemes.keys()

    def get_colors_list(self, scheme):
        return self.color_schemes[scheme]


