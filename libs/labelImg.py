#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import codecs
import distutils.spawn
import os.path
import platform
import re
import sys
import subprocess
import shutil
import webbrowser as wb
import logging
from enum import Enum
from pathlib import Path


import colorama
from colorama import Fore, Back, Style


import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from psutil import Process
from collections import Counter


from functools import partial
from collections import defaultdict

from lib.Bbox    import Bbox
from lib.Bbox    import BboxList
from lib.Plotter import Plotter, DrawObject
from lib.ColorPalette import ColorPalette

from PySide6.QtGui import QTextLine, QAction, QImage, QColor, QCursor, QPixmap, QImageReader, QFont, QPainter
from PySide6.QtCore import QObject, Qt, QPoint, QSize, QByteArray, QTimer, QFileInfo, QPointF, QProcess, QRect
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QCheckBox, QLineEdit, QHBoxLayout, QWidget, QToolButton, \
    QListWidget, QDockWidget, QScrollArea, QWidgetAction, QMenu, QApplication, QLabel, QMessageBox, QFileDialog, \
    QListWidgetItem, QGroupBox, QSlider, QDialog, QRubberBand, QComboBox

from libs.combobox import ComboBox
from libs.default_label_combobox import DefaultLabelComboBox, DefaultPlantComboBox, DefaultTypeComboBox
from libs.constants import *
from libs.resources import *
from libs.utils import (Struct, add_actions, format_shortcut, generate_color_by_text, 
                        natural_sort, new_action, new_icon)
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.stringBundle import StringBundle
from libs.canvas import Canvas
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.createNote import CreateNote
from libs.colorDialog import ColorDialog
from libs.labelFile import LabelFile, LabelFileError, LabelFileFormat
from libs.toolBar import ToolBar
from libs.pascal_voc_io import PascalVocReader
from libs.pascal_voc_io import XML_EXT
from libs.yolo_io import YoloReader
from libs.yolo_io import TXT_EXT
from libs.create_ml_io import CreateMLReader
from libs.create_ml_io import JSON_EXT
from libs.ustr import ustr
from libs.hashableQListWidgetItem import HashableQListWidgetItem
from libs.plantData import PLANT_NAMES, TYPE_NAMES, PLANT_TYPE_NAMES, PLANT_COLORS
from libs.plantData import split_name_into_plant_and_type

#__appname__ = 'labelImg'
__appname__ = 'compare_image_annotations'

class BarStats():
    pass

class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            add_actions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            add_actions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar


