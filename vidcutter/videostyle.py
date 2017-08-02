#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# VidCutter - media cutter & joiner
#
# copyright © 2017 Pete Alexandrou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import functools
import os
import sys

from PyQt5.QtCore import QFile, QFileInfo, Qt, QTextStream
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import qApp, QStyle

try:
    from PyQt5.QtWidgets import QProxyStyle

    class VideoStyle(QProxyStyle):
        # noinspection PyMethodOverriding
        def styleHint(self, hint, option, widget, returnData) -> int:
            if hint == QStyle.SH_UnderlineShortcut:
                return 0
            return super(VideoStyle, self).styleHint(hint, option, widget, returnData)

        @staticmethod
        def loadQSS(theme, devmode: bool = False) -> str:
            if devmode:
                filename = os.path.join(QFileInfo(__file__).absolutePath(), 'vidcutter/styles/%s.qss' % theme)
            else:
                filename = ':/styles/%s.qss' % theme
            if QFileInfo(filename).exists():
                qssfile = QFile(filename)
                qssfile.open(QFile.ReadOnly | QFile.Text)
                content = QTextStream(qssfile).readAll()
                if sys.platform == 'darwin' and theme == 'dark':
                    content += 'QComboBox, QHeaderView::section, QMenu::item, QMenu::item:selected { color: #444; }'
                qApp.setStyleSheet(content)
                return content

except ImportError:
    from PyQt5.QtWidgets import QCommonStyle, QStyleFactory

    class VideoStyle(QCommonStyle):
        # workaround for earlier version of PyQt5 when QProxyStyle did not exist
        def __init__(self):
            self._style = QStyleFactory.create(qApp.style().objectName())
            for method in ['drawComplexControl', 'drawControl', 'drawPrimitive', 'drawItemPixmap', 'generatedIconPixmap',
                           'hitTestComplexControl', 'layoutSpacing', 'pixelMetric', 'polish', 'sizeFromContents',
                           'standardPixmap', 'subControlRect', 'subElementRect', 'unpolish', 'itemPixmapRect',
                           'itemTextRect', 'styleHint', 'drawItemText']:
                target = getattr(self._style, method)
                setattr(self, method, functools.partial(target))
            super().__init__()

        # noinspection PyMethodOverriding
        def styleHint(self, hint, option, widget, returnData) -> int:
            if hint == QStyle.SH_UnderlineShortcut:
                return 0
            return super(VideoStyle, self).styleHint(hint, option, widget, returnData)

        @staticmethod
        def loadQSS(theme, devmode: bool = False) -> str:
            if devmode:
                filename = os.path.join(QFileInfo(__file__).absolutePath(), 'vidcutter/styles/%s.qss' % theme)
            else:
                filename = ':/styles/%s.qss' % theme
            if QFileInfo(filename).exists():
                qssfile = QFile(filename)
                qssfile.open(QFile.ReadOnly | QFile.Text)
                content = QTextStream(qssfile).readAll()
                if sys.platform == 'darwin' and theme == 'dark':
                    content += 'QComboBox, QHeaderView::section, QMenu::item, QMenu::item:selected { color: #444; }'
                qApp.setStyleSheet(content)
                return content


class VideoStyleLight(VideoStyle):
    def __init__(self):
        super(VideoStyleLight, self).__init__()
        palette = qApp.palette()
        palette.setColor(QPalette.Window, QColor(239, 240, 241))
        palette.setColor(QPalette.WindowText, QColor(49, 54, 59))
        palette.setColor(QPalette.Base, QColor(252, 252, 252))
        palette.setColor(QPalette.AlternateBase, QColor(239, 240, 241))
        palette.setColor(QPalette.ToolTipBase, QColor(239, 240, 241))
        palette.setColor(QPalette.ToolTipText, QColor(49, 54, 59))
        palette.setColor(QPalette.Text, QColor(49, 54, 59))
        palette.setColor(QPalette.Button, QColor(239, 240, 241))
        palette.setColor(QPalette.ButtonText, QColor(49, 54, 59))
        palette.setColor(QPalette.BrightText, QColor(255, 255, 255))
        palette.setColor(QPalette.Link, QColor(41, 128, 185))
        palette.setColor(QPalette.Highlight, QColor(136, 136, 136))
        palette.setColor(QPalette.HighlightedText, QColor(239, 240, 241))
        palette.setColor(QPalette.Disabled, QPalette.Light, Qt.white)
        palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(234, 234, 234))
        qApp.setPalette(palette)


class VideoStyleDark(VideoStyle):
    def __init__(self):
        super(VideoStyleDark, self).__init__()
        palette = qApp.palette()
        palette.setColor(QPalette.Window, QColor(27, 35, 38))
        palette.setColor(QPalette.WindowText, QColor(234, 234, 234))
        palette.setColor(QPalette.Base, QColor(27, 35, 38))
        palette.setColor(QPalette.AlternateBase, QColor(12, 15, 16))
        palette.setColor(QPalette.ToolTipBase, QColor(27, 35, 38))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, QColor(234, 234, 234))
        palette.setColor(QPalette.Button, QColor(27, 35, 38))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, QColor(100, 215, 222))
        palette.setColor(QPalette.Link, QColor(126, 71, 130))
        palette.setColor(QPalette.Highlight, QColor(126, 71, 130))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        palette.setColor(QPalette.Disabled, QPalette.Light, Qt.black)
        palette.setColor(QPalette.Disabled, QPalette.Shadow, QColor(12, 15, 16))
        qApp.setPalette(palette)
