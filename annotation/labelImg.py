#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Original project https://github.com/tzutalin/labelImg

import codecs
import cv2
import numpy as np
import os.path
import platform
import sys
import subprocess
from collections import OrderedDict
import logging

from csv import reader as csv_reader
from time import time
from functools import partial
# Andreu
from pathlib import Path
from ctypes import *

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

# Add internal libs
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
from libs.pascal_voc_io import PascalVocReader
from libs.pascal_voc_io import XML_EXT
from libs.yolo_io import YoloReader
from libs.yolo_io import TXT_EXT
from libs.ustr import ustr
from libs.version import __version__

from server_request import Requests, ENDPOINTS

__appname__ = 'labelImg'

# Utility functions and classes.

def have_qstring():
    '''p3/qt5 get rid of QString wrapper as py3 has native unicode str type'''
    return not (sys.version_info.major >= 3 or QT_VERSION_STR.startswith('5.'))

def util_qt_strlistclass():
    return QStringList if have_qstring() else list


class Login(QDialog):

    def endpointchange(self):
        if self.comboEndpointDefault.currentText() == 'Custom':
            self.comboEndpointCustom.setEnabled(True)
            # show it
            self.labelEndpointCustom.show()
            self.comboEndpointCustom.show()
        else:
            self.comboEndpointCustom.setEnabled(False)
            # hide it
            self.labelEndpointCustom.hide()
            self.comboEndpointCustom.hide()

    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        
        self.labelName = QLabel("Username:")
        self.textName = QLineEdit(self)
        
        self.labelPass = QLabel("Password:")
        self.textPass = QLineEdit(self)
        self.textPass.setEchoMode(QLineEdit.Password)

        # Dropdown menu with default ENDPOINTS as options
        self.labelEndpointDefault = QLabel("Default Endpoints:")
        self.comboEndpointDefault = QComboBox(self)
        self.comboEndpointDefault.addItems(ENDPOINTS + ['Custom'])
        self.comboEndpointDefault.currentIndexChanged.connect(self.endpointchange)

        self.labelEndpointCustom = QLabel("Custom Endpoint:")
        self.comboEndpointCustom = QLineEdit(self)
        self.comboEndpointCustom.setPlaceholderText("http://localhost:5000")
        # disable and hide it
        self.comboEndpointCustom.setEnabled(False)
        self.labelEndpointCustom.hide()
        self.comboEndpointCustom.hide()

        self.buttonLogin = QPushButton('Go', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        

        self.hor_name = QHBoxLayout()
        self.hor_name.addWidget(self.labelName)
        self.hor_name.addWidget(self.textName)

        self.hor_pass = QHBoxLayout()
        self.hor_pass.addWidget(self.labelPass)
        self.hor_pass.addWidget(self.textPass)

        self.hor_endpoint_default = QHBoxLayout()
        self.hor_endpoint_default.addWidget(self.labelEndpointDefault)
        self.hor_endpoint_default.addWidget(self.comboEndpointDefault)

        self.hor_endpoint_custom = QHBoxLayout()
        self.hor_endpoint_custom.addWidget(self.labelEndpointCustom)
        self.hor_endpoint_custom.addWidget(self.comboEndpointCustom)

        layout = QVBoxLayout(self)
        layout.addLayout(self.hor_name)
        layout.addLayout(self.hor_pass)
        layout.addLayout(self.hor_endpoint_default)
        layout.addLayout(self.hor_endpoint_custom)
        layout.addWidget(self.buttonLogin)

    def getUser(self):
        return self.textName.text()
    def getPassword(self):
        return self.textPass.text()
    def getEndpoint(self):
        endpoint = self.comboEndpointDefault.currentText()
        if endpoint == 'Custom':
            endpoint = self.comboEndpointCustom.text()
            if endpoint == '':
                endpoint = self.comboEndpointCustom.placeholderText()
        return endpoint

    def checkLogin(self):
        textName = self.textName.text()
        textPass = self.textPass.text()
        endpoint = self.getEndpoint()

        logging.info(f"Login.checkLogin: u: {textName}, e: {endpoint}")
        response, description = Requests.Login.do(textName, textPass, endpoint)
        logging.debug(response, description)
        if not response:
            QMessageBox.warning(
                self, 'Error', description)

        return response
        #return True

    def handleLogin(self):
        if self.checkLogin():
            self.accept()

    def closeEvent(self, evnt):
        evnt.ignore()
        sys.exit()

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

    import sys
    app = QApplication(sys.argv)
    Requests.APP = app
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    
    login = Login()
    if login.exec_() == QDialog.Accepted:
        logging.debug(f"loging in as u: {login.getUser()}, e: {login.getEndpoint()}")
        from labelImg_new import *
        app, _win = get_main_app(app, sys.argv, endpoint=login.getEndpoint())
        sys.exit(app.exec_())