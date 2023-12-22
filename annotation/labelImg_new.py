#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Original project https://github.com/tzutalin/labelImg
import datetime
import codecs
import cv2
import numpy as np
import os.path
import platform
import sys
import subprocess
from collections import OrderedDict
import shutil
from apscheduler.schedulers.background import BackgroundScheduler

from csv import reader as csv_reader
from time import time
from functools import partial
# Andreu
from pathlib import Path

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# Add internal libs
from libs.images import Images
from libs.constants import *
from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut, getRandomColor, parseColorFromHex, callbackAction
from libs.settings import Settings
from libs.shape import Shape, DEFAULT_LINE_COLOR, DEFAULT_FILL_COLOR
from libs.canvas import Canvas, CURSOR_DEFAULT
from libs.zoomWidget import ZoomWidget
from libs.labelDialog import LabelDialog
from libs.colorDialog import ColorDialog
from libs.labelFile import LabelFile, LabelFileError
from libs.toolBar import ToolBar
from libs.pascal_voc_io import PascalVocReader, PascalVocWriter
from libs.pascal_voc_io import XML_EXT
from libs.yolo_io import YoloReader
from libs.yolo_io import TXT_EXT
from libs.ustr import ustr
from libs.version import __version__

from server_request import Requests

__appname__ = 'labelImg'

import threading
from functools import wraps

from libs.constants import *


from apscheduler.triggers.interval import IntervalTrigger


def delay(delay=0.):
    """
    Decorator delaying the execution of a function for a while.
    """
    def wrap(f):
        @wraps(f)
        def delayed(*args, **kwargs):
            timer = threading.Timer(delay, f, args=args, kwargs=kwargs)
            timer.start()
        return delayed
    return wrap
class Timer():
    toClearTimer = False
    def setTimeout(self, fn, time):
        isInvokationCancelled = False
        @delay(time)
        def some_fn():
                if (self.toClearTimer is False):
                        fn()
                else:
                    print('Invokation is cleared!')        
        some_fn()
        return isInvokationCancelled
    def setClearTimer(self):
        self.toClearTimer = True

# Utility functions and classes.

def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))

def util_qt_strlistclass():
    return QStringList if have_qstring() else list

class StartQ(QDialog):
    def __init__(self, parent=None):
        super(StartQ, self).__init__(parent)

        self.buttonStart = QPushButton('Start', self)
        self.buttonStart.clicked.connect(self.handleStart)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Click to start the labeling process'))
        layout.addWidget(self.buttonStart)

        self.parent = parent

    def handleStart(self):
        """self.parent.fileListWidget.clear()
        if self.parent.status_process == 'NOT_START':
            for anno_path in self.parent.mImgList:
                item = QListWidgetItem(anno_path)
                self.parent.fileListWidget.addItem(item)

            if self.parent.openNextImg():
                self.parent.status_process = 'START'
                self.accept()"""
        if self.parent.startDialog():
            self.accept()

    def closeEvent(self, evnt):
        self.parent.finishDialog(popup=False)
        evnt.ignore()
        sys.exit()
        #self.setWindowState(Qt.WindowMinimized)

class SelectRoiQ(QDialog):
    class DrawRoiQ(QLabel):
        button_active = pyqtSignal(bool)
        def __init__(self, parent, margins):
            super(SelectRoiQ.DrawRoiQ, self).__init__(parent)
            self.parent = parent
            self.positions = []
            self.pixmap = None
            self.margins = margins
            self.setContentsMargins(*self.margins)
            self.curr_idx = 0
            self.detect_position = False

        def paintEvent(self, event):
            super().paintEvent(event)
            qp = QPainter(self)
            if self.pixmap is not None:
                qsize = QSize(self.size().width() - self.margins[0] - self.margins[2], self.size().height() - self.margins[1] - self.margins[3])
                self.pixmap_resized = self.pixmap.scaled(qsize, Qt.KeepAspectRatio)
                qp.setBrush(QColor(0, 0, 0))
                qp.drawRect(0, 0, self.width(), self.height())
                qp.drawPixmap(self.margins[0], self.margins[1], self.pixmap_resized)

                poly = QPolygonF()
                for real_x, real_y in self.positions:
                    pix_x = int(real_x / self.image_size[0] * self.pixmap_resized.width() + self.margins[0])
                    pix_y = int(real_y / self.image_size[1] * self.pixmap_resized.height() + self.margins[1])
                    poly.append(QPointF(pix_x, pix_y))
                
                qp.setBrush(QColor(255, 255, 0, 50))
                qp.drawPolygon(poly)                    
                
                rad = int(max(9, 0.01 * self.pixmap_resized.width()))
                for i, p in enumerate(poly):
                    if self.curr_idx == i and self.detect_position:
                        qp.setBrush(QColor(0, 255, 0))
                    else:
                        qp.setBrush(QColor(255, 0, 0))

                    qp.drawEllipse(p.x() - rad // 2, p.y() - rad // 2, rad, rad)
            qp.end()

            self.button_active.emit(len(self.positions) >= 4)

        def load_image(self, im):
            self.positions = []
            self.image_size = im.size().width(), im.size().height()
            self.pixmap = QPixmap.fromImage(im)

            """
            asp_ratio = self.pixmap.width() / self.pixmap.height()
            if asp_ratio > 0: # ajuste por width
                new_height = self.width() * asp_ratio
                self.setGeometry(QRect(self.x(), self.y(), self.width(), new_height)) 

            else: # ajuste por height
                new_width = self.height() / asp_ratio
                self.setGeometry(QRect(self.x(), self.y(), new_width, self.height()))
            """

        def get_mouse_positions(self, event):
            x = event.pos().x()
            y = event.pos().y()

            real_pos_x = (x - self.margins[0]) / self.pixmap_resized.width() * self.image_size[0]
            real_pos_y = (y - self.margins[1]) / self.pixmap_resized.height() * self.image_size[1]

            return real_pos_x, real_pos_y

        def mousePressEvent(self, event):
            has_edit = -1
            actual_pos = self.get_mouse_positions(event)
            for i, (x, y) in enumerate(self.positions):
                if ((x - actual_pos[0])**2 + (y - actual_pos[1]) ** 2) < (10**2):
                    has_edit = i

            #if event.button() == Qt.RightButton:
            #    del self.positions[has_edit]

            if event.button() == Qt.LeftButton:
                self.detect_position = True
                if has_edit >= 0:
                    self.curr_idx = has_edit
                else:
                    self.curr_idx = len(self.positions)
                    self.positions.append(actual_pos)
            self.repaint()

        def mouseMoveEvent(self, event):
            if self.detect_position:
                self.positions[self.curr_idx] = self.get_mouse_positions(event)
            self.repaint()

        def mouseReleaseEvent(self, event):
            self.detect_position = False
            self.repaint()

        def reset_draw(self):
            self.positions = []
            self.repaint()

    def __init__(self, parent=None, already_done=False):
        super(SelectRoiQ, self).__init__(parent)
        self.already_done = already_done

        self.buttonStart = QPushButton('Done', self)
        self.buttonStart.clicked.connect(self.handleStart)
        self.buttonStart.setEnabled(False)

        self.label = SelectRoiQ.DrawRoiQ(self, (40, 40, 40, 40)) #QLabel()
        self.label.button_active.connect(self.buttonStart.setEnabled)
        #self.label.mousePressEvent = self.get_position
        self.label.setMinimumSize(1200, 800)

        self.buttonReset = QPushButton('Reset', self)
        self.buttonReset.clicked.connect(self.label.reset_draw)

        layout = QVBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(QLabel('Delimite the roi of the field.'))
        layout.addWidget(self.buttonReset)
        layout.addWidget(self.buttonStart)

        self.parent = parent

    def load_image(self, im):
        self.label.load_image(im)
        #self.update()

    def handleStart(self):
        if len(self.label.positions) >= 4:
            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Information)
            msgBox.setText("Are you sure?")
            msgBox.setWindowTitle("ROI confirmation")
            msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            if msgBox.exec() == QMessageBox.Ok:
                self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Backspace:
            self.label.positions.pop()
        elif event.key() == Qt.Key_Escape:
            self.closeEvent(event)

        super(SelectRoiQ, self).keyPressEvent(event)
        self.label.repaint()

    def closeEvent(self, evnt):
        if not self.already_done:
            self.parent.finishDialog(popup=False)
            evnt.ignore()
            sys.exit()

    def get_roi(self):
        return self.label.positions

class TimeoutQ(QDialog):
    def __init__(self, object_parent, parent=None):
        super(TimeoutQ, self).__init__(parent)
        self.setModal(True)

        self.buttonStart = QPushButton('Continue', self)
        self.buttonStart.clicked.connect(self.handleStart)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('The tagging time of an image has been exceeded. Press continue to get another one.'))
        layout.addWidget(self.buttonStart)

        self.object_parent = object_parent
        self.parent = parent

    def handleStart(self):
        self.accept()

    def closeEvent(self, evnt):
        self.parent.finishDialog(popup=False)
        evnt.ignore()
        sys.exit()
        #self.setWindowState(Qt.WindowMinimized)

