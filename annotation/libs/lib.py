from math import sqrt
from libs.ustr import ustr
import hashlib
import sys
from collections import OrderedDict
try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
import os
curr_path = os.path.dirname(os.path.abspath(__file__))


def internal_path(ruta_relativa):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, ruta_relativa)
    return os.path.join(os.path.dirname(os.path.dirname(curr_path)), ruta_relativa)
 

def newIcon(icon):
    return QIcon(internal_path(os.path.join('icons', icon)))


def newButton(text, icon=None, slot=None):
    b = QPushButton(text)
    if icon is not None:
        b.setIcon(newIcon(icon))
    if slot is not None:
        b.clicked.connect(slot)
    return b


def newAction(parent, text, slot=None, shortcut=None, icon=None,
              tip=None, checkable=False, enabled=True):
    """Create a new action and assign callbacks, shortcuts, etc."""
    a = QAction(text, parent)
    if icon is not None:
        a.setIcon(newIcon(icon))
    if shortcut is not None:
        if isinstance(shortcut, (list, tuple)):
            a.setShortcuts(shortcut)
        else:
            a.setShortcut(shortcut)
    if tip is not None:
        a.setToolTip(tip)
        a.setStatusTip(tip)
    if slot is not None:
        a.triggered.connect(slot)
    if checkable:
        a.setCheckable(True)
    a.setEnabled(enabled)
    return a


def addActions(widget, actions):
    def addNode(widget, action_or_menu):
        if action_or_menu is None:
            widget.addSeparator()
        elif isinstance(action_or_menu, QMenu):
            widget.addMenu(action_or_menu)
        else:
            widget.addAction(action_or_menu)

    for action in actions:
        if isinstance(action, (list, tuple)):
            for v in action:
                addNode(widget, v)
        elif isinstance(action, (dict, OrderedDict)):
            for v in action.values():
                addNode(widget, v)
        else:
            addNode(widget, action)

def callbackAction(action, callback):
    if isinstance(action, (list, tuple)):
        for v in action:
            callback(v)
    elif isinstance(action, (dict, OrderedDict)):
        for v in action.values():
            callback(v)
    else:
        callback(action)

def labelValidator():
    return QRegExpValidator(QRegExp(r'^[^ \t].+'), None)


class struct(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def distance(p):
    return sqrt(p.x() * p.x() + p.y() * p.y())


def fmtShortcut(text):
    mod, key = text.split('+', 1)
    return '<b>%s</b>+<b>%s</b>' % (mod, key)

def getRandomColor(text):
    s = str(ustr(text))
    hashCode = int(hashlib.sha256(s.encode('utf-8')).hexdigest(), 16)
    r = int((hashCode / 255) % 255)
    g = int((hashCode / 65025)  % 255)
    b = int((hashCode / 16581375)  % 255)
    return QColor(r, g, b, 100)

def parseColorFromHex(hex_code):
    hex_code = hex_code.lstrip('#')
    rgba_color = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4, 6))
    return QColor(*rgba_color)