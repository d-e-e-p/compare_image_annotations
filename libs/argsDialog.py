
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import *

BB = QDialogButtonBox


import logging

class Results():
    pass

class ArgsDialog(QDialog):

    def __init__(self, text="", parent=None, res=None ):
        super(ArgsDialog, self).__init__(parent)

        self.res = res
        self.res.args = None
        self.setWindowTitle("args for compare_image_annotations")
        self.resize(500,500)

        main_title = QLabel()
        main_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_title.setText("<center><h1>compare_image_annotations</h1></center>")

        title = QLabel('<b>Reports Folder:<\\b>')
        self.rpt_foldername  = QLineEdit()
        self.rpt_file_browse = QPushButton('Browse')
        self.rpt_file_browse.clicked.connect(self.rptFolderDialog)

        group1 = QGroupBox('')
        layout = QGridLayout()
        layout.addWidget(title, 0, 0)
        layout.addWidget(self.rpt_foldername, 1, 0, 1, 3)
        layout.addWidget(self.rpt_file_browse,1, 3, 1, 1)
        layout.setVerticalSpacing(0)
        group1.setLayout(layout)

        title = QLabel('<b>Data Folder (images and xml):</b>')
        self.data_foldername  = QLineEdit()
        self.data_file_browse = QPushButton('Browse')
        self.data_file_browse.clicked.connect(self.dataFolderDialog)

        group2 = QGroupBox('')
        layout = QGridLayout()
        layout.addWidget(title, 0, 0)
        layout.addWidget(self.data_foldername, 1, 0, 1, 3)
        layout.addWidget(self.data_file_browse,1, 3, 1, 1)
        layout.setVerticalSpacing(0)
        group2.setLayout(layout)


        self.group3 = QGroupBox('')
        title = QLabel('<b>Check level:</b>')
        radio1 = QRadioButton("relaxed")
        radio2 = QRadioButton("normal")
        radio3 = QRadioButton("strict")
        radio2.setChecked(True)

        vbox = QVBoxLayout()
        vbox.addWidget(title)
        vbox.addWidget(radio1)
        vbox.addWidget(radio2)
        vbox.addWidget(radio3)
        vbox.addStretch(1)
        self.group3.setLayout(vbox)

        group4 = QGroupBox('')
        title = QLabel('<b>Flags</b>')
        but1 = QCheckBox("prune (only consider xml with more than 1 version)")
        but1.setChecked(True)
        but2 = QCheckBox("verbose (print debug messages)")
        but2.setChecked(False)

        vbox = QVBoxLayout()
        vbox.addWidget(title)
        vbox.addWidget(but1)
        vbox.addWidget(but2)
        vbox.addStretch(1)
        group4.setLayout(vbox)

        bb = self.setButtonBox()

        main_layout = QVBoxLayout()
        main_layout.addWidget(main_title)
        main_layout.addWidget(group1)
        main_layout.addWidget(group2)
        main_layout.addWidget(self.group3)
        main_layout.addWidget(group4)
        main_layout.addWidget(bb)
        self.setLayout(main_layout)

    def validate(self):
        rpt_foldername  = self.rpt_foldername.text()
        data_foldername = self.data_foldername.text()
        args = ""
        args += f" --out '{rpt_foldername}' "
        args += f" --data '{data_foldername}' "
        for item in self.findChildren(QRadioButton):
            if item.isChecked():
                    args += f" --check {item.text()} "

        for item in self.findChildren(QCheckBox):
            if item.isChecked():
                if "prune" in item.text():
                    args += f" --prune "
                if "verbose" in item.text():
                    args += f" --verbose "

        logging.debug(f"args= {args}")
        self.res.args = args
        self.accept()


    def post_process(self):
        pass

    def rptFolderDialog(self):
        folder = str(QFileDialog.getExistingDirectory(self, "Select Reports Directory"))
        if folder == '':
            return None
        else:
            self.rpt_foldername.setText(folder)

    def dataFolderDialog(self):
        folder = str(QFileDialog.getExistingDirectory(self, "Select Reports Directory"))
        if folder == '':
            return None
        else:
            self.data_foldername.setText(folder)


    def setButtonBox(self):
        button_box = QDialogButtonBox()
        button_box.addButton("Run", QDialogButtonBox.AcceptRole)
        button_box.accepted.connect(self.validate)

        return button_box

