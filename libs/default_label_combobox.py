import sys
from PySide6.QtGui import QTextLine, QAction, QImage, QColor, QCursor, QPixmap, QImageReader
from PySide6.QtCore import QObject, Qt, QPoint, QSize, QByteArray, QTimer, QFileInfo, QPointF, QProcess
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QCheckBox, QLineEdit, QHBoxLayout, QWidget, QToolButton, \
    QListWidget, QDockWidget, QScrollArea, QWidgetAction, QMenu, QApplication, QLabel, QMessageBox, QFileDialog, \
    QListWidgetItem, QComboBox

class DefaultLabelComboBox(QWidget):
    def __init__(self, parent=None, items=[]):
        super(DefaultLabelComboBox, self).__init__(parent)

        layout = QHBoxLayout()
        self.cb = QComboBox()
        self.items = items
        self.cb.addItems(self.items)

        self.cb.currentIndexChanged.connect(parent.default_label_combo_selection_changed)

        layout.addWidget(self.cb)


        self.setLayout(layout)

class DefaultPlantComboBox(QWidget):
    def __init__(self, parent=None, items=[]):
        super(DefaultPlantComboBox, self).__init__(parent)

        layout = QHBoxLayout()
        self.cb = QComboBox()
        self.items = items
        self.cb.addItems(self.items)

        self.cb.currentIndexChanged.connect(parent.default_plant_combo_selection_changed)

        label = QLabel()
        label.setText("Plant:")
        layout.addWidget(label)

        layout.addWidget(self.cb)
        self.setLayout(layout)

class DefaultTypeComboBox(QWidget):
    def __init__(self, parent=None, items=[]):
        super(DefaultTypeComboBox, self).__init__(parent)

        layout = QHBoxLayout()
        self.cb = QComboBox()
        self.items = items
        self.cb.addItems(self.items)

        self.cb.currentIndexChanged.connect(parent.default_type_combo_selection_changed)

        label = QLabel()
        label.setText("Type:")
        #label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        label.setMinimumWidth(100)
        layout.addWidget(label)

        layout.addWidget(self.cb)
        self.setLayout(layout)