class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))
    class ZoomMode(Enum):
        FIT_WINDOW   = "fit_window"
        FIT_WIDTH    = "fit_width"
        MANUAL_ZOOM  = "manual_zoom"
        ZOOM_TO_AREA = "zoom_to_area"

    # TODO: split up _init into pieces..
    def __init__(self, bbl, pl,  default_filename=None, default_save_dir=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        default_prefdef_class_file=None

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        self.os_name = platform.system()
        self.username = get_username()

        self.bbl = bbl
        self.pl  = pl
        self.ref_user = None
        self.current_image = None
        self.current_draw_object = None
        self.iou_filter_value = 10

        # Load string bundle for i18n
        self.string_bundle = StringBundle.get_bundle()
        get_str = lambda str_id: self.string_bundle.get_string(str_id)

        # Save as Pascal voc xml
        self.default_save_dir = default_save_dir
        self.label_file_format = settings.get(SETTING_LABEL_FILE_FORMAT, LabelFileFormat.PASCAL_VOC)

        # For loading all image under a directory
        self.m_img_list = []
        self.dir_name = None
        self.label_hist = []
        self.last_open_dir = None
        self.cur_img_idx = 0
        self.img_count = len(self.m_img_list)
        self.color_theme = self.pl.color_theme
        self.adjust_foreground =  5     # brightness
        self.adjust_background = 10     # transparency
        self.filestats = None

        # record image to path (assume unique names!)
        self.image_basename_to_path = defaultdict(str)
        self.path_to_image_basename = defaultdict(str)

        # Whether we need to save or not.
        self.dirty = False

        self._no_selection_slot = False
        self._beginner = True
        self.screencast = "https://youtu.be/p0nR2YsCY_U"

        # Load predefined classes to the list
        #self.load_predefined_classes(default_prefdef_class_file)

        self.plant_hist  = PLANT_NAMES
        self.type_hist  =  TYPE_NAMES
        self.label_hist =  PLANT_TYPE_NAMES 

        self.annotation_opacity = 7

        self.default_plant = self.plant_hist[0]
        self.default_type  = self.type_hist[0]
        self.default_label = self.label_hist[0]

        # Main widgets and related state.
        self.plant_dialog = LabelDialog( parent=self, text="Enter Plant Name", list_item=self.plant_hist)
        self.type_dialog  = LabelDialog( parent=self, text="Enter Stem or Outer", list_item=self.type_hist)
        self.note_dialog  = CreateNote( parent=self, text="Enter Notes" )

        self.items_to_shapes = {}
        self.shapes_to_items = {}
        self.prev_label_text = ''
        self.prev_plant_text = ''
        self.prev_type_text = ''
        self.noise = False


        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(0, 0, 0, 0)

        # visible class types selection
        self.class_type_button = {}
        for class_type in self.bbl.stats.class_type_list:
            self.class_type_button[class_type] = QCheckBox(get_str(class_type))
            if class_type == "inout":
                self.class_type_button[class_type].setChecked(False)
            else:
                self.class_type_button[class_type].setChecked(True)
            self.class_type_button[class_type].stateChanged.connect(self.draw_iou_boxes)
            list_layout.addWidget(self.class_type_button[class_type])

        list_layout.addSpacing(50)

        # visible users selection
        self.user_button = {}
        for user in self.bbl.stats.user_list:
            self.user_button[user] = QCheckBox(user)
            self.user_button[user].setChecked(True)
            self.user_button[user].setChecked(True)
            self.user_button[user].setEnabled(False)
            # self.cb.setStyleSheet("color: black")
            # self.cb.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips)
            # self.cb.setToolTip ('my checkBox')
            self.user_button[user].stateChanged.connect(self.draw_iou_boxes)
            list_layout.addWidget(self.user_button[user])

        #import pdb; pdb.set_trace()
        list_layout.addSpacing(10)
        # ref_user selection

        ref_user_label = QLabel("Reference User:")
        ref_user_label.setAlignment(Qt.AlignCenter)
        list_layout.addWidget(ref_user_label)

        self.ref_user_box = QComboBox()
        self.ref_user_box.addItems(self.bbl.stats.user_list)

        self.ref_user_box.currentIndexChanged.connect(self.draw_iou_boxes)

        list_layout.addWidget(self.ref_user_box)

        list_layout.addSpacing(20)
        iouLabel = QLabel("IOU Filter")
        iouLabel.setAlignment(Qt.AlignCenter)
        list_layout.addWidget(iouLabel)

        self.iouFilterSlider = QSlider(Qt.Horizontal)
        self.iouFilterSlider.setMinimum(0)
        self.iouFilterSlider.setMaximum(10)
        self.iouFilterSlider.setValue(self.iou_filter_value)
        self.iouFilterSlider.valueChanged.connect(self.iou_filter_value_changed)
        list_layout.addWidget(self.iouFilterSlider)

        # color selection
        list_layout.addSpacing(20)

        colorLabel = QLabel("Color Pallet:")
        colorLabel.setAlignment(Qt.AlignCenter)
        list_layout.addWidget(colorLabel)

        self.colorBox = QComboBox()
        self.set_color_theme_options(self.colorBox)
        self.colorBox.currentIndexChanged.connect(self.color_theme_changed)
        list_layout.addWidget(self.colorBox)

        # slider for background and foreground
        backgroundLabel = QLabel("Background Opacity")
        backgroundLabel.setAlignment(Qt.AlignCenter)
        list_layout.addWidget(backgroundLabel)

        self.colorBackgroundSlider = QSlider(Qt.Horizontal)
        self.colorBackgroundSlider.setMinimum(0)
        self.colorBackgroundSlider.setMaximum(10)
        self.colorBackgroundSlider.setValue(self.adjust_background)
        self.colorBackgroundSlider.valueChanged.connect(self.adjust_background_changed)
        list_layout.addWidget(self.colorBackgroundSlider)

        foregroundLabel = QLabel("Annotation Darkness")
        foregroundLabel.setAlignment(Qt.AlignCenter)
        list_layout.addWidget(foregroundLabel)

        self.colorForegroundSlider = QSlider(Qt.Horizontal)
        self.colorForegroundSlider.setMinimum(0)
        self.colorForegroundSlider.setMaximum(10)
        self.colorForegroundSlider.setValue(self.adjust_foreground)
        self.colorForegroundSlider.valueChanged.connect(self.adjust_foreground_changed)
        list_layout.addWidget(self.colorForegroundSlider)


        # Add some of widgets to list_layout
        #list_layout.addStretch()

        # Tzutalin 20160906 : Add file list and dock to move faster
#        self.file_list = QListWidget()
#        file_list = QLabel(get_str('fileList'))
#        file_list.setContentsMargins(0, 0, 0, 0)
#        file_list.setAlignment(Qt.AlignTop)
#        file_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Ignored)
#        file_list.setWordWrap(True)
#
#        self.dock = QDockWidget(get_str('fileList'), self)

        # Add some of widgets to list_layout
        #list_layout.addWidget(self.edit_button)
        #list_layout.addWidget(self.diffc_button)
        #list_layout.addWidget(use_default_label_container)

        # Create and add combobox for showing unique labels in group
        #self.combo_box = ComboBox(self)
        #list_layout.addWidget(self.combo_box)

        #self.edit_button = QToolButton()
        #self.edit_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)

        # Create and add a widget for showing current label items
        self.label_list = QListWidget()
        label_list_container = QWidget()
        label_list_container.setLayout(list_layout)
        self.label_list.itemActivated.connect(self.label_selection_changed)
        self.label_list.itemSelectionChanged.connect(self.label_selection_changed)
        self.label_list.itemDoubleClicked.connect(self.edit_label)
        # Connect to itemChanged to detect checkbox changes.
        self.label_list.itemChanged.connect(self.label_item_changed)
        #list_layout.addWidget(self.label_list)

        self.annotation_dock = QDockWidget("Annotations to Display", self)
        self.annotation_dock.setObjectName('xml')
        self.annotation_dock.setWidget(label_list_container)



           # file list
        self.file_list_widget = QListWidget()
        self.file_list_widget.itemDoubleClicked.connect(self.file_item_double_clicked)
        file_list_layout = QVBoxLayout()
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        file_list_layout.addWidget(self.file_list_widget)
        file_list_layout.setAlignment(Qt.AlignCenter)

        #self.file_list_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #self.file_list_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #list = self.file_list_widget
        #self.file_list_widget.setFixedSize(\
        #    list.sizeHintForColumn(0) + 2 * list.frameWidth(), list.sizeHintForRow(0) * list.count() + 2 * list.frameWidth())

        # size the file list to 10 lines
        file_list_container = QWidget()
        file_list_container.setLayout(file_list_layout)

        self.file_dock = QDockWidget('Image List', self)
        self.file_dock.setObjectName('images')
        self.file_dock.setWidget(file_list_container)

        self.class_list_widget = QListWidget()
        self.class_list_widget.itemDoubleClicked.connect(self.class_item_double_clicked)
        class_list_layout = QVBoxLayout()
        class_list_layout.setContentsMargins(0, 0, 0, 0)
        class_list_layout.addWidget(self.class_list_widget)
        class_list_container = QWidget()
        class_list_container.setLayout(class_list_layout)

        self.class_dock = QDockWidget(get_str('classList'), self)
        self.class_dock.setObjectName(get_str('classes'))
        self.class_dock.setWidget(class_list_container)
        logging.debug(f"self.class_list_widget = {self.class_list_widget}")

        self.zoom_widget = ZoomWidget()
        self.color_dialog = ColorDialog(parent=self)

        self.canvas = Canvas(parent=self)
        self.canvas.zoomRequest.connect(self.zoom_request)
        self.canvas.zoomToSelection.connect(self.zoom_to_selection_callback)
        self.canvas.set_drawing_shape_to_square(settings.get(SETTING_DRAW_SQUARE, False))

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scroll_bars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scroll_area = scroll
        self.canvas.scrollRequest.connect(self.scroll_request)

        # for debug only
        #self.scroll_bars[Qt.Vertical].rangeChanged.connect(self.scroll_vrange_changed)
        #self.scroll_bars[Qt.Horizontal].rangeChanged.connect(self.scroll_hrange_changed)

        self.canvas.newShape.connect(self.new_shape)
        #self.canvas.shapeMoved.connect(self.moved_shape)
        self.canvas.selectionChanged.connect(self.shape_selection_changed)
        self.canvas.drawingPolygon.connect(self.toggle_drawing_sensitive)



        # add docks to RHS
        self.setCentralWidget(scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.annotation_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.class_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.file_dock)
        self.file_dock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.dock_features = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        self.annotation_dock.setFeatures(self.annotation_dock.features() ^ self.dock_features)

        # Actions
        action = partial(new_action, self)
        quit = action(get_str('quit'), self.close,
                      'Ctrl+Q', 'quit', get_str('quitApp'))

        open = action(get_str('openFile'), self.open_file,
                      'Ctrl+O', 'open', get_str('openFileDetail'))

        open_dir = action(get_str('openDir'), self.open_dir_dialog,
                          'Ctrl+u', 'open', get_str('openDir'))

        change_save_dir = action(get_str('changeSaveDir'), self.change_save_dir_dialog,
                                 'Ctrl+r', 'open', get_str('changeSavedAnnotationDir'))

        open_annotation = action(get_str('openAnnotation'), self.open_annotation_dialog,
                                 'Ctrl+Shift+O', 'open', get_str('openAnnotationDetail'))
        copy_prev_bounding = action(get_str('copyPrevBounding'), self.copy_previous_bounding_boxes, 'Ctrl+v', 'copy', get_str('copyPrevBounding'))

        open_next_image = action(get_str('nextImg'), self.open_next_image,
                                 'n', 'next', get_str('nextImgDetail'))

        open_prev_image = action(get_str('prevImg'), self.open_prev_image,
                                 'p', 'prev', get_str('prevImgDetail'))

        verify = action(get_str('verifyImg'), self.verify_image,
                        'space', 'verify', get_str('verifyImgDetail'))

        save = action(get_str('save'), self.save_file,
                      'Ctrl+S', 'save', get_str('saveDetail'), enabled=False)

        def get_format_meta(format):
            """
            returns a tuple containing (title, icon_name) of the selected format
            """
            if format == LabelFileFormat.PASCAL_VOC:
                return '&PascalVOC', 'format_voc'
            elif format == LabelFileFormat.YOLO:
                return '&YOLO', 'format_yolo'
            elif format == LabelFileFormat.CREATE_ML:
                return '&CreateML', 'format_createml'

        save_format = action(get_format_meta(self.label_file_format)[0],
                             self.change_format, '',
                             get_format_meta(self.label_file_format)[1],
                             get_str('changeSaveFormat'), enabled=True)

        save_as = action(get_str('saveAs'), self.save_file_as,
                         'Ctrl+Shift+S', 'save-as', get_str('saveAsDetail'), enabled=False)

        close = action(get_str('closeCur'), self.close_file, 'Ctrl+W', 'close', get_str('closeCurDetail'))

        delete_image = action(get_str('deleteImg'), self.delete_image, 'Ctrl+Shift+D', 'close', get_str('deleteImgDetail'))

        reset_all = action(get_str('resetAll'), self.reset_all, None, 'resetall', get_str('resetAllDetail'))
        reset_quit = action('reset and quit', self.reset_quit, None, 'resetall', get_str('resetAllDetail'))

        color1 = action(get_str('boxLineColor'), self.choose_color1,
                        'Ctrl+L', 'color_line', get_str('boxLineColorDetail'))

        create_mode = action(get_str('crtBox'), self.set_create_mode,
                             'w', 'new', get_str('crtBoxDetail'), enabled=False)
        edit_mode = action(get_str('editBox'), self.set_edit_mode,
                           'Ctrl+J', 'edit', get_str('editBoxDetail'), enabled=False)

        create = action(get_str('crtBox'), self.create_shape,
                        'w', 'new', get_str('crtBoxDetail'), enabled=False)
        delete = action(get_str('delBox'), self.delete_selected_shape,
                        'Delete', 'delete', get_str('delBoxDetail'), enabled=False)
        copy = action(get_str('dupBox'), self.copy_selected_shape,
                      'Ctrl+D', 'copy', get_str('dupBoxDetail'),
                      enabled=False)

        add_note = action(get_str('addNote'), self.create_or_edit_note,
                        'm', 'edit', 'Add a Note',
                        enabled=False)

        advanced_mode = action(get_str('advancedMode'), self.toggle_advanced_mode,
                               'Ctrl+Shift+A', 'expert', get_str('advancedModeDetail'),
                               checkable=True)

        hide_all = action(get_str('hideAllBox'), partial(self.toggle_polygons, False),
                          'Ctrl+H', 'hide', get_str('hideAllBoxDetail'),
                          enabled=False)
        show_all = action(get_str('showAllBox'), partial(self.toggle_polygons, True),
                          'Ctrl+A', 'hide', get_str('showAllBoxDetail'),
                          enabled=False)

        help_default = action(get_str('tutorialDefault'), self.show_default_tutorial_dialog, None, 'help', get_str('tutorialDetail'))
        show_info = action(get_str('info'), self.show_info_dialog, None, 'help', get_str('info'))
        show_shortcut = action(get_str('shortcut'), self.show_shortcuts_dialog, None, 'help', get_str('shortcut'))

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoom_widget)
        self.zoom_widget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (format_shortcut("Ctrl+[-+]"),
                                             format_shortcut("Ctrl+Wheel")))
        self.zoom_widget.setEnabled(False)

        zoom_in = action(get_str('zoomin'), partial(self.add_zoom, 10),
                         'Ctrl++', 'zoom-in', get_str('zoominDetail'), enabled=False)
        zoom_out = action(get_str('zoomout'), partial(self.add_zoom, -10),
                          'Ctrl+-', 'zoom-out', get_str('zoomoutDetail'), enabled=False)
        zoom_sel = action(get_str('zoomsel'), self.zoom_to_selection,
                          'z', 'zoom-area', get_str('zoomselDetail'), enabled=False)
        zoom_org = action(get_str('originalsize'), partial(self.set_zoom, 100),
                          'Ctrl+=', 'zoom', get_str('originalsizeDetail'), enabled=False)
        fit_window = action(get_str('fitWin'), self.set_fit_window,
                            'f', 'fit-window', get_str('fitWinDetail'),
                            checkable=True, enabled=False)
        fit_width = action(get_str('fitWidth'), self.set_fit_width,
                           'Ctrl+Shift+F', 'fit-width', get_str('fitWidthDetail'),
                           checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoom_actions = (self.zoom_widget, zoom_in, zoom_out, zoom_sel,
                        zoom_org, fit_window, fit_width)
        self.zoom_mode = self.ZoomMode.MANUAL_ZOOM
        self.scalers = {
            self.ZoomMode.FIT_WINDOW: self.scale_fit_window,
            self.ZoomMode.FIT_WIDTH: self.scale_fit_width,
            # Set to one to scale to 100% when loading files.
            self.ZoomMode.MANUAL_ZOOM: lambda: 1,
        }

        edit = action(get_str('editLabel'), self.edit_label,
                      'Ctrl+E', 'edit', get_str('editLabelDetail'),
                      enabled=False)
        #self.edit_button.setDefaultAction(edit)

        shape_line_color = action(get_str('shapeLineColor'), self.choose_shape_line_color,
                                  icon='color_line', tip=get_str('shapeLineColorDetail'),
                                  enabled=False)
        shape_fill_color = action(get_str('shapeFillColor'), self.choose_shape_fill_color,
                                  icon='color', tip=get_str('shapeFillColorDetail'),
                                  enabled=False)

        labels = self.annotation_dock.toggleViewAction()
        labels.setText(get_str('showHide'))
        labels.setShortcut('Ctrl+Shift+L')

        # Draw squares/rectangles
        self.draw_squares_option = QAction(get_str('drawSquares'), self)
        self.draw_squares_option.setShortcut('Ctrl+Shift+R')
        self.draw_squares_option.setCheckable(True)
        self.draw_squares_option.setChecked(settings.get(SETTING_DRAW_SQUARE, False))
        self.draw_squares_option.triggered.connect(self.toggle_draw_square)

        # Store actions for further handling.
        self.actions = Struct(save=save, save_format=save_format, saveAs=save_as, open=open, close=close, resetAll=reset_all, deleteImg=delete_image,
                              lineColor=color1, create=create, delete=delete, edit=edit, copy=copy, add_note=add_note,
                              createMode=create_mode, editMode=edit_mode, advancedMode=advanced_mode,
                              shapeLineColor=shape_line_color, shapeFillColor=shape_fill_color,
                              zoom=zoom, zoomIn=zoom_in, zoomOut=zoom_out, zoomSel=zoom_sel, zoomOrg=zoom_org, 
                              fitWindow=fit_window, fitWidth=fit_width,
                              zoomActions=zoom_actions,
                              fileMenuActions=(
                                  open, open_dir, save, save_as, close, reset_all, quit),
                              beginner=(), advanced=(),
                              editMenu=(edit, copy, delete,
                                        None, color1, self.draw_squares_option),
                              beginnerContext=(create, edit, copy, delete),
                              advancedContext=(create_mode, edit_mode, edit, copy,
                                               delete, shape_line_color, shape_fill_color),
                              onLoadActive=(
                                  close, create, create_mode, edit_mode),
                              onShapesPresent=(save_as, hide_all, show_all))

        self.menus = Struct(
            file=self.menu(get_str('menu_file')),
            edit=self.menu(get_str('menu_edit')),
            view=self.menu(get_str('menu_view')),
            help=self.menu(get_str('menu_help')),
            recentFiles=QMenu(get_str('menu_openRecent')),)

        # Auto saving : Enable auto saving if pressing next
        self.auto_saving = QAction(get_str('autoSaveMode'), self)
        self.auto_saving.setCheckable(True)
        self.auto_saving.setChecked(settings.get(SETTING_AUTO_SAVE, False))
        # Sync single class mode from PR#106
        self.single_class_mode = QAction(get_str('singleClsMode'), self)
        self.single_class_mode.setShortcut("Ctrl+Shift+S")
        self.single_class_mode.setCheckable(True)
        self.single_class_mode.setChecked(settings.get(SETTING_SINGLE_CLASS, False))
        self.lastLabel = None
        # Add option to enable/disable labels being displayed at the top of bounding boxes
        self.display_label_option = QAction(get_str('displayLabel'), self)
        self.display_label_option.setShortcut("Ctrl+Shift+P")
        self.display_label_option.setCheckable(True)
        self.display_label_option.setChecked(settings.get(SETTING_PAINT_LABEL, True))
        self.display_label_option.triggered.connect(self.toggle_paint_labels_option)
        Shape.paint_label = self.display_label_option.isChecked()

        self.display_note_option = QAction(get_str('displayNote'), self)
        self.display_note_option.setShortcut("Ctrl+Shift+N")
        self.display_note_option.setCheckable(True)
        self.display_note_option.setChecked(settings.get(SETTING_PAINT_NOTE, True))
        self.display_note_option.triggered.connect(self.toggle_paint_notes_option)
        Shape.paint_note = self.display_note_option.isChecked()

        add_actions(self.menus.file,
                    (open, open_dir, change_save_dir, open_annotation, copy_prev_bounding, self.menus.recentFiles, save, save_format, save_as, close, reset_all, delete_image, quit))
        add_actions(self.menus.help, (help_default, show_info, show_shortcut))
        add_actions(self.menus.view, (
            self.auto_saving,
            self.single_class_mode,
            self.display_label_option,
            self.display_note_option,
            labels, advanced_mode, None,
            hide_all, show_all, None,
            zoom_in, zoom_out, zoom_sel, zoom_org, None,
            fit_window, fit_width ))

        self.menus.file.aboutToShow.connect(self.update_file_menu)

        # Custom context menu for the canvas widget:
        add_actions(self.canvas.menus[0], self.actions.beginnerContext)
        add_actions(self.canvas.menus[1], (
            action('&Copy here', self.copy_shape),
            action('&Move here', self.move_shape)))

        self.tools = self.toolbar('Tools')
        self.actions.beginner = (
            open, open_dir, change_save_dir, open_next_image, open_prev_image, save, None, create, copy, delete, add_note, None,
            zoom_in, zoom, zoom_out, zoom_sel, fit_window, fit_width)

        self.actions.advanced = (
            open, open_dir, change_save_dir, open_next_image, open_prev_image, save, save_format, None,
            create_mode, edit_mode, None,
            hide_all, show_all)

        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.image_path = None
        self.annotation_path = None
        self.last_open_dir = None
        self.recent_files = []
        self.max_recent = 7
        self.line_color = None
        self.fill_color = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        
        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = QPoint(0, 0)
        saved_position = settings.get(SETTING_WIN_POSE, position)
        # Fix the multiple monitors issue
        # https://github.com/enthought/pyface/discussions/849
        for i in range(len(QApplication.screens())):
            if QApplication.screens()[i].availableGeometry().contains(saved_position):
                position = saved_position
                break
        self.resize(size)
        self.move(position)
        save_dir = settings.get(SETTING_SAVE_DIR, None)
        self.last_open_dir = settings.get(SETTING_LAST_OPEN_DIR, None)
        if self.default_save_dir is None and save_dir is not None and os.path.exists(save_dir):
            self.default_save_dir = save_dir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.default_save_dir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.line_color = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fill_color = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.set_drawing_color(self.line_color)
        # Add chris
        Shape.difficult = self.difficult



        # Populate the File menu dynamically.
        #self.update_file_menu()

        # Since loading the file may take some time, make sure it runs in the background.
        """
        if self.image_path and os.path.isdir(self.image_path):
            self.queue_event(partial(self.import_dir_images, self.image_path or ""))
        elif self.image_path:
            self.queue_event(partial(self.load_file, self.image_path or ""))
        """
        self.queue_event(self.import_filelist_images)
        # bypass : assume we have a list of files already

        # Callbacks:
        self.zoom_widget.valueChanged.connect(self.paint_canvas)

        self.populate_mode_actions()

        # Display cursor coordinates at the right of status bar
        self.label_coordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.label_coordinates)

        # Open Dir if default file
        #if self.image_path and os.path.isdir(self.image_path):
        #    self.open_dir_dialog(dir_path=self.image_path, silent=True)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.canvas.set_drawing_shape_to_square(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            # Draw rectangle if Ctrl is pressed
            self.canvas.set_drawing_shape_to_square(True)

    # Support Functions #
    def set_format(self, save_format):
        if save_format == FORMAT_PASCALVOC:
            self.actions.save_format.setText(FORMAT_PASCALVOC)
            self.actions.save_format.setIcon(new_icon("format_voc"))
            self.label_file_format = LabelFileFormat.PASCAL_VOC
            LabelFile.suffix = XML_EXT

        elif save_format == FORMAT_YOLO:
            self.actions.save_format.setText(FORMAT_YOLO)
            self.actions.save_format.setIcon(new_icon("format_yolo"))
            self.label_file_format = LabelFileFormat.YOLO
            LabelFile.suffix = TXT_EXT

        elif save_format == FORMAT_CREATEML:
            self.actions.save_format.setText(FORMAT_CREATEML)
            self.actions.save_format.setIcon(new_icon("format_createml"))
            self.label_file_format = LabelFileFormat.CREATE_ML
            LabelFile.suffix = JSON_EXT

    def change_format(self):
        if self.label_file_format == LabelFileFormat.PASCAL_VOC:
            self.set_format(FORMAT_YOLO)
        elif self.label_file_format == LabelFileFormat.YOLO:
            self.set_format(FORMAT_CREATEML)
        elif self.label_file_format == LabelFileFormat.CREATE_ML:
            self.set_format(FORMAT_PASCALVOC)
        else:
            raise ValueError('Unknown label file format.')
        self.set_dirty()

    def no_shapes(self):
        return not self.items_to_shapes

    def toggle_advanced_mode(self, value=True):
        self._beginner = not value
        self.canvas.set_editing(True)
        self.populate_mode_actions()
        #self.edit_button.setVisible(not value)
        if value:
            self.actions.createMode.setEnabled(True)
            self.actions.editMode.setEnabled(False)
            self.annotation_dock.setFeatures(self.annotation_dock.features() | self.dock_features)
        else:
            self.annotation_dock.setFeatures(self.annotation_dock.features() ^ self.dock_features)

    def populate_mode_actions(self):
        if self.beginner():
            tool, menu = self.actions.beginner, self.actions.beginnerContext
        else:
            tool, menu = self.actions.advanced, self.actions.advancedContext
        self.tools.clear()
        add_actions(self.tools, tool)
        self.canvas.menus[0].clear()
        add_actions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = (self.actions.create,) if self.beginner()\
            else (self.actions.createMode, self.actions.editMode)
        add_actions(self.menus.edit, actions + self.actions.editMenu)

    def set_beginner(self):
        self.tools.clear()
        add_actions(self.tools, self.actions.beginner)

    def set_advanced(self):
        self.tools.clear()
        add_actions(self.tools, self.actions.advanced)

    def set_dirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def set_clean(self):
        self.dirty = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)

    def toggle_actions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            z.setEnabled(value)
        for action in self.actions.onLoadActive:
            action.setEnabled(value)

    def queue_event(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def reset_state(self):
        self.items_to_shapes.clear()
        self.shapes_to_items.clear()
        self.label_list.clear()
        self.image_path = None
        self.image_data = None
        self.label_file = None
        self.canvas.reset_state()
        self.label_coordinates.clear()
        #self.combo_box.cb.clear()

    def current_item(self):
        items = self.label_list.selectedItems()
        if items:
            return items[0]
        return None

    def add_recent_file(self, image_path):
        if image_path in self.recent_files:
            self.recent_files.remove(image_path)
        elif len(self.recent_files) >= self.max_recent:
            self.recent_files.pop()
        self.recent_files.insert(0, image_path)

    def beginner(self):
        return self._beginner

    def advanced(self):
        return not self.beginner()

    def show_tutorial_dialog(self, browser='default', link=None):
        if link is None:
            link = self.screencast

        if browser.lower() == 'default':
            wb.open(link, new=2)
        elif browser.lower() == 'chrome' and self.os_name == 'Windows':
            if shutil.which(browser.lower()):  # 'chrome' not in wb._browsers in windows
                wb.register('chrome', None, wb.BackgroundBrowser('chrome'))
            else:
                chrome_path="C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                if os.path.isfile(chrome_path):
                    wb.register('chrome', None, wb.BackgroundBrowser(chrome_path))
            try:
                wb.get('chrome').open(link, new=2)
            except:
                wb.open(link, new=2)
        elif browser.lower() in wb._browsers:
            wb.get(browser.lower()).open(link, new=2)

    def show_default_tutorial_dialog(self):
        self.show_tutorial_dialog(browser='default')

    def show_info_dialog(self):
        from libs.__init__ import __version__
        msg = u'Name:{0} \nApp Version:{1} \n{2} '.format(__appname__, __version__, sys.version_info)
        QMessageBox.information(self, u'Information', msg)

    def show_shortcuts_dialog(self):
        self.show_tutorial_dialog(browser='default', link='https://github.com/tzutalin/labelImg#Hotkeys')

    def create_shape(self):
        logging.debug(f"-->creating shape")
        assert self.beginner()
        self.canvas.set_editing(False)
        self.actions.create.setEnabled(False)

    def create_or_edit_note(self):
        if not self.canvas.editing():
            return
        item = self.current_item()
        if not item:
            return
        shape = self.items_to_shapes[item]
        note_text = self.note_dialog.pop_up(shape.note)
        logging.debug(f"creating note = {note_text}")
        if note_text != shape.note:
            shape.note = note_text
            self.set_dirty()


    def toggle_drawing_sensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            logging.info('Cancel creation.')
            self.canvas.set_editing(True)
            self.canvas.restore_cursor()
            self.actions.create.setEnabled(True)

    def toggle_draw_mode(self, edit=True):
        self.canvas.set_editing(edit)
        self.actions.createMode.setEnabled(edit)
        self.actions.editMode.setEnabled(not edit)

    def set_create_mode(self):
        assert self.advanced()
        self.toggle_draw_mode(False)

    def set_edit_mode(self):
        assert self.advanced()
        self.toggle_draw_mode(True)
        self.label_selection_changed()

    def update_file_menu(self):
        curr_image_path = self.image_path

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recent_files if f !=
                 curr_image_path and exists(f)]
        for i, f in enumerate(files):
            icon = new_icon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.load_recent, f))
            menu.addAction(action)

    def pop_label_list_menu(self, point):
        self.menus.labelList.exec_(self.label_list.mapToGlobal(point))

    def split_label(self,label):
        """
        split by _ into plant and type
        """
        if '_' in label:
            plant, type = label.rsplit('_', 1)
        else:
            plant, type = label,"outer"
        return plant, type


    def get_color(self,text):
        """
        get color from map or autogen
        alpha = 0-255 annotation_opacity : 0 to 10
        """
        alpha = self.annotation_opacity * 255 / 10.0
        if text in PLANT_COLORS:
            color = QColor(PLANT_COLORS[text])
            color.setAlpha(alpha)
        else:
            color = generate_color_by_text(text)
        return color

    def get_fg_color(self,text):
        """
        assume dark colors for stems and light colors for outers
        """
        alpha = 225
        if "_stem" in text:
            color = Qt.white
        else:
            color = self.get_color(text)
            color.setAlpha(alpha)
        return color

    def get_bg_color(self,text):
        """
        assume dark for stem and light for outer
        """
        return Qt.black
        plant, type = self.split_label(text)
        if "outer" in type:
            color = Qt.black
        else:
            color = QColor("#aaa") # off white
        return color

    def get_fill_color(self,text):
        """
        more alpha in fill
        """
        alpha = 50
        color = self.get_color(text)
        color.setAlpha(alpha)
        #logging.debug(f"l={text} so c={color.name()} alpha={color.alpha()}")
        return color


    def edit_label(self):
        if not self.canvas.editing():
            return
        item = self.current_item()
        if not item:
            return
        orig_plant, orig_type = self.split_label(item.text())
        plant = self.plant_dialog.pop_up(orig_plant)
        type  = self.type_dialog.pop_up(orig_type)
        if plant is None:
            plant = orig_plant
        if type is None:
            type = orig_type
        text = f"{plant}_{type}"
        if text is not None:
            item.setText(text)
            item.setBackground(self.get_bg_color(text))
            item.setForeground(self.get_fg_color(text))
            self.set_dirty()
            self.update_combo_box()


    def update_footer_text(self):

        if 'compare' in __appname__:
            return

        css = self.get_right_table_css()
        html = self.get_boxcount_table_html()
        if html is None:
            self.canvas.footer_right_block_text = None
        else:
            text = f"<style>{css}</style><html>{html}</html>"
            self.canvas.footer_right_block_text = text
    
        css = self.get_left_table_css()
        html = self.get_imagestats_table_html()
        if html is None:
            self.canvas.footer_left_block_text = None
        else:
            text = f"<style>{css}</style><html>{html}</html>"
            #logging.debug(text)
            self.canvas.footer_left_block_text = text


    def get_imagestats_table_html(self):


        text = f"""
<table>
<caption>Image Stats</caption>
<body>
  <tr><td>image</td><td>{self.image_path}</td></tr>
  <tr><td>annotation</td><td>{self.annotation_path}</td></tr>
        """


        if self.filestats is not None:
            attr = "username timestamp".split()
            for key in attr:
                if hasattr(self.filestats, key):
                    value = getattr(self.filestats, key)
                    if value is not None:
                        text += f'<tr><td>{key}</td><td>{value}</td></tr>'

        text += f"""
</body>
</table>
        """
        #logging.debug(text)
        return text




    def get_boxcount_table_html(self):

        cname, cplant, ctype, cplantType = self.count_shapes()
        text = """
<table>
<caption>Box Counts</caption>
<thead>
  <tr>"""
        text += f"<th>plant</th>"
        for type in TYPE_NAMES:
            text += f"<th>{type}</th>"
        text += f"<th>total</th>"

        text += "</tr></thead><tbody>"
        
        for plant, tcount in cplant.most_common():
            color = self.get_fg_color(plant + "_outer" ).name()
            text += f'<tr><td style="color: {color};">{plant}</td>'
            for type in TYPE_NAMES:
                count = cplantType[plant][type]
                text += f"<td>{count}</td>"
                #logging.debug(f" cplantType[{plant}][{type}] =  {count}")
            text += f"<td>{tcount}</td>"
            text += "</tr>"

        text += "</tbody></table>"
        return text


    def get_left_table_css(self):

        # gen using https://divtable.com/table-styler/

        return """

table {
  color: "#ddd";
  width: 100%;
  text-align: center;
  border-collapse: collapse;
}
table caption {
  font-weight: bold;
  font-size: 20px;
}
table td, table th {
  padding: 5px 5px;
  text-align: left;
}

    """

    def get_right_table_css(self):

        # gen using https://divtable.com/table-styler/

        return """

table {
  color: "#ddd";
  width: 100%;
  text-align: center;
  border-collapse: collapse;
}
table caption {
  font-weight: bold;
  font-size: 20px;
}
table td, table th {
  padding: 5px 5px;
  text-align: right;
}
table td{
  color: white;
  font-weight: bold;
}
table thead th {
  font-size: 15px;
  text-align: center;
}

    """



    def count_shapes(self):
        namelist = []
        for shape in self.canvas.shapes:
            namelist.append(shape.label)

        cname  = Counter()
        cplant = Counter()
        ctype  = Counter()
        for name in namelist:
            cname[name] += 1
            plant, type = split_name_into_plant_and_type(name)
            cplant[plant] += 1
            ctype[type] += 1
        
        cplantType = {}
        for plant in cplant:
            cplantType[plant] = Counter()

        for name in namelist:
            plant, type = split_name_into_plant_and_type(name)
            cplantType[plant][type] += 1

        return cname, cplant, ctype, cplantType

    # Tzutalin 20160906 : Add file list and dock to move faster
    def file_item_double_clicked(self, item=None):
        imgName = item.text()
        imgPath = self.image_basename_to_path[imgName]
        logging.debug(f"loading image {self.cur_img_idx} :  {imgName} from {imgPath}")
        # TODO: remove index scheme of tracking files
        self.cur_img_idx = self.m_img_list.index(ustr(imgPath))
        filename = self.m_img_list[self.cur_img_idx]
        logging.debug(f"loading filename = {filename}")
        if filename:
            self.load_file(filename)

    # Add chris
    def button_state(self, item=None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return

        item = self.current_item()
        if not item:  # If not selected Item, take the first one
            item = self.label_list.item(self.label_list.count() - 1)
        logging.debug(f"button pressed!: {item.text()}")

        difficult = self.diffc_button.isChecked()

        shape = self.items_to_shapes[item]
        if difficult != shape.difficult:
            shape.difficult = difficult
            self.set_dirty()
        else:
            self.canvas.set_shape_visible(shape, item.checkState() == Qt.Checked)

    # React to canvas signals.
    def shape_selection_changed(self, selected=False):
        if self._no_selection_slot:
            self._no_selection_slot = False
        else:
            shape = self.canvas.selected_shape
            if shape:
                self.shapes_to_items[shape].setSelected(True)
            else:
                self.label_list.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.add_note.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)

    def add_label(self, shape):
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setBackground(self.get_bg_color(shape.label))
        item.setForeground(self.get_fg_color(shape.label))
        

        self.items_to_shapes[item] = shape
        self.shapes_to_items[shape] = item
        self.label_list.addItem(item)
        for action in self.actions.onShapesPresent:
            action.setEnabled(True)
        self.update_combo_box()
        self.update_footer_text()

    def remove_label(self, shape):
        if shape is None:
            logging.info('rm empty label')
            return
        item = self.shapes_to_items[shape]
        self.label_list.takeItem(self.label_list.row(item))
        del self.shapes_to_items[shape]
        del self.items_to_shapes[item]
        self.update_combo_box()
        self.update_footer_text()

    def load_labels(self, shapes):
        s = []
        logging.debug(f"load_labels shapes = {shapes}")
        for label, points, line_color, fill_color, note, user, difficult in shapes:
            shape = Shape(label=label)
            for x, y in points:

                # Ensure the labels are within the bounds of the image. If not, fix them.
                x, y, snapped = self.canvas.snap_point_to_canvas(x, y)
                if snapped:
                    self.set_dirty()

                shape.add_point(QPointF(x, y))
            shape.note = note
            shape.user = user
            shape.difficult = difficult
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = self.get_color(label)

            if fill_color:
                shape.fill_color = QColor(*fill_color)
            else:
                shape.fill_color = self.get_fill_color(label)

            self.add_label(shape)
        self.update_combo_box()
        self.canvas.load_shapes(s)
        self.update_footer_text()

    def recolor_shapes(self):
        logging.debug(f"recolor with o={self.annotation_opacity}")
        for shape in self.canvas.shapes:
            shape.line_color = self.get_color(shape.label)
        self.canvas.repaint()



    def update_combo_box(self):
        #        ## Get the unique labels and add them to the Combobox.
        #        #items_text_list = [str(self.label_list.item(i).text()) for i in range(self.label_list.count())]
        #
        #        unique_text_list = list(set(items_text_list))
        #        # Add a null row for showing all the labels
        #        unique_text_list.append("")
        #        unique_text_list.sort()
        #self.combo_box.update_items(self.bbl.stats.user_list)
        pass

    def save_labels(self, annotation_path):
        annotation_path = ustr(annotation_path)
        if self.label_file is None:
            self.label_file = LabelFile()
            self.label_file.verified = self.canvas.verified

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                        note=s.note,
                        user=s.user,
                        difficult=s.difficult)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # Can add different annotation formats here
        try:
            if self.label_file_format == LabelFileFormat.PASCAL_VOC:
                if annotation_path[-4:].lower() != ".xml":
                    annotation_path += XML_EXT
                self.annotation_path = annotation_path + annotation_path
                self.update_footer_text()
                self.label_file.save_pascal_voc_format(annotation_path, shapes, self.image_path, self.image_data,
                                                       self.line_color.getRgb(), self.fill_color.getRgb())
            elif self.label_file_format == LabelFileFormat.YOLO:
                if annotation_path[-4:].lower() != ".txt":
                    annotation_path += TXT_EXT
                self.label_file.save_yolo_format(annotation_path, shapes, self.image_path, self.image_data, self.label_hist,
                                                 self.line_color.getRgb(), self.fill_color.getRgb())
            elif self.label_file_format == LabelFileFormat.CREATE_ML:
                if annotation_path[-5:].lower() != ".json":
                    annotation_path += JSON_EXT
                self.label_file.save_create_ml_format(annotation_path, shapes, self.image_path, self.image_data,
                                                      self.label_hist, self.line_color.getRgb(), self.fill_color.getRgb())
            else:
                self.label_file.save(annotation_path, shapes, self.image_path, self.image_data,
                                     self.line_color.getRgb(), self.fill_color.getRgb())
            logging.info('Image:{0} -> Annotation:{1}'.format(self.image_path, annotation_path))
            return True
        except LabelFileError as e:
            self.error_message(u'Error saving label data', u'<b>%s</b>' % e)
            return False

    def copy_selected_shape(self):
        self.add_label(self.canvas.copy_selected_shape())
        # fix copy and delete
        self.shape_selection_changed(True)

    def combo_selection_changed(self, index):
        text = self.combo_box.cb.itemText(index)
        logging.debug(f"reference changed: {text}")
        # HACK workaround for now...
        if not text:
            self.update_combo_box()



    def label_selection_changed(self):
        item = self.current_item()
        if item and self.canvas.editing():
            self._no_selection_slot = True
            if item in self.items_to_shapes:
                shapes = self.items_to_shapes[item]
                self.canvas.select_shape(shapes)
            #else:
                #logging.warning(f"item {item} not in self.items_to_shapes")

            # Add Chris
            #self.diffc_button.setChecked(shape.difficult)

    def update_plant_type_combo_box(self, label):
        """
        update combo box
        """
        get_str = lambda str_id: self.string_bundle.get_string(str_id)
        if label == get_str('selectAll') or label == "":
            return
        if label == get_str('selectWeeds') or get_str('selectCrops'):
            return
        if label == get_str('selectOuters') or get_str('selectStems'):
            return
        # split by last '_' character
        plant, type = self.split_label(label)
        logging.debug(f" update_plant_label_box to {label} =  {plant} and {type}")
        self.noise = True
        index = self.default_plant_combo_box.cb.findText(plant);
        if ( index == -1 ):
            logging.warning(f"plant = {plant} not found")
        else:
            self.default_plant_combo_box.cb.setCurrentIndex(index)

        index = self.default_type_combo_box.cb.findText(type);
        if ( index == -1 ):
            logging.warning(f"type = {type} not found")
        else:
            self.default_type_combo_box.cb.setCurrentIndex(index)
        self.noise = False
        logging.debug(f" update_plant_label_box finished with {plant} and {type}")

    def adjust_annotation_opacity_changed(self):
        value = self.annotationOpacitySlider.value()
        if self.annotation_opacity != value:
            self.annotation_opacity = value
            self.recolor_shapes()

        logging.debug(f" adjust_annotation_opacity_changed to {self.annotation_opacity}")

    def label_item_changed(self, item):
        shape = self.items_to_shapes[item]
        label = item.text()
        logging.debug(f"label_item_changed {label}")
        if label != shape.label:
            shape.label = item.text()
            shape.line_color = generate_color_by_text(shape.label)
            self.set_dirty()
        else:  # User probably changed item visibility
            self.canvas.set_shape_visible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def new_shape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        """
        # if creating note then use special name for box
        if not self.use_default_label_checkbox.isChecked():
            if len(self.label_hist) > 0:
                self.plant_dialog = LabelDialog( parent=self, text="Enter Plant Name", list_item=self.plant_hist)
                self.type_dialog  = LabelDialog( parent=self, text="Enter Stem or Outer", list_item=self.type_hist)

            # Sync single class mode from PR#106
            if self.single_class_mode.isChecked() and self.lastLabel:
                text = self.lastLabel
            else:
                plant = self.plant_dialog.pop_up(text=self.prev_plant_text)
                type  = self.type_dialog.pop_up(text=self.prev_type_text)
                if plant is None:
                    plant = self.default_plant
                if type is None:
                    type = self.default_type
                text  = f"{plant}_{type}"
                logging.debug(f"new shape text = {text}")
                self.lastLabel = text
        else:
            text = self.default_label
        """

        # Add Chris
        #self.diffc_button.setChecked(False)
        if text is not None:
            self.prev_label_text = text
            line_color = self.get_color(text)
            fill_color = self.get_fill_color(text)
            shape = self.canvas.set_last_label(text, line_color, fill_color)
            shape.user = self.username
            logging.debug(f"new_shape text = {text}")
            self.add_label(shape)
            if self.beginner():  # Switch to edit mode.
                self.canvas.set_editing(True)
                self.actions.create.setEnabled(True)
            else:
                self.actions.editMode.setEnabled(True)
            self.set_dirty()

            if text not in self.label_hist:
                self.label_hist.append(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.reset_all_lines()

    """
    # https://stackoverflow.com/questions/1736015/debugging-a-pyqt4-app
    def debug_trace(self):
        '''Set a tracepoint in the Python debugger that works with Qt'''
        from PyQt5.QtCore import pyqtRemoveInputHook

        from pdb import set_trace
        pyqtRemoveInputHook()
        set_trace()
        # QtCore.pyqtRestoreInputHook()
    """

    def scroll_request_zoom(self, absolute, orientation):
        bar = self.scroll_bars[orientation]
        logging.info(f"current bar = {bar} p={orientation} new value = {absolute}")
        logging.info(f"current bar = {str(bar.__dict__)} new value = {absolute}")
        logging.info(f"current bar val = {bar.value()}") 
        logging.info(f"current bar ps = {bar.pageStep()}") 
        logging.info(f"current bar min = {bar.minimum()}") 
        logging.info(f"current bar max = {bar.maximum()}") 
        logging.info(f"current bar pox = {bar.sliderPosition()}") 
        for i in range(100):
            bar.setValue(i)
            logging.info(f"current bar val = {bar.value()}") 
            self.canvas.update() 
            self.canvas.update() 
        #self.debug_trace()


    def scroll_request(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scroll_bars[orientation]
        value = bar.value() + bar.singleStep() * units
        #logging.debug(f"bar {orientation}  min:{bar.minimum()} max:{bar.maximum()} value:{bar.value()} new_value={value}")
        bar.setValue(value)

    def set_zoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoom_mode = self.ZoomMode.MANUAL_ZOOM
        self.zoom_widget.setValue(value)

    def add_zoom(self, increment=10):
        self.set_zoom(self.zoom_widget.value() + increment)
        self.zoom_mode = self.MANUAL_ZOOM

    def zoom_to_selection(self):
        self.zoom_mode = self.ZoomMode.ZOOM_TO_AREA
        self.canvas.mode_zoom_to_area = True

    def scroll_vrange_changed(self, min, max):
        v_bar = self.scroll_bars[Qt.Vertical]
        v_bar_max = v_bar.maximum()
        v_bar_min = v_bar.minimum()
        v_bar_value =  v_bar.value()
        logging.debug(f" scroll vrange changed to {min} - {max} : {v_bar_min} v={v_bar_value} {v_bar_max} ")

    def scroll_hrange_changed(self, min, max):
        h_bar = self.scroll_bars[Qt.Horizontal]
        h_bar_max = h_bar.maximum()
        h_bar_min = h_bar.minimum()
        h_bar_value =  h_bar.value()
        logging.debug(f" scroll hrange changed to {min} - {max} : {h_bar_min} v={h_bar_value} {h_bar_max} ")

    def zoom_to_selection_callback(self, rect):


        self.canvas.mode_zoom_to_area = False

        """
        first calculate scale comparing pixmap size vs display size
        """
        px1 = rect.x()
        pw  = rect.width()
        px2 = px1 + pw
        py1 = rect.y()
        ph  = rect.height()
        py2 = py1 + ph

        # pixmap
        if ph == 0 or pw == 0:
            logging.debug(f" zoom window too small: {rect}")
            return

        # compare pixmap aspect ratio to display aspect ratio and scale by 
        # width or height
        pa = pw / ph

        # display
        dw = self.centralWidget().width()
        dh = self.centralWidget().height() 
        da = dw / dh

        if pa > da:
            scale = dw/pw
        else:
            scale = dh/ph

        old_zoom_value = self.zoom_widget.value()
        new_zoom_value = int(100 * scale) 


        """

        shift bar

         see https://stackoverflow.com/questions/17432534/set-slider-size-of-qscrollbar-correspond-with-content

         document length = maximum() - minimum() + pageStep().

         min          value   max
          [------------[==================]------]
                              bar_len

        
        """

        # record location before momving
        h_bar = self.scroll_bars[Qt.Horizontal]
        v_bar = self.scroll_bars[Qt.Vertical]

        #orig_h = self.record_bar_stats(h_bar)
        #orig_v = self.record_bar_stats(v_bar)

        #shift_h = self.record_bar_stats(h_bar)
        #shift_v = self.record_bar_stats(v_bar)

        #logging.warning(f"1={px1} 2={px2} z={old_zoom_value} {px1/old_zoom_value}")

        # shift based on ratio 
        #w2 = self.canvas.pixmap.width() - 0.0
        #h2 = self.canvas.pixmap.height() - 0.0
        #shift_h.value += h_percent * shift_h.pstep
        #logging.debug(f"shift_h.value = {orig_h.value} + {h_percent} * {shift_h.pstep} = {shift_h.value}")

        #v_percent = py1 / self.scroll_area.height()
        #shift_v.value += v_percent * shift_v.pstep
         
        # ok now zoom and let slider get adjusted
        self.zoom_widget.setValue(new_zoom_value)
        logging.debug(f" set zoom value from {old_zoom_value} to {new_zoom_value}")

        zoom_h = self.record_bar_stats(h_bar)
        zoom_v = self.record_bar_stats(v_bar)

        extra_height = self.canvas.footer_block_height
        h_percent = px1 / self.canvas.pixmap.width()
        v_percent = (py1 + 1.5 * extra_height) / (self.canvas.pixmap.height() + 3 * extra_height)
        logging.debug(f"h_percent = {px1} / {self.canvas.pixmap.width()} = {h_percent}")

        zoom_h.value = h_percent * zoom_h.dlen
        zoom_v.value = v_percent * zoom_v.dlen

        #logging.debug(f"zoom_h.value = {shift_h.value} * {zoom_h.dlen} / {shift_h.dlen} = {zoom_h.value}")

        h_bar.setValue(zoom_h.value)
        v_bar.setValue(zoom_v.value)

    def record_bar_stats(self, bar):
        stats = BarStats();
        stats.min   = bar.minimum()
        stats.max   = bar.maximum()
        stats.value = bar.value()
        stats.pstep = bar.pageStep()
        stats.dlen  = stats.max - stats.min + stats.pstep
        logging.debug(f"min={stats.min} max={stats.max} v={stats.value} p={stats.pstep} d={stats.dlen}")
        return stats


    def zoom_request(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scroll_bars[Qt.Horizontal]
        v_bar = self.scroll_bars[Qt.Vertical]

        # get the current maximum, to know the difference after zooming
        h_bar_max = h_bar.maximum()
        v_bar_max = v_bar.maximum()

        # get the cursor position and canvas size
        # calculate the desired movement from 0 to 1
        # where 0 = move left
        #       1 = move right
        # up and down analogous
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scroll_area.width()
        h = self.scroll_area.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        margin = 0.1
        move_x = (cursor_x - margin * w) / (w - 2 * margin * w)
        move_y = (cursor_y - margin * h) / (h - 2 * margin * h)

        # clamp the values from 0 to 1
        move_x = min(max(move_x, 0), 1)
        move_y = min(max(move_y, 0), 1)

        # zoom in
        units = delta / (8 * 15)
        scale = 10
        self.add_zoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def set_fit_window(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoom_mode = self.ZoomMode.FIT_WINDOW if value else self.ZoomMode.MANUAL_ZOOM
        self.adjust_scale()

    def set_fit_width(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoom_mode = self.ZoomMode.FIT_WIDTH if value else self.ZoomMode.MANUAL_ZOOM
        self.adjust_scale()

    def toggle_polygons(self, value):
        for item, shape in self.items_to_shapes.items():
            item.setCheckState(Qt.Checked if value else Qt.Unchecked)

    def load_file(self, image_path=None):
        """Load the specified file, or the last opened file if None."""
        self.reset_state()
        self.canvas.setEnabled(False)
        if image_path is None:
            image_path = self.settings.get(SETTING_FILENAME)

        #abs_image_path = os.path.abspath(image_path)
        abs_image_path = image_path
        if abs_image_path and self.file_list_widget.count() > 0:
            logging.debug(f" testing for {abs_image_path} in {self.m_img_list}")
            if abs_image_path in self.m_img_list:
                index = self.m_img_list.index(abs_image_path)
                file_widget_item = self.file_list_widget.item(index)
                file_widget_item.setSelected(True)
                self.file_list_widget.setCurrentItem(file_widget_item)
            else:
                logging.debug(f"clearing...why?")
                self.file_list_widget.clear()
                self.m_img_list.clear()

        if abs_image_path and os.path.exists(abs_image_path):
            if LabelFile.is_label_file(abs_image_path):
                try:
                    self.label_file = LabelFile(abs_image_path)
                except LabelFileError as e:
                    self.error_message(u'Error opening file',
                                       (u"<p><b>%s</b></p>"
                                        u"<p>Make sure <i>%s</i> is a valid label file.")
                                       % (e, abs_image_path))
                    self.status("Error reading %s" % abs_image_path)
                    return False
                self.image_data = self.label_file.image_data
                self.line_color = QColor(*self.label_file.lineColor)
                self.fill_color = QColor(*self.label_file.fillColor)
                self.canvas.verified = self.label_file.verified
            else:
                # Load image:
                # read data first and store for saving into label file.
                self.image_data = read(abs_image_path, None)
                self.label_file = None
                self.canvas.verified = False

            if isinstance(self.image_data, QImage):
                image = self.image_data
            else:
                image = QImage.fromData(self.image_data)
            if image.isNull():
                self.error_message(u'Error opening file',
                                   u"<p>Make sure <i>%s</i> is a valid image file." % abs_file_path)
                self.status("Error reading %s" % abs_file_path)
                return False
                return False
            self.status("Loaded %s" % os.path.basename(abs_image_path))
            logging.info(f"Loaded {os.path.basename(abs_image_path)}")


            # place self.image on using painter on new version with gutters
            self.image = image
            new_width = self.image.width() + self.pl.margin_x
            new_height = self.image.height() + self.pl.margin_y
            image2 = image.scaled(new_width, new_height)
            p= QPainter()
            p.begin(image2)
            p.drawImage(0, 0, image)
            p.end()
            logging.debug(f"loaded image2")

            # convert painter to qimage and set it to canvas
            qimage = QImage(image2)
            self.canvas.load_pixmap(QPixmap.fromImage(image2))
            self.image = image2


            self.image_path = abs_image_path
            #self.canvas.load_pixmap(QPixmap.fromImage(image))
            if self.label_file:
                self.load_labels(self.label_file.shapes)
            self.set_clean()
            self.canvas.setEnabled(True)
            self.adjust_scale(initial=True)
            self.paint_canvas()
            self.add_recent_file(self.image_path)
            self.toggle_actions(True)
            self.show_bounding_box_from_annotation_file(image_path)
            imgName = Path(self.image_path).stem
            self.active_users = self.bbl.stats.image_to_active_users_map[imgName]
            self.ref_user_box.clear()
            self.ref_user_box.addItems(self.active_users)
            #AllItems = [self.ref_user_box.itemText(i) for i in range(self.ref_user_box.count())]
            #logging.warning(f"ref_user list = {AllItems}")

            # ok, now that file is loaded, update combo box
            self.show_class_list_for_image_file(image_path)

            counter = self.counter_str()
            self.setWindowTitle(__appname__ + ' ' + image_path + ' ' + counter)

            # Default : select last item if there is at least one item
            if self.label_list.count():
                self.label_list.setCurrentItem(self.label_list.item(self.label_list.count() - 1))
                self.label_list.item(self.label_list.count() - 1).setSelected(True)
            # get active users and enable them
            for user in self.bbl.stats.user_list:
                if user in self.active_users:
                   self.user_button[user].setEnabled(True)
                else:
                   self.user_button[user].setEnabled(False)


            self.canvas.setFocus()
            self.draw_iou_boxes()
            return True
        return False

    def counter_str(self):
        """
        Converts image counter to string representation.
        """
        return '[{} / {}]'.format(self.cur_img_idx + 1, self.img_count)

    def show_bounding_box_from_annotation_file(self, image_path):
        if self.default_save_dir is not None:
            basename = os.path.basename(os.path.splitext(image_path)[0])
            xml_path = os.path.join(self.default_save_dir, basename + XML_EXT)
            txt_path = os.path.join(self.default_save_dir, basename + TXT_EXT)
            json_path = os.path.join(self.default_save_dir, basename + JSON_EXT)

            """Annotation file priority:
            PascalXML > YOLO
            """
            if os.path.isfile(xml_path):
                self.load_pascal_xml_by_filename(xml_path)
            elif os.path.isfile(txt_path):
                self.load_yolo_txt_by_filename(txt_path)
            elif os.path.isfile(json_path):
                self.load_create_ml_json_by_filename(json_path, image_path)

        else:
            xml_path = os.path.splitext(image_path)[0] + XML_EXT
            txt_path = os.path.splitext(image_path)[0] + TXT_EXT
            if os.path.isfile(xml_path):
                self.load_pascal_xml_by_filename(xml_path)
            elif os.path.isfile(txt_path):
                self.load_yolo_txt_by_filename(txt_path)

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoom_mode != self.ZoomMode.MANUAL_ZOOM:
            self.adjust_scale()
        super(MainWindow, self).resizeEvent(event)

    def paint_canvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoom_widget.value()
        self.canvas.label_font_size = int(0.02 * max(self.image.width(), self.image.height()))
        self.canvas.adjustSize()
        self.canvas.update()

    def adjust_scale(self, initial=False):
        value = self.scalers[self.ZoomMode.FIT_WINDOW if initial else self.zoom_mode]()
        self.zoom_widget.setValue(int(100 * value))

    def scale_fit_window(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        extra_height = self.canvas.footer_block_height
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() + extra_height - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scale_fit_width(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.may_continue():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the beginning
        if self.dir_name is None:
            settings[SETTING_FILENAME] = self.image_path if self.image_path else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.line_color
        settings[SETTING_FILL_COLOR] = self.fill_color
        settings[SETTING_RECENT_FILES] = self.recent_files
        settings[SETTING_ADVANCE_MODE] = not self._beginner
        if self.default_save_dir and os.path.exists(self.default_save_dir):
            settings[SETTING_SAVE_DIR] = ustr(self.default_save_dir)
        else:
            settings[SETTING_SAVE_DIR] = ''

        if self.last_open_dir and os.path.exists(self.last_open_dir):
            settings[SETTING_LAST_OPEN_DIR] = self.last_open_dir
        else:
            settings[SETTING_LAST_OPEN_DIR] = ''

        settings[SETTING_AUTO_SAVE] = self.auto_saving.isChecked()
        settings[SETTING_SINGLE_CLASS] = self.single_class_mode.isChecked()
        settings[SETTING_PAINT_LABEL] = self.display_label_option.isChecked()
        settings[SETTING_PAINT_NOTE] = self.display_note_option.isChecked()
        settings[SETTING_DRAW_SQUARE] = self.draw_squares_option.isChecked()
        settings[SETTING_LABEL_FILE_FORMAT] = self.label_file_format
        settings.save()

    def load_recent(self, filename):
        if self.may_continue():
            self.load_file(filename)

    def scan_all_images(self, folder_path):
        extensions = ['.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        images = []

        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(tuple(extensions)):
                    relative_path = os.path.join(root, file)
                    path = ustr(os.path.abspath(relative_path))
                    images.append(path)
        natural_sort(images, key=lambda x: x.lower())
        return images

    def change_save_dir_dialog(self, _value=False):
        if self.default_save_dir is not None:
            path = ustr(self.default_save_dir)
        else:
            path = '.'

        dir_path = ustr(QFileDialog.getExistingDirectory(self,
                                                         '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                         | QFileDialog.DontResolveSymlinks))

        if dir_path is not None and len(dir_path) > 1:
            self.default_save_dir = dir_path

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.default_save_dir))
        self.statusBar().show()

    def open_annotation_dialog(self, _value=False):
        if self.image_path is None:
            self.statusBar().showMessage('Please select image first')
            self.statusBar().show()
            return

        path = os.path.dirname(ustr(self.image_path))\
            if self.image_path else '.'
        if self.label_file_format == LabelFileFormat.PASCAL_VOC:
            filters = "Open Annotation XML file (%s)" % ' '.join(['*.xml'])
            filename = ustr(QFileDialog.getOpenFileName(self, '%s - Choose a xml file' % __appname__, path, filters))
            if filename:
                if isinstance(filename, (tuple, list)):
                    filename = filename[0]
            self.load_pascal_xml_by_filename(filename)

    def open_dir_dialog(self, _value=False, dir_path=None, silent=False):
        if not self.may_continue():
            return

        default_open_dir_path = dir_path if dir_path else '.'
        if self.last_open_dir and os.path.exists(self.last_open_dir):
            default_open_dir_path = self.last_open_dir
        else:
            default_open_dir_path = os.path.dirname(self.image_path) if self.image_path else '.'
        if silent != True:
            target_dir_path = ustr(QFileDialog.getExistingDirectory(self,
                                                                    '%s - Open Directory' % __appname__, default_open_dir_path,
                                                                    QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks))
        else:
            target_dir_path = ustr(default_open_dir_path)
        self.last_open_dir = target_dir_path
        self.import_dir_images(target_dir_path)

    def import_filelist_images(self):
        """
        load images from key in self.pl.source_img
        """
        if not self.may_continue():
            logging.warning(f"self.may_continue = {self.may_continue()}")
            #return

        self.file_list_widget.clear()

        for imgName, imgPath in self.bbl.stem2jpgs.items():
            if self.bbl.stats.image_to_class_map[imgName]:
                self.image_basename_to_path[imgName] = imgPath
                self.path_to_image_basename[imgPath] = imgName
        logging.debug(f"self.image_basename_to_path = {self.image_basename_to_path}")

        self.m_img_list = list(self.image_basename_to_path.values())
        self.img_count = len(self.m_img_list)
        logging.debug(f"self.m_img_list = {self.m_img_list}")
        self.open_next_image()
        for imgPath in self.m_img_list:
            imgName = self.path_to_image_basename[imgPath]
            item = QListWidgetItem(imgName)
            self.file_list_widget.addItem(item)

        self.image_path = self.m_img_list[0]
        self.add_recent_file(self.image_path)
        logging.debug(f"curr_image_path = {self.image_path} recent={self.recent_files}")


    def import_dir_images(self, dir_path):
        if not self.may_continue() or not dir_path:
            return

        self.last_open_dir = dir_path
        self.dir_name = dir_path
        self.image_path = None
        self.file_list_widget.clear()

        files_in_dir = self.scan_all_images(dir_path)
        for imgPath in files_in_dir:
            imgName = Path(imgPath).stem
            if self.bbl.stats.image_to_class_map[imgName]:
                self.image_basename_to_path[imgName] = imgPath
                self.path_to_image_basename[imgPath] = imgName
        logging.debug(f"self.image_basename_to_path = {self.image_basename_to_path}")

        self.m_img_list = list(self.image_basename_to_path.values())
        self.img_count = len(self.m_img_list)
        logging.debug(f"self.m_img_list = {self.m_img_list}")
        self.open_next_image()
        for imgPath in self.m_img_list:
            imgName = self.path_to_image_basename[imgPath]
            item = QListWidgetItem(imgName)
            self.file_list_widget.addItem(item)


    def verify_image(self, _value=False):
        # Proceeding next image without dialog if having any label
        if self.image_path is not None:
            try:
                self.label_file.toggle_verify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.save_file()
                if self.label_file is not None:
                    self.label_file.toggle_verify()
                else:
                    return

            self.canvas.verified = self.label_file.verified
            self.paint_canvas()
            self.save_file()

    def open_prev_image(self, _value=False):
        # Proceeding prev image without dialog if having any label
        if self.auto_saving.isChecked():
            if self.default_save_dir is not None:
                if self.dirty is True:
                    self.save_file()
            else:
                self.change_save_dir_dialog()
                return

        if not self.may_continue():
            return

        if self.img_count <= 0:
            return

        if self.image_path is None:
            return

        if self.cur_img_idx - 1 >= 0:
            self.cur_img_idx -= 1
            filename = self.m_img_list[self.cur_img_idx]
            if filename:
                self.load_file(filename)

    def open_next_image(self, _value=False):
        # Proceeding next image without dialog if having any label
        #logging.debug(f"open next image {_value}")
        if self.auto_saving.isChecked():
            if self.default_save_dir is not None:
                if self.dirty is True:
                    self.save_file()
            else:
                self.change_save_dir_dialog()
                return

        if not self.may_continue():
            return

        if self.img_count <= 0:
            return

        filename = None
        if self.image_path is None:
            filename = self.m_img_list[0]
            self.cur_img_idx = 0
        else:
            if self.cur_img_idx + 1 < self.img_count:
                self.cur_img_idx += 1
                filename = self.m_img_list[self.cur_img_idx]
        #logging.debug(f"filename={filename} self.cur_img_idx={self.cur_img_idx} self.m_img_list={self.m_img_list}")

        if filename:
            self.load_file(filename)

    def open_file(self, _value=False):
        if not self.may_continue():
            return
        path = os.path.dirname(ustr(self.image_path)) if self.image_path else '.'
        formats = ['*.%s' % fmt.data().decode("ascii").lower() for fmt in QImageReader.supportedImageFormats()]
        filters = "Image & Label files (%s)" % ' '.join(formats + ['*%s' % LabelFile.suffix])
        filename = QFileDialog.getOpenFileName(self, '%s - Choose Image or Label file' % __appname__, path, filters)
        if filename:
            if isinstance(filename, (tuple, list)):
                filename = filename[0]
            self.cur_img_idx = 0
            self.img_count = 1
            self.load_file(filename)

    def save_file(self, _value=False):
        if self.default_save_dir is not None and len(ustr(self.default_save_dir)):
            if self.image_path:
                image_file_name = os.path.basename(self.image_path)
                saved_file_name = os.path.splitext(image_file_name)[0]
                saved_path = os.path.join(ustr(self.default_save_dir), saved_file_name)
                self._save_file(saved_path)
        else:
            image_file_dir = os.path.dirname(self.image_path)
            image_file_name = os.path.basename(self.image_path)
            saved_file_name = os.path.splitext(image_file_name)[0]
            saved_path = os.path.join(image_file_dir, saved_file_name)
            self._save_file(saved_path if self.label_file
                            else self.save_file_dialog(remove_ext=False))

    def save_file_as(self, _value=False):
        assert not self.image.isNull(), "cannot save empty image"
        self._save_file(self.save_file_dialog())

    def save_file_dialog(self, remove_ext=True):
        caption = '%s - Choose File' % __appname__
        filters = 'File (*%s)' % LabelFile.suffix
        open_dialog_path = self.current_path()
        dlg = QFileDialog(self, caption, open_dialog_path, filters)
        dlg.setDefaultSuffix(LabelFile.suffix[1:])
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        filename_without_extension = os.path.splitext(self.image_path)[0]
        dlg.selectFile(filename_without_extension)
        dlg.setOption(QFileDialog.DontUseNativeDialog, False)
        if dlg.exec_():
            full_image_path = ustr(dlg.selectedFiles()[0])
            if remove_ext:
                return os.path.splitext(full_image_path)[0]  # Return file path without the extension.
            else:
                return full_image_path
        return ''

    def _save_file(self, annotation_path):
        if annotation_path and self.save_labels(annotation_path):
            self.set_clean()
            self.statusBar().showMessage('Saved to  %s' % annotation_path)
            self.statusBar().show()

    def close_file(self, _value=False):
        if not self.may_continue():
            return
        self.reset_state()
        self.set_clean()
        self.toggle_actions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def delete_image(self):
        return
        delete_path = self.image_path
        if delete_path is not None:
            self.open_next_image()
            self.cur_img_idx -= 1
            self.img_count -= 1
            if os.path.exists(delete_path):
                os.remove(delete_path)
            self.import_dir_images(self.last_open_dir)

    def reset_all(self):
        self.settings.reset()
        self.close()
        process = QProcess()
        process.startDetached(os.path.abspath(__file__))

    def reset_quit(self):
        self.settings.reset()
        self.close()
        #process = QProcess()
        #process.startDetached(os.path.abspath(__file__))

    def may_continue(self):
        if not self.dirty:
            return True
        else:
            discard_changes = self.discard_changes_dialog()
            if discard_changes == QMessageBox.No:
                return True
            elif discard_changes == QMessageBox.Yes:
                self.save_file()
                return True
            else:
                return False

    def discard_changes_dialog(self):
        yes, no, cancel = QMessageBox.Yes, QMessageBox.No, QMessageBox.Cancel
        msg = u'You have unsaved changes, would you like to save them and proceed?\nClick "No" to undo all changes.'
        return QMessageBox.warning(self, u'Attention', msg, yes | no | cancel)

    def error_message(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def current_path(self):
        return os.path.dirname(self.image_path) if self.image_path else '.'

    def choose_color1(self):
        color = self.color_dialog.getColor(self.line_color, u'Choose line color',
                                           default=DEFAULT_LINE_COLOR)
        if color:
            self.line_color = color
            Shape.line_color = color
            self.canvas.set_drawing_color(color)
            self.canvas.update()
            self.set_dirty()

    def delete_selected_shape(self):
        self.remove_label(self.canvas.delete_selected())
        self.set_dirty()
        if self.no_shapes():
            for action in self.actions.onShapesPresent:
                action.setEnabled(False)

    def choose_shape_line_color(self):
        color = self.color_dialog.getColor(self.line_color, u'Choose Line Color',
                                           default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selected_shape.line_color = color
            self.canvas.update()
            self.set_dirty()

    def choose_shape_fill_color(self):
        color = self.color_dialog.getColor(self.fill_color, u'Choose Fill Color',
                                           default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selected_shape.fill_color = color
            self.canvas.update()
            self.set_dirty()

    def copy_shape(self):
        self.canvas.end_move(copy=True)
        self.add_label(self.canvas.selected_shape)
        self.set_dirty()

    def move_shape(self):
        self.canvas.end_move(copy=False)
        self.set_dirty()

    def load_predefined_classes(self, predef_classes_file):
        if os.path.exists(predef_classes_file) is True:
            with codecs.open(predef_classes_file, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.label_hist is None:
                        self.label_hist = [line]
                    else:
                        self.label_hist.append(line)

    def load_pascal_xml_by_filename(self, xml_path):
        logging.debug(f"loading xml file {xml_path}")
        self.annotation_path = xml_path

        if self.image_path is None:
            return
        if os.path.isfile(xml_path) is False:
            return

        self.set_format(FORMAT_PASCALVOC)

        t_voc_parse_reader = PascalVocReader(xml_path)
        self.filestats = t_voc_parse_reader.filestats
        shapes = t_voc_parse_reader.get_shapes()
        self.load_labels(shapes)
        self.canvas.verified = t_voc_parse_reader.verified

    def load_yolo_txt_by_filename(self, txt_path):
        if self.image_path is None:
            return
        if os.path.isfile(txt_path) is False:
            return

        self.set_format(FORMAT_YOLO)
        t_yolo_parse_reader = YoloReader(txt_path, self.image)
        shapes = t_yolo_parse_reader.get_shapes()
        print(shapes)
        self.load_labels(shapes)
        self.canvas.verified = t_yolo_parse_reader.verified

    def load_create_ml_json_by_filename(self, json_path, image_path):
        if self.image_path is None:
            return
        if os.path.isfile(json_path) is False:
            return

        self.set_format(FORMAT_CREATEML)

        create_ml_parse_reader = CreateMLReader(json_path, image_path)
        shapes = create_ml_parse_reader.get_shapes()
        self.load_labels(shapes)
        self.canvas.verified = create_ml_parse_reader.verified

    def copy_previous_bounding_boxes(self):
        current_index = self.m_img_list.index(self.image_path)
        if current_index - 1 >= 0:
            prev_image_path = self.m_img_list[current_index - 1]
            self.show_bounding_box_from_annotation_file(prev_image_path)
            self.save_file()

    def toggle_paint_labels_option(self):
        for shape in self.canvas.shapes:
            shape.paint_label = self.display_label_option.isChecked()

    def toggle_paint_notes_option(self):
        Shape.paint_note  = self.display_note_option.isChecked()


    def toggle_draw_square(self):
        self.canvas.set_drawing_shape_to_square(self.draw_squares_option.isChecked())

    def show_class_list_for_image_file(self, imgPath):
        """
        retrieve classes that match an image
        """
        imgName = Path(imgPath).stem
        self.current_image = imgName
        class_list = self.bbl.stats.image_to_class_map[imgName]
        logging.debug(f"class list for {imgName} is {class_list}")
        if not class_list:
            return
        self.class_list_widget.clear()
        logging.debug(f"class list widget clear")
        for cls in class_list:
            self.class_list_widget.addItem(cls)
        logging.debug(f"added classes: {class_list}")
        # make one of the items in the list selected
        self.class_list_widget.setCurrentRow(0)
        # also make it setselected to true
        #import pdb; pdb.set_trace()
        self.class_list_widget.item(0).setSelected(True)
        # ok now set a reference user if nobody is defined
        if not self.ref_user:
            logging.debug(f"get best ref for {imgName}, {class_list[0]}")
            self.ref_user = self.bbl.get_best_ref_user(imgName, class_list[0])
            # update widget as well..assume order of user_list
            if not self.ref_user:
                return
            index = list(self.bbl.stats.user_list).index(self.ref_user)
            self.ref_user_box.setCurrentIndex(index)

            #self.staff_buttons[self.ref_user].setToolTip(f"{self.ref_user} has the most annotations for this image")
            logging.debug(f"{self.ref_user} has the most annotations for this image: setting as ref")
            logging.debug(f"ref_user = {self.ref_user} ")


    # iou filter value changed
    def iou_filter_value_changed(self):
        value = self.iouFilterSlider.value()
        if value != self.iou_filter_value:
            self.iou_filter_value = value
            self.draw_iou_boxes()


    # trigger update on new color theme
    def color_theme_changed(self):
        # get color scheme from combo box
        txt = self.colorBox.currentText()
        if self.color_theme != txt:
            self.color_theme = txt
            self.draw_iou_boxes()

    def adjust_background_changed(self):
        # get value from slider
        value = self.colorBackgroundSlider.value()
        if self.adjust_background != value:
            self.adjust_background = value
            self.draw_iou_boxes()

    def adjust_foreground_changed(self):
        # get value from slider
        value = self.colorForegroundSlider.value()
        if self.adjust_foreground != value:
            self.adjust_foreground = value
            self.draw_iou_boxes()

    def set_color_theme_options(self, widget):
        # set the options and also set default
        c = ColorPalette()
        theme_list = c.get_list_of_themes()
        index = 0
        for themename in theme_list:
            widget.addItem(themename)
            if themename == self.color_theme:
                self.colorBox.setCurrentIndex(index)
            index += 1


    def btnstate(self, state):
        logging.debug(f"state = {state}")
        
        #b = state
        #logging.info(f"user = {user} button pressed {b.text()} checked={b.isChecked()}")
        #if b.isChecked():
        #    self.ref_user = b.text()
        #self.draw_iou_boxes()

    def class_item_double_clicked(self, item=None):
        class_base = item.text()
        logging.debug(f"class item selected : {class_base}")
        self.draw_iou_boxes()
            
    def draw_iou_boxes(self, force_draw=False):
        logging.debug(f"draw -----------------------------------------")
        if self.class_list_widget.selectedItems().__len__() == 0:
            logging.debug(f"draw: no class selected")
            return

        if not self.current_image:
            logging.debug(f"draw: no image selected")
            return

        class_base = self.class_list_widget.selectedItems()[0].text()
        image = self.current_image
        #self.ref_user = self.ref_user_box.currentText()
        #logging.warning(f"ref user changed to {self.ref_user}")

        visible_users = {}
        active_users = self.bbl.stats.image_to_active_users_map[image]
        for user in self.bbl.stats.user_list:
            if user in active_users:
                visible_users[user] = self.user_button[user].isChecked()
            else:
                visible_users[user] = False

        # class type
        visible_types = {}
        for class_type in self.bbl.stats.class_type_list:
            visible_types[class_type] = self.class_type_button[class_type].isChecked()

        dobj = DrawObject(image, class_base, self.ref_user, visible_types, active_users, visible_users, self.iou_filter_value,
                        self.color_theme , self.adjust_background, self.adjust_foreground,)
        if force_draw or dobj != self.current_draw_object:
            self.current_draw_object = dobj
            logging.debug(f"draw: new draw object {dobj}")
            self.draw_overlay_on_canvas()
            self.update_widgets_with_overlay_stats()
        else:
            logging.debug(f"draw: nothing to do : same settings {dobj}")

    def draw_overlay_on_canvas(self):
        if self.current_draw_object.image != self.current_image:
            logging.debug(f"mismatch background image")
            return
        img_data = self.pl.fetch_overlay_image(self.current_draw_object)
        qimg = QImage()
        qimg.loadFromData(img_data, format = 'PNG')
        pm = QPixmap.fromImage(qimg)
        self.canvas.load_overlay(pm, self.adjust_background)


    def update_widgets_with_overlay_stats(self):
        """
        map of counts...
        """
        overlay_stats = self.current_draw_object.overlay_stats
        for user in self.bbl.stats.user_list:
            userclass = f"{user}_total"
            count = overlay_stats['userclass'][userclass]
            self.user_button[user].setText(f"[{count:2d}] {user}")

        get_str = lambda str_id: self.string_bundle.get_string(str_id)
        for class_type in self.bbl.stats.class_type_list:
            count = overlay_stats['class_type'][class_type]
            self.class_type_button[class_type].setText(f"[{count}] {get_str(class_type)}")
            

    def staff_button_toggled(self, user):       
        self.ref_user = user
        self.draw_iou_boxes()
        


def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    reader = QImageReader(filename)
    reader.setAutoTransform(True)
    return reader.read()

def dump_process_info():
    proc = Process()
    logging.debug(f"cmd = {proc.cmdline()}")
    logging.debug(f"env = {proc.environ()}")
    logging.debug(f"cwd = {proc.cwd()}")
    logging.debug(f"files = {proc.open_files()}")

def get_username():
    proc = Process()
    username = proc.username()
    # remove any domain info for windows
    #username = username.split('\\')[-1]
    username = Path(username).name
    return username

def run_main_gui(bbl, pl, args):
    """
    boilerplate Qt application code to bring up main window
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    argv = []
    #app = QApplication(argv)
    app = QApplication.instance()
    if app == None:
        app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(new_icon("tensor"))
    #app.setStyle('Fusion')

    # Usage : labelImg.py image classFile saveDir
    logging.info(f" data dir:  {args.data}")
    logging.info(f" save dir:  {args.out}")
    win = MainWindow(bbl, pl)
    win.show()
    return app, win


#def main():
#    """construct main app and run it"""
#    app, _win = get_main_app(sys.argv)
#    return app.exec_()
#
#if __name__ == '__main__':
#    sys.exit(main())
#