class WindowMixin(object):

    def menu(self, title, actions=None):
        menu = self.menuBar().addMenu(title)
        if actions:
            addActions(menu, actions)
        return menu

    def toolbar(self, title, actions=None):
        toolbar = ToolBar(title)
        toolbar.setObjectName(u'%sToolBar' % title)
        # toolbar.setOrientation(Qt.Vertical)
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        if actions:
            addActions(toolbar, actions)
        self.addToolBar(Qt.LeftToolBarArea, toolbar)
        return toolbar

# PyQt5: TypeError: unhashable type: 'QListWidgetItem'
class HashableQListWidgetItem(QListWidgetItem):

    def __init__(self, *args):
        super(HashableQListWidgetItem, self).__init__(*args)

    def __hash__(self):
        return hash(id(self))

class MainWindow(QMainWindow, WindowMixin):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))
    next_image_slot = pyqtSignal()

    def __init__(self, defaultFilename=None, defaultPrefdefClassFile=None, defaultSaveDir=None,annotation_endpoint=None):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)
        self.status_process = 'NOT_START'
        
        self.annotation_endpoint = annotation_endpoint

        # Scheduler
        self.scheduler = BackgroundScheduler()
        
        def _set_active_job():
            response, description = Requests.User.set_active(datetime.datetime.utcnow(), self.annotation_endpoint)
        self.active_job = self.scheduler.add_job(_set_active_job, IntervalTrigger(seconds = 5 * 60), id='job_set_active')
        self.scheduler.start()
        self.active_job.pause()

        # Load setting in the main thread
        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        # Save as Pascal voc xml
        self.defaultSaveDir = defaultSaveDir
        self.usingPascalVocFormat = True
        self.usingYoloFormat = False

        # For loading all image under a directory
        self.annotationDict = {}
        self.mImgList = []
        self.dirname = None
        self.labelHist = OrderedDict()
        self.lastOpenDir = None

        # Andreu. For working with video files
        self.match_id = ''
        self.vid_filename = ''
        self.extension = ''
        self.cam_type = ''
        self.cam_type2 = ''  # Complete name (e.g. right)
        self.vid = None
        self.current_frame = 0
        self.skip_frames = 0
        self.set_skip_frame = False
        self.set_current_frame = False
        self.skip_frame_rate = 0
        self.time_spent = 0
        self.zoom_amount = 10

        # Name for the saved file (both image and xml)
        self.file_name = ''
        ###
        self.visibilityShapes = True

        # Whether we need to save or not.
        self.dirty = False
        self.enable_nolabels = False

        self._noSelectionSlot = False
        self._beginner = True
        self.screencastViewer = self.getAvailableScreencastViewer()
        self.screencast = "https://youtu.be/p0nR2YsCY_U"

        # Load predefined classes to the list
        self.loadPredefinedClasses(defaultPrefdefClassFile)

        # Main widgets and related state.
        self.labelDialog = LabelDialog(parent=self, listItem=list(self.labelHist.keys()))

        self.itemsToShapes = {}
        self.shapesToItems = {}
        self.prevLabelText = ''

        listLayout = QVBoxLayout()
        listLayout.setContentsMargins(0, 0, 0, 0)

        # Andreu
        # Create a text box for indicating the frame number
        self.frame_current = QLabel()
        self.frame_current.setText(u'Current frame: ' + str(self.current_frame))
        ###

        # Create a widget for using default label
        self.useDefaultLabelCheckbox = QCheckBox(u'Use default label')
        self.useDefaultLabelCheckbox.setChecked(False)
        self.defaultLabelTextLine = QLineEdit()
        useDefaultLabelQHBoxLayout = QHBoxLayout()
        useDefaultLabelQHBoxLayout.addWidget(self.useDefaultLabelCheckbox)
        useDefaultLabelQHBoxLayout.addWidget(self.defaultLabelTextLine)
        useDefaultLabelContainer = QWidget()
        useDefaultLabelContainer.setLayout(useDefaultLabelQHBoxLayout)

        # Create a widget for edit and diffc button
        self.diffcButton = QCheckBox(u'difficult')
        self.diffcButton.setChecked(False)
        self.diffcButton.stateChanged.connect(self.btnstate)
        self.editButton = QToolButton()
        self.editButton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)


        self.noLabelsOrEdit = QPushButton('No labels', self)
        self.noLabelsOrEdit.clicked.connect(self.enableNoLabels)

        # Add some of widgets to listLayout
        # Andreu
        listLayout.addWidget(self.noLabelsOrEdit)
        listLayout.addWidget(self.frame_current)
        ###
        listLayout.addWidget(self.editButton)
        listLayout.addWidget(self.diffcButton)
        listLayout.addWidget(useDefaultLabelContainer)

        # Create and add a widget for showing current label items
        self.labelList = QListWidget()
        labelListContainer = QWidget()
        labelListContainer.setLayout(listLayout)
        self.labelList.itemActivated.connect(self.labelSelectionChanged)
        self.labelList.itemSelectionChanged.connect(self.labelSelectionChanged)
        self.labelList.itemDoubleClicked.connect(self.editLabel)
        # Connect to itemChanged to detect checkbox changes.
        self.labelList.itemChanged.connect(self.labelItemChanged)
        listLayout.addWidget(self.labelList)

        self.dock = QDockWidget(u'Box Labels', self)
        self.dock.setObjectName(u'Labels')
        self.dock.setWidget(labelListContainer)

        # Tzutalin 20160906 : Add file list and dock to move faster
        self.fileListWidget = QListWidget()
        self.fileListWidget.itemDoubleClicked.connect(self.fileitemDoubleClicked)
        filelistLayout = QVBoxLayout()
        filelistLayout.setContentsMargins(0, 0, 0, 0)
        filelistLayout.addWidget(self.fileListWidget)
        fileListContainer = QWidget()
        fileListContainer.setLayout(filelistLayout)
        self.filedock = QDockWidget(u'Current File List', self)
        self.filedock.setObjectName(u'Files')
        self.filedock.setWidget(fileListContainer)

        self.zoomWidget = ZoomWidget()
        self.colorDialog = ColorDialog(parent=self)

        self.canvas = Canvas(parent=self, label_img=self)
        self.canvas.zoomRequest.connect(self.zoomRequest)

        split_info = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(True)
        self.scrollBars = {
            Qt.Vertical: scroll.verticalScrollBar(),
            Qt.Horizontal: scroll.horizontalScrollBar()
        }
        self.scrollArea = scroll
        self.canvas.scrollRequest.connect(self.scrollRequest)
        self.canvas.scrollRequestPer.connect(self.scrollRequestPer)

        self.canvas.newShape.connect(self.newShape)
        self.canvas.shapeMoved.connect(self.setDirty)
        self.canvas.selectionChanged.connect(self.shapeSelectionChanged)
        self.canvas.drawingPolygon.connect(self.toggleDrawingSensitive)

        split_sport = QHBoxLayout()
        split_sport.addWidget(QLabel("Sport:"))
        self.actual_sport = QLabel("None")
        self.actual_sport.setAlignment(Qt.AlignRight) #| Qt.AlignVCenter)
        split_sport.addWidget(self.actual_sport)

        split_camera = QHBoxLayout()
        split_camera.addWidget(QLabel("Camera:"))
        self.actual_camera = QLabel("None")
        self.actual_camera.setAlignment(Qt.AlignRight) #| Qt.AlignVCenter)
        split_camera.addWidget(self.actual_camera)

        split_frame_tags = QHBoxLayout()
        split_frame_tags.addWidget(QLabel("Frame Tags:"))
        self.frame_tags_group = QDialogButtonBox(Qt.Horizontal)
        self.frame_tags_group.setOrientation(Qt.Horizontal)
        split_frame_tags.addWidget(self.frame_tags_group)

        split_info.addLayout(split_sport)
        split_info.addLayout(split_camera)
        split_info.addLayout(split_frame_tags)
        split_info.addWidget(scroll)
        split_info_w = QWidget()
        split_info_w.setLayout(split_info)

        self.setCentralWidget(split_info_w)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        # Tzutalin 20160906 : Add file list and dock to move faster
        self.addDockWidget(Qt.RightDockWidgetArea, self.filedock)
        self.filedock.setFeatures(QDockWidget.DockWidgetFloatable)

        self.dockFeatures = QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetFloatable
        self.dock.setFeatures(self.dock.features() ^ self.dockFeatures)

        # Actions
        action = partial(newAction, self)
        quit = action('&Quit', self.close,
                      'Ctrl+Q', 'quit', u'Quit application')
        self.finish_process = action('&Finish', self.finishDialog,
                         'Ctrl+u', 'open', u'Finish')

        openPrevImg = action('&Prev Image', self.openPrevImg,
                             'a', 'prev', u'Open Prev')

        change_zoom = action('&Change Zoom', self.change_zoom,
                             'Shift+z', 'change_zoom', u'Change Zoom')

        save = action('&Save and next', self.saveAndNextDialog,
                      'd', 'save', u'Send server labels', enabled=False)
        
        color1 = action('Box Line Color', self.chooseColor1,
                        'Ctrl+L', 'color_line', u'Choose Box line color')

        color3 = action('Bakground Color', self.chooseColor3,
                'Ctrl+Shift+B', 'color', u'Choose background color')

        editMode = action('&Edit\nRectBox', self.setEditMode,
                          'Ctrl+J', 'edit', u'Move and edit Boxs', enabled=False)

        create = action('Create\nRectBox', partial(self.createShape, 0),
                        'w', 'new', u'Draw a new Box', enabled=True)

        toggle_visibility = action('Visibility Toggle', partial(self.toggleVisibility, None),
                        'h', 'visibility', u'Toggle visibility shapes', enabled=True)

        create_buttons = OrderedDict()
        for i, n in enumerate(self.labelHist.keys()):
            idx = i + 1
            create_buttons['create_button_'  + n] = action('Create\n' + n.capitalize(), partial(self.createShape, idx),
                        str(idx), 'new', u'Draw a new Box', enabled=False)

        delete = action('Delete\nRectBox', self.deleteSelectedShape,
                        'Delete', 'delete', u'Delete', enabled=False)
        
        clear = action('&Clear\nBoxes', self.deleteAllShapes,
                        'Ctrl+Shift+C', 'clear', u'Clear all Boxes', enabled=True)

        copy = action('&Duplicate\nRectBox', self.copySelectedShape,
                      'Ctrl+D', 'copy', u'Create a duplicate of the selected Box',
                      enabled=False)

        hideAll = action('&Hide\nRectBox', partial(self.toggleVisibility, False),
                         'Ctrl+H', 'hide', u'Hide all Boxs',
                         enabled=False)


        showAll = action('&Show\nRectBox', partial(self.toggleVisibility, True),
                         'Ctrl+A', 'hide', u'Show all Boxs',
                         enabled=False)

        help = action('&Tutorial', self.showTutorialDialog, None, 'help', u'Show demos')
        showInfo = action('&Information', self.showInfoDialog, None, 'help', u'Information')

        zoom = QWidgetAction(self)
        zoom.setDefaultWidget(self.zoomWidget)
        self.zoomWidget.setWhatsThis(
            u"Zoom in or out of the image. Also accessible with"
            " %s and %s from the canvas." % (fmtShortcut("Ctrl+[-+]"),
                                             fmtShortcut("Ctrl+Wheel")))
        self.zoomWidget.setEnabled(False)

        zoomIn = action('Zoom &In', partial(self.addZoom, self.zoom_amount),
                        'Ctrl++', 'zoom-in', u'Increase zoom level', enabled=False)
        zoomOut = action('&Zoom Out', partial(self.addZoom, -10),
                         'Ctrl+-', 'zoom-out', u'Decrease zoom level', enabled=False)
        zoomOrg = action('&Original size', partial(self.setZoom, 100),
                         'Ctrl+=', 'zoom', u'Zoom to original size', enabled=False)
        fitWindow = action('&Fit Window', self.setFitWindow,
                           'Ctrl+R', 'fit-window', u'Zoom follows window size',
                           checkable=True, enabled=False)
        fitWidth = action('Fit &Width', self.setFitWidth,
                          'Ctrl+Shift+F', 'fit-width', u'Zoom follows window width',
                          checkable=True, enabled=False)
        # Group zoom controls into a list for easier toggling.
        zoomActions = (self.zoomWidget, zoomIn, zoomOut,
                       zoomOrg, fitWindow, fitWidth)
        self.zoomMode = self.MANUAL_ZOOM
        self.scalers = {
            self.FIT_WINDOW: self.scaleFitWindow,
            self.FIT_WIDTH: self.scaleFitWidth,
            # Set to one to scale to 100% when loading files.
            self.MANUAL_ZOOM: lambda: 1,
        }

        edit = action('&Edit Label', self.editLabel,
                      'E', 'edit', u'Modify the label of the selected Box',
                      enabled=False)
        self.editButton.setDefaultAction(edit)

        shapeLineColor = action('Shape &Line Color', self.chshapeLineColor,
                                icon='color_line', tip=u'Change the line color for this specific shape',
                                enabled=False)
        shapeFillColor = action('Shape &Fill Color', self.chshapeFillColor,
                                icon='color', tip=u'Change the fill color for this specific shape',
                                enabled=False)

        labels = self.dock.toggleViewAction()
        labels.setText('Show/Hide Label Panel')
        labels.setShortcut('Ctrl+Shift+L')

        # Lavel list context menu.
        labelMenu = QMenu()
        addActions(labelMenu, (edit, delete))
        self.labelList.setContextMenuPolicy(Qt.CustomContextMenu)
        self.labelList.customContextMenuRequested.connect(
            self.popLabelListMenu)

        # Store actions for further handling.
        self.actions = struct(save=save,
                              lineColor=color1, backgroundColor=color3, create=create, create_buttons=create_buttons,
                              delete=delete, edit=edit, copy=copy, clear=clear,
                              editMode=editMode,
                              shapeLineColor=shapeLineColor, shapeFillColor=shapeFillColor,
                              zoom=zoom, zoomIn=zoomIn, zoomOut=zoomOut, zoomOrg=zoomOrg,
                              fitWindow=fitWindow, fitWidth=fitWidth,
                              zoomActions=zoomActions,
                              fileMenuActions=(
                                  quit),
                              beginner=(),
                              editMenu=(edit, copy, delete, clear,
                                        None, color1, color3),
                              beginnerContext=(create, create_buttons, edit, copy, delete, clear),
                              onLoadActive=(
                                  create, create_buttons, editMode),
                              onShapesPresent=(hideAll, showAll, toggle_visibility))

        self.menus = struct(
            file=self.menu('&File'),
            edit=self.menu('&Edit'),
            view=self.menu('&View'),
            help=self.menu('&Help'),
            recentFiles=QMenu('Open &Recent'),
            labelList=labelMenu)

        # Auto saving : Enable auto saving if pressing next
        self.autoSaving = QAction("Auto Saving", self)
        self.autoSaving.setCheckable(True)
        self.autoSaving.setChecked(settings.get(SETTING_AUTO_SAVE, True))
        # Sync single class mode from PR#106
        self.singleClassMode = QAction("Single Class Mode", self)
        self.singleClassMode.setShortcut("Ctrl+Shift+S")
        self.singleClassMode.setCheckable(True)
        self.singleClassMode.setChecked(settings.get(SETTING_SINGLE_CLASS, False))
        self.lastLabel = None
        # Add option to enable/disable labels being painted at the top of bounding boxes
        self.paintLabelsOption = QAction("Paint Labels", self)
        self.paintLabelsOption.setShortcut("Ctrl+Shift+P")
        self.paintLabelsOption.setCheckable(True)
        self.paintLabelsOption.setChecked(settings.get(SETTING_PAINT_LABEL, False))
        self.paintLabelsOption.triggered.connect(self.togglePaintLabelsOption)

        addActions(self.menus.file,
                   (save, self.menus.recentFiles, quit))
        addActions(self.menus.help, (help, showInfo))
        addActions(self.menus.view, (
            self.autoSaving,
            self.singleClassMode,
            self.paintLabelsOption,
            labels, None,
            hideAll, showAll, None,
            toggle_visibility,
            zoomIn, zoomOut, zoomOrg, None,
            fitWindow, fitWidth))

        self.menus.file.aboutToShow.connect(self.updateFileMenu)

        # Custom context menu for the canvas widget:
        addActions(self.canvas.menus[0], self.actions.beginnerContext)
        addActions(self.canvas.menus[1], (
            action('&Copy here', self.copyShape),
            action('&Move here', self.moveShape)))

        self.tools = self.toolbar('Tools')
        # Andreu
        self.actions.beginner = (
            self.finish_process,
            save, openPrevImg,
            change_zoom,
            None, create, copy, delete, clear, None, zoomIn, zoom, zoomOut, fitWindow, fitWidth)
        
        self.statusBar().showMessage('%s started.' % __appname__)
        self.statusBar().show()

        # Application state.
        self.image = QImage()
        self.filePath = ustr(defaultFilename)
        self.recentFiles = []
        self.maxRecent = 7
        self.lineColor = None
        self.fillColor = None
        self.backgroundColor = None
        self.canvas.backgroundColor = None
        self.zoom_level = 100
        self.fit_window = False
        # Add Chris
        self.difficult = False

        # Andreu. To keep track of changes
        self.img_full_path_save = ''
        self.xml_full_path_save = ''
        # For annotating with 1,2,3,4
        self.label_default = 0
        # Prediction
        self.predict_mode = 'disabled'
        self.predict_mode_loaded = 'disabled'
        self.predict_mode_net_cfg = None
        self.predict_mode_net_weights = None
        self.predict_mode_net_names = None
        self.predict_resources = Path(__file__).parent / 'resources_dl'
        str_predict_path = str(self.predict_resources.absolute())
        self.predict_list = ('disabled', ) + tuple(filter(lambda x: os.path.isdir(os.path.join(str_predict_path, x)), os.listdir(str_predict_path)))
        self.cv_img = None

        ## Fix the compatible issue for qt4 and qt5. Convert the QStringList to python list
        if settings.get(SETTING_RECENT_FILES):
            if have_qstring():
                recentFileQStringList = settings.get(SETTING_RECENT_FILES)
                self.recentFiles = [ustr(i) for i in recentFileQStringList]
            else:
                self.recentFiles = recentFileQStringList = settings.get(SETTING_RECENT_FILES)

        size = settings.get(SETTING_WIN_SIZE, QSize(600, 500))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)
        saveDir = ustr(settings.get(SETTING_SAVE_DIR, None))
        self.lastOpenDir = ustr(settings.get(SETTING_LAST_OPEN_DIR, None))
        if self.defaultSaveDir is None and saveDir is not None and os.path.exists(saveDir):
            self.defaultSaveDir = saveDir
            self.statusBar().showMessage('%s started. Annotation will be saved to %s' %
                                         (__appname__, self.defaultSaveDir))
            self.statusBar().show()

        self.restoreState(settings.get(SETTING_WIN_STATE, QByteArray()))
        Shape.line_color = self.lineColor = QColor(settings.get(SETTING_LINE_COLOR, DEFAULT_LINE_COLOR))
        Shape.fill_color = self.fillColor = QColor(settings.get(SETTING_FILL_COLOR, DEFAULT_FILL_COLOR))
        self.canvas.setDrawingColor(self.lineColor)
        # Add chris
        Shape.difficult = self.difficult

        def xbool(x):
            if isinstance(x, QVariant):
                return x.toBool()
            return bool(x)

        # Populate the File menu dynamically.
        self.updateFileMenu()

        # Since loading the file may take some time, make sure it runs in the background.
        if self.filePath:
            self.queueEvent(partial(self.loadAnnotation, self.filePath or ""))

        # Callbacks:
        self.zoomWidget.valueChanged.connect(self.paintCanvas)

        self.populateModeActions()

        # Display cursor coordinates at the right of status bar
        self.labelCoordinates = QLabel('')
        self.statusBar().addPermanentWidget(self.labelCoordinates)

        # Open Dir if deafult file
        if self.filePath and os.path.isdir(self.filePath):
            self.openDirDialog(dirpath=self.filePath)

        #self.toggleAllButtons(False)
        self.labelFile = None
        self.tagDict = {}
        self.timeout_popup = TimeoutQ(self)
        self.select_roi = SelectRoiQ(self)
        self.timeout_image = QTimer(self)
        self.next_image_slot.connect(self.open_next_image, type=Qt.QueuedConnection)

        self.timeout_image.timeout.connect(self.timeout_event, type=Qt.QueuedConnection)
        self.timeout_image.setSingleShot(True)

        StartQ(self).exec_()

    def timeout_event(self):
        if self.labelFile is None or self.labelFile is not None and self.labelFile.idx != self.last_ref_id:
            return
        self.remove_file_from_filelist(self.last_ref_id)
        if self.select_roi.isVisible():
            self.select_roi.reject()
        self.timeout_popup.exec_()
        self.next_image_slot.emit()


    ## Support Functions ##
    def set_format(self, save_format):
        if save_format == FORMAT_PASCALVOC:
            self.actions.save_format.setText(FORMAT_PASCALVOC)
            self.actions.save_format.setIcon(newIcon("format_voc"))
            self.usingPascalVocFormat = True
            self.usingYoloFormat = False
            LabelFile.suffix = XML_EXT

        elif save_format == FORMAT_YOLO:
            self.actions.save_format.setText(FORMAT_YOLO)
            self.actions.save_format.setIcon(newIcon("format_yolo"))
            self.usingPascalVocFormat = False
            self.usingYoloFormat = True
            LabelFile.suffix = TXT_EXT

    def change_format(self):
        #if self.usingPascalVocFormat: self.set_format(FORMAT_YOLO)
        #elif self.usingYoloFormat: self.set_format(FORMAT_PASCALVOC)
        g=2

    def noShapes(self):
        return not self.itemsToShapes

    def populateModeActions(self):
        tool, menu = self.actions.beginner, self.actions.beginnerContext
        self.tools.clear()
        addActions(self.tools, tool)
        self.canvas.menus[0].clear()
        addActions(self.canvas.menus[0], menu)
        self.menus.edit.clear()
        actions = [self.actions.create] + list(self.actions.create_buttons.values()) if self.beginner()\
            else [self.actions.editMode]
        actions = tuple(actions)
        addActions(self.menus.edit, actions + self.actions.editMenu)

    def setBeginner(self):
        self.tools.clear()
        addActions(self.tools, self.actions.beginner)

    def setDirty(self):
        self.dirty = True
        self.actions.save.setEnabled(True)

    def enableNoLabels(self):
        self.enable_nolabels = True
        self.actions.save.setEnabled(True)

    def setClean(self):
        self.dirty = False
        self.enable_nolabels = False
        self.actions.save.setEnabled(False)
        self.actions.create.setEnabled(True)

    def toggleActions(self, value=True):
        """Enable/Disable widgets which depend on an opened image."""
        for z in self.actions.zoomActions:
            callbackAction(z, lambda x: x.setEnabled(value))
        for action in self.actions.onLoadActive:
            callbackAction(action, lambda x: x.setEnabled(value))

    def queueEvent(self, function):
        QTimer.singleShot(0, function)

    def status(self, message, delay=5000):
        self.statusBar().showMessage(message, delay)

    def resetState(self):
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.labelList.clear()
        self.filePath = None
        self.imageData = None
        self.labelFile = None
        self.canvas.resetState()
        self.labelCoordinates.clear()

    def currentItem(self):
        items = self.labelList.selectedItems()
        if items:
            return items[0]
        return None

    def addRecentFile(self, filePath):
        if filePath in self.recentFiles:
            self.recentFiles.remove(filePath)
        elif len(self.recentFiles) >= self.maxRecent:
            self.recentFiles.pop()
        self.recentFiles.insert(0, filePath)

    def beginner(self):
        return self._beginner

    def getAvailableScreencastViewer(self):
        osName = platform.system()

        if osName == 'Windows':
            return ['C:\\Program Files\\Internet Explorer\\iexplore.exe']
        elif osName == 'Linux':
            return ['xdg-open']
        elif osName == 'Darwin':
            return ['open', '-a', 'Safari']

    ## Callbacks ##
    def showTutorialDialog(self):
        subprocess.Popen(self.screencastViewer + [self.screencast])

    def showInfoDialog(self):
        msg = u'Name:{0} \nApp Version:{1} \n{2} '.format(__appname__, __version__, sys.version_info)
        QMessageBox.information(self, u'Information', msg)

    def checkAndChangeShape(self, idx):
        try:
            shape = None
            #if self.canvas.hShape is not None:
            #    shape = self.canvas.hShape
            if self.canvas.selectedShape is not None:
                shape = self.canvas.selectedShape

            if shape is not None:
                text = list(self.labelHist.keys())[idx - 1]
                item = self.shapesToItems[shape]
                item.setText(text)
                item.setBackground(self.labelHist[text])
                self.labelItemChanged(item)
                return True
        except: # TODO
            pass
        return False

    def createShape(self, idx=0):
        assert self.beginner()
        if not self.checkAndChangeShape(idx):
            self.canvas.setEditing(False)
            # self.actions.create.setEnabled(False)
            self.label_default = idx

    def toggleVisibility(self, visibility=None):
        if visibility is not None:
            self.visibilityShapes = visibility
        else:
            self.visibilityShapes = not self.visibilityShapes            
        self.canvas.update()

    def toggleDrawingSensitive(self, drawing=True):
        """In the middle of drawing, toggling between modes should be disabled."""
        self.actions.editMode.setEnabled(not drawing)
        if not drawing and self.beginner():
            # Cancel creation.
            # print('Cancel creation.')
            self.canvas.setEditing(True)
            self.canvas.restoreCursor()
            for v in self.actions.create_buttons.values():
                v.setEnabled(True)

    def toggleDrawMode(self, edit=True):
        self.canvas.setEditing(edit)
        self.actions.editMode.setEnabled(not edit)

    def setEditMode(self):
        self.toggleDrawMode(True)
        self.labelSelectionChanged()

    def updateFileMenu(self):
        currFilePath = self.filePath

        def exists(filename):
            return os.path.exists(filename)
        menu = self.menus.recentFiles
        menu.clear()
        files = [f for f in self.recentFiles if f !=
                 currFilePath and exists(f)]
        for i, f in enumerate(files):
            icon = newIcon('labels')
            action = QAction(
                icon, '&%d %s' % (i + 1, QFileInfo(f).fileName()), self)
            action.triggered.connect(partial(self.loadRecent, f))
            menu.addAction(action)

    def popLabelListMenu(self, point):
        self.menus.labelList.exec_(self.labelList.mapToGlobal(point))

    def editLabel(self):
        if not self.canvas.editing():
            return
        item = self.currentItem()
        text = self.labelDialog.popUp(item.text())
        if text is not None:
            item.setText(text)
            item.setBackground(self.labelHist[text])
            self.setDirty()

    # Tzutalin 20160906 : Add file list and dock to move faster
    def fileitemDoubleClicked(self, item=None):
        currIndex = self.mImgList.index(ustr(item.text()))
        if currIndex < len(self.mImgList):
            filename = self.mImgList[currIndex]
            if filename:
                self.loadAnnotation(filename)

    # Add chris
    def btnstate(self, item= None):
        """ Function to handle difficult examples
        Update on each object """
        if not self.canvas.editing():
            return

        item = self.currentItem()
        if not item: # If not selected Item, take the first one
            item = self.labelList.item(self.labelList.count()-1)

        difficult = self.diffcButton.isChecked()

        try:
            shape = self.itemsToShapes[item]
        except:
            pass
        # Checked and Update
        try:
            if difficult != shape.difficult:
                shape.difficult = difficult
                self.setDirty()
            else:  # User probably changed item visibility
                self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)
        except:
            pass

    # React to canvas signals.
    def shapeSelectionChanged(self, selected=False):
        if self._noSelectionSlot:
            self._noSelectionSlot = False
        else:
            shape = self.canvas.selectedShape
            if shape:
                self.shapesToItems[shape].setSelected(True)
            else:
                self.labelList.clearSelection()
        self.actions.delete.setEnabled(selected)
        self.actions.copy.setEnabled(selected)
        self.actions.edit.setEnabled(selected)
        self.actions.shapeLineColor.setEnabled(selected)
        self.actions.shapeFillColor.setEnabled(selected)

    def addLabel(self, shape):
        shape.paintLabel = self.paintLabelsOption.isChecked()
        item = HashableQListWidgetItem(shape.label)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setBackground(self.labelHist[shape.label])
        self.itemsToShapes[item] = shape
        self.shapesToItems[shape] = item
        self.labelList.addItem(item)
        for action in self.actions.onShapesPresent:
            callbackAction(action, lambda x: x.setEnabled(True))

    def remLabel(self, shape):
        if shape is None:
            # print('rm empty label')
            return
        item = self.shapesToItems[shape]
        self.labelList.takeItem(self.labelList.row(item))
        del self.shapesToItems[shape]
        del self.itemsToShapes[item]

    def remAllLabel(self):
        self.itemsToShapes.clear()
        self.shapesToItems.clear()
        self.labelList.clear()

    def loadLabels(self, shapes):
        s = []
        self.labelList.clear()
        for label, points, line_color, fill_color, difficult in shapes:
            shape = Shape(label=label)
            for x, y in points:
                shape.addPoint(QPointF(x, y))
            shape.difficult = difficult
            shape.close()
            s.append(shape)

            if line_color:
                shape.line_color = QColor(*line_color)
            else:
                shape.line_color = self.labelHist[label]

            if fill_color:
                shape.fill_color = QColor(*line_color) #fill_color)
                shape.fill_color.setAlpha(DEFAULT_FILL_COLOR.alpha())
            else:
                shape.fill_color = self.labelHist[label]

            self.addLabel(shape)

        self.canvas.loadShapes(s)

    def copySelectedShape(self):
        self.addLabel(self.canvas.copySelectedShape())
        # fix copy and delete
        self.shapeSelectionChanged(True)

    def labelSelectionChanged(self):
        item = self.currentItem()
        if item and self.canvas.editing():
            self._noSelectionSlot = True
            self.canvas.selectShape(self.itemsToShapes[item])
            shape = self.itemsToShapes[item]
            # Add Chris
            self.diffcButton.setChecked(shape.difficult)

    def labelItemChanged(self, item):
        shape = self.itemsToShapes[item]
        label = item.text()
        if label != shape.label:
            shape.label = item.text()
            shape.line_color = self.labelHist[shape.label]
            shape.fill_color = QColor(shape.line_color)
            shape.fill_color.setAlpha(DEFAULT_FILL_COLOR.alpha())
            self.setDirty()
        else:  # User probably changed item visibility
            self.canvas.setShapeVisible(shape, item.checkState() == Qt.Checked)

    # Callback functions:
    def newShape(self):
        """Pop-up and give focus to the label editor.

        position MUST be in global coordinates.
        """
        if (not self.useDefaultLabelCheckbox.isChecked() or not self.defaultLabelTextLine.text()) and self.label_default == 0:
            if len(self.labelHist) > 0:
                self.labelDialog = LabelDialog(
                    parent=self, listItem=list(self.labelHist.keys()))

            # Sync single class mode from PR#106
            if self.singleClassMode.isChecked() and self.lastLabel:
                text = self.lastLabel
            else:
                text = self.labelDialog.popUp(text=self.prevLabelText)
                self.lastLabel = text
        else:
            try:
                text = list(self.labelHist.keys())[self.label_default - 1]
            except:
                text = self.defaultLabelTextLine.text()

        # Add Chris
        self.diffcButton.setChecked(False)
        if text is not None:
            self.prevLabelText = text
            generate_color = self.labelHist[text]
            shape = self.canvas.setLastLabel(text, generate_color, generate_color)
            self.addLabel(shape)
            if self.beginner():  # Switch to edit mode.
                self.canvas.setEditing(True)
                for v in self.actions.create_buttons.values():
                    v.setEnabled(True)
            else:
                self.actions.editMode.setEnabled(True)
            self.setDirty()

            if text not in self.labelHist:
                self.labelHist[text] = getRandomColor(text)
        else:
            # self.canvas.undoLastLine()
            self.canvas.resetAllLines()

    def scrollRequest(self, delta, orientation):
        units = - delta / (8 * 15)
        bar = self.scrollBars[orientation]
        bar.setValue(bar.value() + bar.singleStep() * units)

    def scrollRequestPer(self, delta_x, delta_y):
        def set_scroll(orientation, d):
            bar = self.scrollBars[orientation]
            bar.setValue(bar.value() + int(bar.pageStep() * d))

        set_scroll(Qt.Horizontal, delta_x)
        set_scroll(Qt.Vertical, delta_y)

    def setZoom(self, value):
        self.actions.fitWidth.setChecked(False)
        self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.MANUAL_ZOOM
        self.zoomWidget.setValue(value)

    def addZoom(self, increment=10):
        self.setZoom(self.zoomWidget.value() + increment)

    def getMousePosition(self):
        cursor = QCursor()
        pos = cursor.pos()
        relative_pos = QWidget.mapFromGlobal(self.scrollArea, pos)

        cursor_x = relative_pos.x()
        cursor_y = relative_pos.y()

        w = self.scrollArea.width()
        h = self.scrollArea.height()

        # the scaling from 0 to 1 has some padding
        # you don't have to hit the very leftmost pixel for a maximum-left movement
        move_x = cursor_x / w
        move_y = cursor_y / h

        return QPointF(move_x, move_y)

    def zoomRequest(self, delta):
        # get the current scrollbar positions
        # calculate the percentages ~ coordinates
        h_bar = self.scrollBars[Qt.Horizontal]
        v_bar = self.scrollBars[Qt.Vertical]

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

        w = self.scrollArea.width()
        h = self.scrollArea.height()

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
        # scale = 10
        scale = self.zoom_amount
        self.addZoom(scale * units)

        # get the difference in scrollbar values
        # this is how far we can move
        d_h_bar_max = h_bar.maximum() - h_bar_max
        d_v_bar_max = v_bar.maximum() - v_bar_max

        # get the new scrollbar values
        new_h_bar_value = h_bar.value() + move_x * d_h_bar_max
        new_v_bar_value = v_bar.value() + move_y * d_v_bar_max

        h_bar.setValue(new_h_bar_value)
        v_bar.setValue(new_v_bar_value)

    def setFitWindow(self, value=True):
        if value:
            self.actions.fitWidth.setChecked(False)
        self.zoomMode = self.FIT_WINDOW if value else self.MANUAL_ZOOM
        self.adjustScale()

    def setFitWidth(self, value=True):
        if value:
            self.actions.fitWindow.setChecked(False)
        self.zoomMode = self.FIT_WIDTH if value else self.MANUAL_ZOOM
        self.adjustScale()

    def resizeEvent(self, event):
        if self.canvas and not self.image.isNull()\
           and self.zoomMode != self.MANUAL_ZOOM:
            self.adjustScale()
        super(MainWindow, self).resizeEvent(event)

    def paintCanvas(self):
        assert not self.image.isNull(), "cannot paint null image"
        self.canvas.scale = 0.01 * self.zoomWidget.value()
        self.canvas.adjustSize()
        self.canvas.update()

    def adjustScale(self, initial=False):
        value = self.scalers[self.FIT_WINDOW if initial else self.zoomMode]()
        self.zoomWidget.setValue(int(100 * value))

    def scaleFitWindow(self):
        """Figure out the size of the pixmap in order to fit the main widget."""
        e = 2.0  # So that no scrollbars are generated.
        w1 = self.centralWidget().width() - e
        h1 = self.centralWidget().height() - e
        a1 = w1 / h1
        # Calculate a new scale value based on the pixmap's aspect ratio.
        w2 = self.canvas.pixmap.width() - 0.0
        h2 = self.canvas.pixmap.height() - 0.0
        a2 = w2 / h2
        return w1 / w2 if a2 >= a1 else h1 / h2

    def scaleFitWidth(self):
        # The epsilon does not seem to work too well here.
        w = self.centralWidget().width() - 2.0
        return w / self.canvas.pixmap.width()

    def closeEvent(self, event):
        if not self.mayContinue():
            event.ignore()
        settings = self.settings
        # If it loads images from dir, don't load it at the begining
        if self.dirname is None:
            settings[SETTING_FILENAME] = self.filePath if self.filePath else ''
        else:
            settings[SETTING_FILENAME] = ''

        settings[SETTING_WIN_SIZE] = self.size()
        settings[SETTING_WIN_POSE] = self.pos()
        settings[SETTING_WIN_STATE] = self.saveState()
        settings[SETTING_LINE_COLOR] = self.lineColor
        settings[SETTING_FILL_COLOR] = self.fillColor
        settings[SETTING_RECENT_FILES] = self.recentFiles
        settings[SETTING_ADVANCE_MODE] = not self._beginner
        if self.defaultSaveDir and os.path.exists(self.defaultSaveDir):
            settings[SETTING_SAVE_DIR] = ustr(self.defaultSaveDir)
        else:
            settings[SETTING_SAVE_DIR] = ""

        if self.lastOpenDir and os.path.exists(self.lastOpenDir):
            settings[SETTING_LAST_OPEN_DIR] = self.lastOpenDir
        else:
            settings[SETTING_LAST_OPEN_DIR] = ""

        settings[SETTING_AUTO_SAVE] = self.autoSaving.isChecked()
        settings[SETTING_SINGLE_CLASS] = self.singleClassMode.isChecked()
        settings[SETTING_PAINT_LABEL] = self.paintLabelsOption.isChecked()
        settings.save()

        shutil.rmtree(".tmp", ignore_errors=True)
        self.finishDialog(popup=False)
    ## User Dialogs ##

    def loadRecent(self, filename):
        if self.mayContinue():
            self.loadAnnotation(filename)

    
    def changeSavedirDialog(self, _value=False):
        if self.defaultSaveDir is not None:
            path = ustr(self.defaultSaveDir)
        else:
            path = '.'

        dirpath = ustr(QFileDialog.getExistingDirectory(self,
                                                       '%s - Save annotations to the directory' % __appname__, path,  QFileDialog.ShowDirsOnly
                                                       | QFileDialog.DontResolveSymlinks))

        if dirpath is not None and len(dirpath) > 1:

            if self.filePath is not None:
                # Andreu
                self.defaultSaveDir = os.path.join(dirpath, self.match_id)
                if not os.path.isdir(self.defaultSaveDir):
                    os.mkdir(self.defaultSaveDir)
                self.defaultSaveDir = os.path.join(self.defaultSaveDir, self.cam_type2)
                if not os.path.isdir(self.defaultSaveDir):
                    os.mkdir(self.defaultSaveDir)
                ###
                # self.defaultSaveDir = dirpath

        self.statusBar().showMessage('%s . Annotation will be saved to %s' %
                                     ('Change saved folder', self.defaultSaveDir))
        self.statusBar().show()

    def openAnnotationDialog(self, _value=False):
        if self.filePath is None:
            self.statusBar().showMessage('Please select image first')
            self.statusBar().show()
            return

        path = os.path.dirname(ustr(self.filePath))\
            if self.filePath else '.'
        if self.usingPascalVocFormat:
            filters = "Open Annotation XML file (%s)" % ' '.join(['*.xml'])
            filename = ustr(QFileDialog.getOpenFileName(self,'%s - Choose a xml file' % __appname__, path, filters))
            if filename:
                if isinstance(filename, (tuple, list)):
                    filename = filename[0]
            self.loadPascalXMLByFilename(filename)

    def toggleAllButtons(self, value=True):
        pass
        # for z in self.actions.zoomActions:
        #     callbackAction(z, lambda x: x.setEnabled(value))
        # for action in self.actions.onLoadActive:
        #     callbackAction(action, lambda x: x.setEnabled(value))

        # callbackAction(self.actions.save, lambda x: x.setEnabled(value))
        # callbackAction(self.actions.openPrevImg, lambda x: x.setEnabled(value))

    def startDialog(self, _value=False):
        Requests.User.set_active(datetime.datetime.utcnow(), self.annotation_endpoint)
        #if not self.scheduler.running:
        #    self.scheduler.start()
        self.active_job.resume()
        
        self.fileListWidget.clear()
        if self.status_process == 'NOT_START':
            #self.toggleAllButtons(True)
            for anno_path in self.mImgList:
                item = QListWidgetItem(anno_path)
                self.fileListWidget.addItem(item)

            if self.labelFile is None:
                if self.open_next_image():
                    self.status_process = 'START'
                    return True
            else:
                if self.open_current_image():
                    self.status_process = 'START'
                    return True
        return False

            #if not ((self.dirty or self.enable_nolabels) and self.labelFile is not None):
            #    self.openNextImg()
            #self.finish_process.setText("Finish")
            #self.finish_process.setEnabled(False)

    def finishDialog(self, _value=False, popup=True):
        #print(self.status_process)
        Requests.User.set_active(None, self.annotation_endpoint)
        #if self.scheduler.running:
        #    self.scheduler.shutdown()
        self.active_job.pause()
             
        if self.status_process == 'START':
            #self.toggleAllButtons(False)
            self.status_process = 'NOT_START'
            #self.finish_process.setText("Start")
            if popup:
                StartQ(self).exec_()

    # Andreu
    def frameSkip(self):
        self.skip_frame_rate, _ = QInputDialog.getInt(self, "Frame rate selection",
                                                      "Enter the amount of frames to skip between annotations",
                                                      value=self.skip_frame_rate)

    """def positionInFrame(self):
        self.current_frame, _ = QInputDialog.getInt(self, "Frame positioning", "Enter the frame where to position to",
                                                    value=self.current_frame)
        self.set_current_frame = True
        self.openNextImg()

    def skipFrames(self):
        self.skip_frames, _ = QInputDialog.getInt(self, "Number of frames to skip", "Enter the amount of frames to skip",
                                                  value=0)
        self.set_skip_frame = True
        self.openNextImg()"""

    def change_zoom(self):
        self.zoom_amount, _ = QInputDialog.getInt(self, "Change the amount of zoom", "Enter the amount of zoom when scrolling",
                                                  value=10)

    def verifyImg(self, _value=False):
        # Proceding next image without dialog if having any label
         if self.filePath is not None:
            try:
                self.labelFile.toggleVerify()
            except AttributeError:
                # If the labelling file does not exist yet, create if and
                # re-save it with the verified attribute.
                self.saveFile()
                if self.labelFile != None:
                    self.labelFile.toggleVerify()
                else:
                    return

            self.canvas.verified = self.labelFile.verified
            self.paintCanvas()
            self.saveFile()

    def saveImg(self, img_save_path):
        img = self.convertQImageToMat(self.image)
        cv2.imwrite(img_save_path, img)
        # self.image.save(img_save_path)

    def convertQImageToMat(self, incomingImage):
        '''  Converts a QImage into an opencv MAT format  '''

        incomingImage = incomingImage.convertToFormat(4)

        width = incomingImage.width()
        height = incomingImage.height()

        ptr = incomingImage.bits()
        ptr.setsize(incomingImage.byteCount())
        arr = np.array(ptr).reshape(height, width, 4)  # Copies the data
        return arr

    def openPrevImg(self, _value=False):
        # Proceding prev image without dialog if having any label
        if self.dirty is True or self.enable_nolabels is True:
            self.sendAnnotationServer()

        #if not self.mayContinue():
        #    return

        if len(self.mImgList) <= 0 and self.extension != 'mp4':
            return

        filename = None
        if self.filePath is None:
            return
        
        else:
            currIndex = self.mImgList.index(self.filePath)
            if currIndex - 1 >= 0:
                filename = self.mImgList[currIndex - 1]
        if filename:
            self.loadAnnotation(filename)

    """def openNextImg(self, _value=False):
        if (self.dirty or self.enable_nolabels) and self.labelFile is not None:
            self.sendAnnotationServer()

        if self.filePath is None or self.mImgList.index(self.filePath) + 1 == len(self.mImgList):
            annotation = Requests.Annotation.get()
            if annotation is None:
                self.enableNoLabels()
                #self.status_process = 'NOT_START'
                QMessageBox.warning(
                    self, 'Error', "Actually there aren't available annotations.")
                return False

            anno_path = annotation['file_path']
            annotation_exist = anno_path in self.annotationDict.keys()
            if not annotation_exist:
                item = QListWidgetItem(anno_path)
                self.fileListWidget.addItem(item)
                self.mImgList.append(anno_path)
                self.annotationDict[anno_path] = annotation

            if annotation_exist:
                self.loadAnnotation(anno_path)
            else:
                self.loadAnnotationServer(annotation)
        else:
            filename = None
            
            currIndex = self.mImgList.index(self.filePath)
            if currIndex + 1 <= len(self.mImgList):
                filename = self.mImgList[currIndex + 1]
            if filename:
                self.loadAnnotation(filename)

        return True"""

    def save_current_image(self):
        if (self.dirty or self.enable_nolabels) and self.labelFile is not None:
            self.sendAnnotationServer()
            try:
                self.scheduler.remove_job('job_timeout')
            except:
                pass

    def open_next_image(self):
        if self.filePath is None or self.mImgList.index(self.filePath) + 1 == len(self.mImgList):
            annotation, _ = Requests.Annotation.get(self.annotation_endpoint)
            if annotation is None:
                #self.enableNoLabels()
                #self.status_process = 'NOT_START'
                QMessageBox.warning(
                    self, 'Error', "No available annotations.")
                return False

            anno_path = annotation['file_path']
            annotation_exist = anno_path in self.annotationDict.keys()
            if not annotation_exist:
                item = QListWidgetItem(anno_path)
                self.fileListWidget.addItem(item)
                self.mImgList.append(anno_path)
                self.annotationDict[anno_path] = annotation

            if annotation_exist:
                self.loadAnnotation(anno_path)
            else:
                self.loadAnnotationServer(annotation)
        else:
            filename = None
            
            currIndex = self.mImgList.index(self.filePath)
            if currIndex + 1 <= len(self.mImgList):
                filename = self.mImgList[currIndex + 1]
            if filename:
                self.loadAnnotation(filename)

        return True

    def open_current_image(self):
        return True

    def sendAnnotationServer(self):
        if self.labelFile is None:
            return

        def format_shape(s):
            return dict(label=s.label,
                        line_color=s.line_color.getRgb(),
                        fill_color=s.fill_color.getRgb(),
                        points=[(p.x(), p.y()) for p in s.points],
                        # add chris
                        difficult = s.difficult)

        shapes = [format_shape(shape) for shape in self.canvas.shapes]
        # for label, points, line_color, fill_color, difficult in shapes:
        self.labelFile.shapes = [(shape.label, [(p.x(), p.y()) for p in shape.points], None, None, shape.difficult) for shape in self.canvas.shapes]

        # Can add differrent annotation formats here
        data = self.labelFile.getPascalVocFormat(shapes, self.labelFile.imagePath, self.labelFile.imageShape, self.lineColor.getRgb(), self.fillColor.getRgb())

        if self.dirty:
            last_changes = "annotator"
        else:
            last_changes = None

        frame_tags = []
        aux_frame_tags = self.tagDict[self.labelFile.job_id]
        for tag, active in zip(aux_frame_tags['list'], aux_frame_tags['active']):
            if active:
                frame_tags.append(tag)

        if 'roi' in self.annotationDict[self.filePath]:
            roi = self.annotationDict[self.filePath]['roi']
        else:
            roi = None
        self.annotationDict[self.filePath]['is_already_done'] = True
        response, text, error_or_status = Requests.Annotation.set(self.labelFile.idx, data, last_changes, frame_tags, self.annotation_endpoint, roi=roi)
        if text is not None:
            if not response:
                QMessageBox.warning(
                    self, 'Error', text)

            if error_or_status == 'set_annotation_job_finished' or \
                error_or_status == 'error_set_annotation_removed' or \
                error_or_status == 'error_set_annotation_file_not_exists' or \
                error_or_status == 'error_set_annotation_job_not_process':
                self.remove_job_from_filelist(self.labelFile.job_id)

        self.labelFile = None
        self.last_ref_id = None
        self.timeout_image.stop()
        #self.dirty = False
        #self.enable_nolabels = False
        self.setClean()

        return response

    def remove_job_from_filelist(self, job_id):
        is_curr_path = False
        new_imList = [] 
        for impath in self.mImgList:
            if self.annotationDict[impath]['job_id'] != job_id:
                new_imList.append(impath)
            else:
                if self.filePath == impath:
                    is_curr_path = True
                del self.annotationDict[impath]
        self.mImgList = new_imList

        self.fileListWidget.clear()
        for impath in self.mImgList:
            item = QListWidgetItem(impath)
            self.fileListWidget.addItem(item)

        if is_curr_path:
            self.filePath = None
            self.resetState()
            self.canvas.setEnabled(False)

    def remove_file_from_filelist(self, ref_id):
        is_curr_path = False
        new_imList = [] 
        for impath in self.mImgList:
            if self.annotationDict[impath]['_id'] != ref_id:
                new_imList.append(impath)
            else:
                if self.filePath == impath:
                    is_curr_path = True
                del self.annotationDict[impath]
        self.mImgList = new_imList

        self.fileListWidget.clear()
        for impath in self.mImgList:
            item = QListWidgetItem(impath)
            self.fileListWidget.addItem(item)

        if is_curr_path:
            self.filePath = None
            self.resetState()
            self.canvas.setEnabled(False)

    def open_roi_popup(self, image, annotation, already_done=False):
        # TODO
        # print('Popup canvas roi')
        self.select_roi.load_image(image)
        self.select_roi.already_done = already_done
        if self.select_roi.exec_() > 0:
            annotation['roi'] = self.select_roi.get_roi()
    
    def loadAnnotationServer(self, annotation):
        self.resetState()
        self.canvas.setEnabled(False)

        unicodeFilePath = annotation['file_path']
        if unicodeFilePath and self.fileListWidget.count() > 0:
            index = self.mImgList.index(unicodeFilePath)
            fileWidgetItem = self.fileListWidget.item(index)
            if fileWidgetItem is not None:
                fileWidgetItem.setSelected(True)

        self.labelFile = LabelFile(unicodeFilePath)
        self.annotationDict[unicodeFilePath]['imageShape'] = annotation['image'][2]
        self.annotationDict[unicodeFilePath]['_id'] = annotation['_id']
        self.annotationDict[unicodeFilePath]['labelFile'] = self.labelFile
        self.annotationDict[unicodeFilePath]['sport'] = annotation['sport']
        self.annotationDict[unicodeFilePath]['has_to_label_roi'] = annotation['has_to_label_roi']
        #self.lineColor = QColor(*self.labelFile.lineColor)
        #self.fillColor = QColor(*self.labelFile.fillColor)
        tmp_filepath = os.path.join('.tmp', unicodeFilePath)
        os.makedirs(os.path.dirname(tmp_filepath), exist_ok=True)
        self.cv_img = Images.unpack_im(annotation['image'], 'numpy')
        del annotation['image']
        cv2.imwrite(tmp_filepath, self.cv_img)

        cvImg = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cvImg.shape
        bytesPerLine = 3 * width
        image = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_RGB888)

        if image.isNull():
            self.errorMessage(u'Error opening file',
                              u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
            self.status("Error reading %s" % unicodeFilePath)
            return False

        self.status("Loaded %s" % os.path.basename(unicodeFilePath))
        self.image = image
        self.filePath = unicodeFilePath
        self.canvas.loadPixmap(QPixmap.fromImage(image))
        #if self.labelFile:
        #    self.loadLabels(self.labelFile.shapes)
        #    self.annotationDict[unicodeFilePath]['labelFile'] = self.labelFile

        self.canvas.verified = self.labelFile.verified
        if annotation['xml'] is not None:
            self.labelFile.shapes = self.loadPascalXMLByString(annotation['xml'])
            self.loadLabels(self.labelFile.shapes)
        self.canvas.verified = False

        self.setClean()
        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()
        self.addRecentFile(self.filePath)
        self.toggleActions(True)

        self.imageShape = self.annotationDict[unicodeFilePath]['imageShape']
        self.anno_id = self.annotationDict[unicodeFilePath]['_id']

        self.labelFile.imagePath = self.filePath
        self.labelFile.idx = self.anno_id
        self.labelFile.imageShape = self.imageShape
        self.labelFile.verified = self.canvas.verified
        self.labelFile.job_id = annotation['job_id']
        self.actual_sport.setText(self.annotationDict[unicodeFilePath]['sport'])
        self.actual_camera.setText(self.annotationDict[unicodeFilePath]['camera'])

        if annotation['job_id'] not in self.tagDict:
            self.tagDict[annotation['job_id']] = annotation['default_frame_tags']

        self.reload_tags()
        
        if len(self.labelFile.shapes) > 0:
            self.noLabelsOrEdit.setText('No edit')
        else:
            self.noLabelsOrEdit.setText('No labels')

        self.last_ref_id = self.annotationDict[unicodeFilePath]['_id']
        #milliseconds_timeout = (self.annotationDict[unicodeFilePath]['timeout'].replace(tzinfo=None) - datetime.datetime.utcnow()).seconds * 1000
        milliseconds_timeout = 60 * 10 * 1000
        self.timeout_image.start(milliseconds_timeout)

        if self.annotationDict[unicodeFilePath]['has_to_label_roi']:
            self.open_roi_popup(image, self.annotationDict[unicodeFilePath], already_done=False)

    def loadAnnotation(self, file_path):
        self.resetState()
        self.canvas.setEnabled(False)

        unicodeFilePath = file_path
        if unicodeFilePath and self.fileListWidget.count() > 0:
            index = self.mImgList.index(unicodeFilePath)
            fileWidgetItem = self.fileListWidget.item(index)
            fileWidgetItem.setSelected(True)

        self.labelFile = self.annotationDict[unicodeFilePath]['labelFile']
        #self.lineColor = QColor(*self.labelFile.lineColor)
        #self.fillColor = QColor(*self.labelFile.fillColor)

        self.cv_img = cv2.imread(os.path.join('.tmp', unicodeFilePath))
        cvImg = cv2.cvtColor(self.cv_img, cv2.COLOR_BGR2RGB)
        height, width, channel = cvImg.shape
        bytesPerLine = 3 * width
        image = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_RGB888)

        if image.isNull():
            self.errorMessage(u'Error opening file',
                              u"<p>Make sure <i>%s</i> is a valid image file." % unicodeFilePath)
            self.status("Error reading %s" % unicodeFilePath)
            return False

        self.status("Loaded %s" % os.path.basename(unicodeFilePath))
        self.image = image
        self.filePath = unicodeFilePath
        self.canvas.loadPixmap(QPixmap.fromImage(image))
        if self.labelFile:
            print(self.labelFile.shapes)
            self.loadLabels(self.labelFile.shapes)

        self.canvas.verified = self.labelFile.verified
        self.canvas.verified = False
        
        self.setClean()
        self.canvas.setEnabled(True)
        self.adjustScale(initial=True)
        self.paintCanvas()
        self.addRecentFile(self.filePath)
        self.toggleActions(True)

        self.imageShape = self.annotationDict[unicodeFilePath]['imageShape']
        self.anno_id = self.annotationDict[unicodeFilePath]['_id']

        self.labelFile.imagePath = self.filePath
        self.labelFile.idx = self.anno_id
        self.labelFile.imageShape = self.imageShape
        self.labelFile.verified = self.canvas.verified
        self.labelFile.job_id = self.annotationDict[unicodeFilePath]['job_id']
        self.actual_sport.setText(self.annotationDict[unicodeFilePath]['sport'])
        self.actual_camera.setText(self.annotationDict[unicodeFilePath]['camera'])

        self.reload_tags()

        if len(self.labelFile.shapes) > 0:
            self.noLabelsOrEdit.setText('No edit')
        else:
            self.noLabelsOrEdit.setText('No labels')

        is_already_done = 'is_already_done' in self.annotationDict[unicodeFilePath] and self.annotationDict[unicodeFilePath]['is_already_done']
        if not is_already_done:
            self.last_ref_id = self.annotationDict[unicodeFilePath]['_id']
            #milliseconds_timeout = (self.annotationDict[unicodeFilePath]['timeout'].replace(tzinfo=None) - datetime.datetime.utcnow()).seconds * 1000
            milliseconds_timeout = 60 * 10 * 1000
            self.timeout_image.start(milliseconds_timeout)

        if self.annotationDict[unicodeFilePath]['has_to_label_roi']:
            self.open_roi_popup(image, self.annotationDict[unicodeFilePath], already_done=is_already_done)

            

    def reload_tags(self):
        job_id = self.labelFile.job_id
        tags = self.tagDict[job_id]

        self.frame_tags_group.clear()
        for tag, active in zip(tags['list'], tags['active']):
            def __set_tag(tag, btn):
                val = btn.isChecked()
                #btn.setChecked(val)
                aux = self.tagDict[job_id]
                idx = aux['list'].index(tag)
                if idx >= 0:
                    aux['active'][idx] = val

            button = QPushButton(tag, self)
            button.setCheckable(True)
            button.setChecked(active)
            button.clicked.connect(partial(__set_tag, tag, button))
            self.frame_tags_group.addButton(button, QDialogButtonBox.ActionRole)


    def saveAndNextDialog(self, value=False):
        self.save_current_image()
        self.open_next_image()

        #self.openNextImg()

    def closeFile(self, _value=False):
        if not self.mayContinue():
            return
        self.resetState()
        self.setClean()
        self.toggleActions(False)
        self.canvas.setEnabled(False)
        self.actions.saveAs.setEnabled(False)

    def resetAll(self):
        self.settings.reset()
        self.close()
        proc = QProcess()
        proc.startDetached(os.path.abspath(__file__))

    def mayContinue(self):
        if self.dirty or self.enable_nolabels:
            return self.discardChangesDialog()
        return True
        #return not ((self.dirty or self.enable_nolabels) and not self.discardChangesDialog())

    def discardChangesDialog(self):
        yes, no = QMessageBox.Yes, QMessageBox.No
        msg = u'You have unsaved changes, proceed anyway?'
        return yes == QMessageBox.warning(self, u'Attention', msg, yes | no)

    def errorMessage(self, title, message):
        return QMessageBox.critical(self, title,
                                    '<p><b>%s</b></p>%s' % (title, message))

    def currentPath(self):
        return os.path.dirname(self.filePath) if self.filePath else '.'

    def chooseColor1(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.lineColor = color
            Shape.line_color = color
            self.canvas.setDrawingColor(color)
            self.canvas.update()
            self.setDirty()

    def chooseColor3(self):
        color = self.colorDialog.getColor(self.backgroundColor, u'Choose background color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.backgroundColor = color
            self.canvas.backgroundColor = color
            self.paintCanvas()

    def deleteSelectedShape(self):
        self.remLabel(self.canvas.deleteSelected())
        self.setDirty()
        if self.noShapes():
            for action in self.actions.onShapesPresent:
                callbackAction(action, lambda x: x.setEnabled(False))

    def deleteAllShapes(self):
        self.remAllLabel()
        self.canvas.deleteAll()
        self.setDirty()
        for action in self.actions.onShapesPresent:
            callbackAction(action, lambda x: x.setEnabled(False))

    def chshapeLineColor(self):
        color = self.colorDialog.getColor(self.lineColor, u'Choose line color',
                                          default=DEFAULT_LINE_COLOR)
        if color:
            self.canvas.selectedShape.line_color = color
            self.canvas.update()
            self.setDirty()

    def chshapeFillColor(self):
        color = self.colorDialog.getColor(self.fillColor, u'Choose fill color',
                                          default=DEFAULT_FILL_COLOR)
        if color:
            self.canvas.selectedShape.fill_color = color
            self.canvas.update()
            self.setDirty()

    def copyShape(self):
        self.canvas.endMove(copy=True)
        self.addLabel(self.canvas.selectedShape)
        self.setDirty()

    def moveShape(self):
        self.canvas.endMove(copy=False)
        self.setDirty()

    def loadPredefinedClasses(self, predefClassesFile):
        if os.path.exists(predefClassesFile) is True:
            with codecs.open(predefClassesFile, 'r', 'utf8') as f:
                for line in f:
                    line = line.strip()
                    if self.labelHist is None:
                        self.labelHist = OrderedDict()
                    else:
                        name, color = line.split(' ')
                        self.labelHist[name] = parseColorFromHex(color)

    def loadPascalXMLByString(self, xmlStr):
        tVocParseReader = PascalVocReader(xmlStr, is_str=True)
        shapes = tVocParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tVocParseReader.verified
        return shapes

    def loadYOLOTXTByFilename(self, txtPath):
        if self.filePath is None:
            return
        if os.path.isfile(txtPath) is False:
            return

        self.set_format(FORMAT_YOLO)
        tYoloParseReader = YoloReader(txtPath, self.image)
        shapes = tYoloParseReader.getShapes()
        self.loadLabels(shapes)
        self.canvas.verified = tYoloParseReader.verified

    def togglePaintLabelsOption(self):
        paintLabelsOptionChecked = self.paintLabelsOption.isChecked()
        for shape in self.canvas.shapes:
            shape.paintLabel = paintLabelsOptionChecked


def inverted(color):
    return QColor(*[255 - v for v in color.getRgb()])


def read(filename, default=None):
    try:
        with open(filename, 'rb') as f:
            # print('Andreu: opened ' + filename)
            return f.read()

    except:
        # print('Andreu: Error reading file ' + filename)
        return default


def get_main_app(app, argv=[], endpoint=None):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile saveDir
    win = MainWindow(argv[1] if len(argv) >= 2 else None,
                     argv[2] if len(argv) >= 3 else os.path.join(
                         os.path.dirname(sys.argv[0]),
                         'data', 'predefined_classes.txt'),
                     argv[3] if len(argv) >= 4 else None,
                     annotation_endpoint=endpoint)
    win.show()
    return app, win


def main():
    '''construct main app and run it'''
    app, _win = get_main_app(sys.argv)
    return app.exec_()


if __name__ == '__main__':
    shutil.rmtree(".tmp", ignore_errors=True)
    sys.exit(main())
