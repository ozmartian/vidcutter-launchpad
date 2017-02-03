#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import platform
import re
import sys
import time
from datetime import timedelta

from PyQt5.QtCore import (QDir, QFile, QFileInfo, QModelIndex, QPoint,
                          QSize, Qt, QTextStream, QTime, QUrl, pyqtSlot, qRound)
from PyQt5.QtGui import (QCloseEvent, QDesktopServices, QFont, QFontDatabase, QIcon,
                         QKeyEvent, QMouseEvent, QMovie, QPalette, QPixmap, QWheelEvent)
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QMenu, QMessageBox, QProgressDialog,
                             QPushButton, QSizePolicy, QStyleFactory, QSlider, QToolBar, QVBoxLayout, QWidget, qApp)

from vidcutter.videoservice import VideoService
from vidcutter.videoslider import VideoSlider
import vidcutter.resources


class VideoCutter(QWidget):
    def __init__(self, parent):
        super(VideoCutter, self).__init__(parent)
        self.novideoWidget = QWidget(self, objectName='novideoWidget', autoFillBackground=True)
        self.parent = parent
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = VideoWidget(self.parent)
        self.videoService = VideoService(self)

        self.latest_release_url = 'https://github.com/ozmartian/vidcutter/releases/latest'

        self.ffmpeg_installer = {
            'win32': {
                64: 'https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.7z',
                32: 'https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.7z'
            },
            'darwin': {
                64: 'http://evermeet.cx/pub/ffmpeg/snapshots',
                32: 'http://evermeet.cx/pub/ffmpeg/snapshots'
            },
            'linux': {
                64: 'https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-64bit-static.tar.xz',
                32: 'https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-32bit-static.tar.xz'
            }
        }

        QFontDatabase.addApplicationFont(':/fonts/DroidSansMono.ttf')
        QFontDatabase.addApplicationFont(':/fonts/OpenSans.ttf')

        stylesheet = ':/styles/vidcutter_osx.qss' if sys.platform == 'darwin' else ':/styles/vidcutter.qss'
        self.parent.load_stylesheet(stylesheet)

        fontSize = 12 if sys.platform == 'darwin' else 10
        qApp.setFont(QFont('Open Sans', fontSize, 300))

        self.clipTimes = []
        self.inCut = False
        self.movieFilename = ''
        self.movieLoaded = False
        self.timeformat = 'hh:mm:ss.zzz'
        self.runtimeformat = 'hh:mm:ss'
        self.finalFilename = ''
        self.totalRuntime = 0
        self.frameRate = 0
        self.notifyInterval = 0

        self.edl = ''
        self.edlblock_re = re.compile(r"(\d+(?:\.?\d+)?)\s(\d+(?:\.?\d+)?)\s([01])")

        self.initIcons()
        self.initActions()

        self.toolbar = QToolBar(floatable=False, movable=False, iconSize=QSize(36, 36))
        self.toolbar.setObjectName('appcontrols')
        if sys.platform == 'darwin':
            self.toolbar.setStyle(QStyleFactory.create('Fusion'))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.initToolbar()

        self.appMenu, self.cliplistMenu = QMenu(), QMenu()
        self.initMenus()

        self.seekSlider = VideoSlider(parent=self, sliderMoved=self.setPosition)

        self.initNoVideo()

        self.cliplist = QListWidget(sizePolicy=QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding),
                                    contextMenuPolicy=Qt.CustomContextMenu, uniformItemSizes=True,
                                    iconSize=QSize(100, 700), dragDropMode=QAbstractItemView.InternalMove,
                                    alternatingRowColors=True, customContextMenuRequested=self.itemMenu,
                                    objectName='cliplist', dragEnabled=True)
        self.cliplist.setFixedWidth(190)
        self.cliplist.setAttribute(Qt.WA_MacShowFocusRect, False)
        self.cliplist.model().rowsMoved.connect(self.syncClipList)

        listHeader = QLabel(pixmap=QPixmap(':/images/clipindex.png', 'PNG'),
                            alignment=Qt.AlignCenter)
        listHeader.setObjectName('listHeader')

        self.runtimeLabel = QLabel('<div align="right">00:00:00</div>', textFormat=Qt.RichText)
        self.runtimeLabel.setObjectName('runtimeLabel')

        self.clipindexLayout = QVBoxLayout(spacing=0)
        self.clipindexLayout.setContentsMargins(0, 0, 0, 0)
        self.clipindexLayout.addWidget(listHeader)
        self.clipindexLayout.addWidget(self.cliplist)
        self.clipindexLayout.addWidget(self.runtimeLabel)

        self.videoLayout = QHBoxLayout()
        self.videoLayout.setContentsMargins(0, 0, 0, 0)
        self.videoLayout.addWidget(self.novideoWidget)
        self.videoLayout.addLayout(self.clipindexLayout)

        self.timeCounter = QLabel('00:00:00 / 00:00:00', autoFillBackground=True, alignment=Qt.AlignCenter,
                                  sizePolicy=QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed))
        self.timeCounter.setObjectName('timeCounter')

        videoplayerLayout = QVBoxLayout(spacing=0)
        videoplayerLayout.setContentsMargins(0, 0, 0, 0)
        videoplayerLayout.addWidget(self.videoWidget)
        videoplayerLayout.addWidget(self.timeCounter)

        self.videoplayerWidget = QWidget(self, visible=False)
        self.videoplayerWidget.setLayout(videoplayerLayout)

        self.muteButton = QPushButton(objectName='muteButton', icon=self.unmuteIcon,
                                      flat=True, toolTip='Mute',
                                      statusTip='Toggle audio mute', iconSize=QSize(16, 16),
                                      cursor=Qt.PointingHandCursor, clicked=self.muteAudio)

        self.volumeSlider = QSlider(Qt.Horizontal, toolTip='Volume', statusTip='Adjust volume level',
                                    cursor=Qt.PointingHandCursor, value=50, minimum=0, maximum=100,
                                    sliderMoved=self.setVolume)

        self.menuButton = QPushButton(objectName='menuButton', flat=True, toolTip='Menu',
                                      iconSize=QSize(24, 20), cursor=Qt.PointingHandCursor)
        self.menuButton.setFixedSize(QSize(24, 20))
        self.menuButton.setMenu(self.appMenu)

        toolbarLayout = QHBoxLayout()
        toolbarLayout.addWidget(self.toolbar)
        toolbarLayout.setContentsMargins(0, 0, 0, 0)

        toolbarGroup = QGroupBox()
        toolbarGroup.setFlat(False)
        toolbarGroup.setLayout(toolbarLayout)
        toolbarGroup.setCursor(Qt.PointingHandCursor)
        toolbarGroup.setStyleSheet('QGroupBox { background-color: rgba(0, 0, 0, 0.1); ' +
                                   'border: 1px inset #888; margin: 0; padding: 0;' +
                                   'border-radius: 5px; }')

        controlsLayout = QHBoxLayout(spacing=0)
        controlsLayout.addStretch(1)
        controlsLayout.addWidget(toolbarGroup)
        controlsLayout.addStretch(1)
        controlsLayout.addWidget(self.muteButton)
        controlsLayout.addWidget(self.volumeSlider)
        controlsLayout.addSpacing(20)
        controlsLayout.addWidget(self.menuButton)
        controlsLayout.addSpacing(10)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 4)
        layout.addLayout(self.videoLayout)
        layout.addWidget(self.seekSlider)
        layout.addSpacing(5)
        layout.addLayout(controlsLayout)
        layout.addSpacing(2)

        self.setLayout(layout)

        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.stateChanged.connect(self.mediaStateChanged)
        self.mediaPlayer.positionChanged.connect(self.positionChanged)
        self.mediaPlayer.durationChanged.connect(self.durationChanged)
        self.mediaPlayer.error.connect(self.handleError)

    def initNoVideo(self) -> None:
        novideoImage = QLabel(alignment=Qt.AlignCenter, autoFillBackground=False,
                              pixmap=QPixmap(':/images/novideo.png', 'PNG'),
                              sizePolicy=QSizePolicy(QSizePolicy.Expanding, QSizePolicy.MinimumExpanding))
        novideoImage.setContentsMargins(0, 20, 0, 15)
        self.novideoLabel = QLabel(alignment=Qt.AlignCenter, autoFillBackground=False,
                                   sizePolicy=QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.novideoLabel.setContentsMargins(0, 20, 15, 40)
        novideoLayout = QVBoxLayout(spacing=0)
        novideoLayout.addWidget(novideoImage)
        novideoLayout.addWidget(self.novideoLabel, alignment=Qt.AlignTop)
        self.novideoMovie = QMovie(':/images/novideotext.gif')
        self.novideoMovie.frameChanged.connect(self.setNoVideoText)
        self.novideoMovie.start()
        self.novideoWidget.setBackgroundRole(QPalette.Dark)
        self.novideoWidget.setLayout(novideoLayout)

    def initIcons(self) -> None:
        self.appIcon = QIcon(':/images/vidcutter.png')
        self.openIcon = QIcon(':/images/toolbar-open.png')
        self.playIcon = QIcon(':/images/toolbar-play.png')
        self.pauseIcon = QIcon(':/images/toolbar-pause.png')
        self.cutStartIcon = QIcon(':/images/toolbar-start.png')
        self.cutEndIcon = QIcon(':/images/toolbar-end.png')
        self.saveIcon = QIcon(':/images/toolbar-save.png')
        self.muteIcon = QIcon(':/images/muted.png')
        self.unmuteIcon = QIcon(':/images/unmuted.png')
        self.upIcon = QIcon(':/images/up.png')
        self.downIcon = QIcon(':/images/down.png')
        self.removeIcon = QIcon(':/images/remove.png')
        self.removeAllIcon = QIcon(':/images/remove-all.png')
        self.successIcon = QIcon(':/images/thumbsup.png')
        self.menuIcon = QIcon(':/images/menu.png')
        self.completePlayIcon = QIcon(':/images/complete-play.png')
        self.completeOpenIcon = QIcon(':/images/complete-open.png')
        self.completeRestartIcon = QIcon(':/images/complete-restart.png')
        self.completeExitIcon = QIcon(':/images/complete-exit.png')
        self.openEDLIcon = QIcon(':/images/edl.png')
        self.saveEDLIcon = QIcon(':/images/save.png')
        self.mediaInfoIcon = QIcon(':/images/info.png')
        self.updateCheckIcon = QIcon(':/images/update.png')
        self.thumbsupIcon = QIcon(':/images/thumbsup.png')

    def initActions(self) -> None:
        self.openAction = QAction(self.openIcon, 'Open\nMedia', self, toolTip='Open Media',
                                  statusTip='Open a valid media file', triggered=self.openMedia)
        self.playAction = QAction(self.playIcon, 'Play\nMedia', self, toolTip='Play Media',
                                  statusTip='Play the loaded media file', triggered=self.playMedia, enabled=False)
        self.pauseAction = QAction(self.pauseIcon, 'Pause\nMedia', self, toolTip='Pause Media', visible=False,
                                   statusTip='Pause the currently playing media file', triggered=self.playMedia)
        self.cutStartAction = QAction(self.cutStartIcon, 'Clip\nStart', self, toolTip='Clip Start',
                                      statusTip='Set the start position of a new clip',
                                      triggered=self.setCutStart, enabled=False)
        self.cutEndAction = QAction(self.cutEndIcon, 'Clip\nEnd', self, toolTip='Clip End',
                                    statusTip='Set the end position of a new clip',
                                    triggered=self.setCutEnd, enabled=False)
        self.saveAction = QAction(self.saveIcon, 'Save\nVideo', self, toolTip='Save Video',
                                  statusTip='Save clips to a new video file', triggered=self.cutVideo, enabled=False)
        self.moveItemUpAction = QAction(self.upIcon, 'Move up', self, statusTip='Move clip position up in list',
                                        triggered=self.moveItemUp, enabled=False)
        self.moveItemDownAction = QAction(self.downIcon, 'Move down', self, statusTip='Move clip position down in list',
                                          triggered=self.moveItemDown, enabled=False)
        self.removeItemAction = QAction(self.removeIcon, 'Remove clip', self,
                                        statusTip='Remove selected clip from list', triggered=self.removeItem,
                                        enabled=False)
        self.removeAllAction = QAction(self.removeAllIcon, 'Clear list', self, statusTip='Clear all clips from list',
                                       triggered=self.clearList, enabled=False)
        self.mediaInfoAction = QAction(self.mediaInfoIcon, 'Media information', self,
                                       statusTip='View current media file information', triggered=self.mediaInfo,
                                       enabled=False)
        self.openEDLAction = QAction(self.openEDLIcon, 'Open EDL file', self,
                                     statusTip='Open a previously saved EDL file',
                                     triggered=self.openEDL, enabled=False)
        self.saveEDLAction = QAction(self.saveEDLIcon, 'Save EDL file', self,
                                     statusTip='Save clip list data to an EDL file',
                                     triggered=self.saveEDL, enabled=False)
        self.updateCheckAction = QAction(self.updateCheckIcon, 'Check for updates...', self,
                                         statusTip='Check for application updates', triggered=self.updateCheck)
        self.aboutQtAction = QAction('About Qt', self, statusTip='About Qt', triggered=qApp.aboutQt)
        self.aboutAction = QAction('About %s' % qApp.applicationName(), self, triggered=self.aboutInfo,
                                   statusTip='About %s' % qApp.applicationName())

    def initToolbar(self) -> None:
        self.toolbar.addAction(self.openAction)
        self.toolbar.addAction(self.playAction)
        self.toolbar.addAction(self.pauseAction)
        self.toolbar.addAction(self.cutStartAction)
        self.toolbar.addAction(self.cutEndAction)
        self.toolbar.addAction(self.saveAction)

    def initMenus(self) -> None:
        self.appMenu.addAction(self.openEDLAction)
        self.appMenu.addAction(self.saveEDLAction)
        self.appMenu.addSeparator()
        self.appMenu.addAction(self.mediaInfoAction)
        self.appMenu.addAction(self.updateCheckAction)
        self.appMenu.addSeparator()
        self.appMenu.addAction(self.aboutQtAction)
        self.appMenu.addAction(self.aboutAction)

        self.cliplistMenu.addAction(self.moveItemUpAction)
        self.cliplistMenu.addAction(self.moveItemDownAction)
        self.cliplistMenu.addSeparator()
        self.cliplistMenu.addAction(self.removeItemAction)
        self.cliplistMenu.addAction(self.removeAllAction)

    @staticmethod
    def getSpacer() -> QWidget:
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        return spacer

    def setRunningTime(self, runtime: str) -> None:
        self.runtimeLabel.setText('<div align="right">%s</div>' % runtime)

    @pyqtSlot(int)
    def setNoVideoText(self) -> None:
        self.novideoLabel.setPixmap(self.novideoMovie.currentPixmap())

    def itemMenu(self, pos: QPoint) -> None:
        globalPos = self.cliplist.mapToGlobal(pos)
        self.moveItemUpAction.setEnabled(False)
        self.moveItemDownAction.setEnabled(False)
        self.removeItemAction.setEnabled(False)
        self.removeAllAction.setEnabled(False)
        index = self.cliplist.currentRow()
        if index != -1:
            if not self.inCut:
                if index > 0:
                    self.moveItemUpAction.setEnabled(True)
                if index < self.cliplist.count() - 1:
                    self.moveItemDownAction.setEnabled(True)
            if self.cliplist.count() > 0:
                self.removeItemAction.setEnabled(True)
        if self.cliplist.count() > 0:
            self.removeAllAction.setEnabled(True)
        self.cliplistMenu.exec_(globalPos)

    def moveItemUp(self) -> None:
        index = self.cliplist.currentRow()
        tmpItem = self.clipTimes[index]
        del self.clipTimes[index]
        self.clipTimes.insert(index - 1, tmpItem)
        self.renderTimes()

    def moveItemDown(self) -> None:
        index = self.cliplist.currentRow()
        tmpItem = self.clipTimes[index]
        del self.clipTimes[index]
        self.clipTimes.insert(index + 1, tmpItem)
        self.renderTimes()

    def removeItem(self) -> None:
        index = self.cliplist.currentRow()
        del self.clipTimes[index]
        if self.inCut and index == self.cliplist.count() - 1:
            self.inCut = False
            self.initMediaControls()
        self.renderTimes()

    def clearList(self) -> None:
        self.clipTimes.clear()
        self.cliplist.clear()
        self.inCut = False
        self.renderTimes()
        self.initMediaControls()

    def mediaInfo(self) -> None:
        if self.mediaPlayer.isMetaDataAvailable():
            content = '<table cellpadding="4">'
            for key in self.mediaPlayer.availableMetaData():
                val = self.mediaPlayer.metaData(key)
                if type(val) is QSize:
                    val = '%s x %s' % (val.width(), val.height())
                content += '<tr><td align="right"><b>%s:</b></td><td>%s</td></tr>\n' % (key, val)
            content += '</table>'
            mbox = QMessageBox(windowTitle='Media Information', windowIcon=self.parent.windowIcon(),
                               textFormat=Qt.RichText)
            mbox.setText('<b>%s</b>' % os.path.basename(self.mediaPlayer.currentMedia().canonicalUrl().toLocalFile()))
            mbox.setInformativeText(content)
            mbox.exec_()
        else:
            QMessageBox.critical(self.parent, 'Media file error',
                                 '<h3>Could not probe media file.</h3>' +
                                 '<p>An error occurred while analyzing the media file for its metadata details.' +
                                 '<br/><br/><b>This DOES NOT mean there is a problem with the file and you should ' +
                                 'be able to continue using it.</b></p>')

    def aboutInfo(self) -> None:
        about_html = '''<style>
    a { color:#441d4e; text-decoration:none; font-weight:bold; }
    a:hover { text-decoration:underline; }
</style>
<div style="min-width:650px;">
<p style="font-size:26pt; font-weight:600; color:#6A4572;">%s</p>
<p>
    <span style="font-size:13pt;"><b>Version: %s</b></span>
    <span style="font-size:10pt;position:relative;left:5px;">( %s )</span>
</p>
<p style="font-size:13px;">
    Copyright &copy; 2017 <a href="mailto:pete@ozmartians.com">Pete Alexandrou</a>
    <br/>
    Website: <a href="%s">%s</a>
</p>
<p style="font-size:13px;">
    Thanks to the folks behind the <b>Qt</b>, <b>PyQt</b> and <b>FFmpeg</b>
    projects for all their hard and much appreciated work.
</p>
<p style="font-size:11px;">
    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.
</p>
<p style="font-size:11px;">
    This software uses libraries from the <a href="https://www.ffmpeg.org">FFmpeg</a> project under the
    <a href="https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html">LGPLv2.1</a>
</p></div>''' % (qApp.applicationName(), qApp.applicationVersion(), platform.architecture()[0],
                 qApp.organizationDomain(), qApp.organizationDomain())
        QMessageBox.about(self.parent, 'About %s' % qApp.applicationName(), about_html)

    def openMedia(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self.parent, caption='Select media file',
                                                  directory=QDir.currentPath())
        if filename != '':
            self.loadMedia(filename)

    def openEDL(self, checked: bool = False, edlfile: str = '') -> None:
        source_file, _ = os.path.splitext(self.mediaPlayer.currentMedia().canonicalUrl().toLocalFile())
        self.edl = edlfile
        if not len(self.edl.strip()):
            self.edl, _ = QFileDialog.getOpenFileName(self.parent, caption='Select EDL file',
                                                      filter='MPlayer EDL (*.edl);;' +
                                                             # 'VideoReDo EDL (*.Vprj);;' +
                                                             # 'Comskip EDL (*.txt);;' +
                                                             # 'CMX 3600 EDL (*.edl);;' +
                                                             'All files (*.*)',
                                                      initialFilter='MPlayer EDL (*.edl)',
                                                      directory='%s.edl' % source_file)
        if self.edl.strip():
            file = QFile(self.edl)
            if not file.open(QFile.ReadOnly | QFile.Text):
                QMessageBox.critical(self.parent, 'Open EDL file',
                                     'Cannot read EDL file %s:\n\n%s' % (self.edl, file.errorString()))
                return
            qApp.setOverrideCursor(Qt.WaitCursor)
            self.clipTimes.clear()
            linenum = 1
            while not file.atEnd():
                line = file.readLine().trimmed()
                if line.length() != 0:
                    try:
                        line = str(line, encoding='utf-8')
                    except TypeError:
                        line = str(line)
                    except UnicodeDecodeError:
                        qApp.restoreOverrideCursor()
                        QMessageBox.critical(self.parent, 'Invalid EDL file',
                                             'Could not make any sense of the EDL file supplied. Try viewing it in a ' +
                                             'text editor to ensure it is valid and not corrupted.\n\nAborting EDL ' +
                                             'processing now...')
                        return
                    mo = self.edlblock_re.match(line)
                    if mo:
                        start, stop, action = mo.groups()
                        clip_start = self.deltaToQTime(int(float(start) * 1000))
                        clip_end = self.deltaToQTime(int(float(stop) * 1000))
                        clip_image = self.captureImage(frametime=int(float(start) * 1000))
                        self.clipTimes.append([clip_start, clip_end, clip_image])
                    else:
                        qApp.restoreOverrideCursor()
                        QMessageBox.critical(self.parent, 'Invalid EDL file',
                                             'Invalid entry at line %s:\n\n%s' % (linenum, line))
                linenum += 1
            self.cutStartAction.setEnabled(True)
            self.cutEndAction.setDisabled(True)
            self.seekSlider.setRestrictValue(0, False)
            self.inCut = False
            self.renderTimes()
            qApp.restoreOverrideCursor()
            self.parent.statusBar().showMessage('EDL file was successfully read...', 2000)

    def _td2str(self, td: timedelta) -> str:
        if td is None or td == timedelta.max:
            return ''
        else:
            return '%f' % (td.days * 86400 + td.seconds + td.microseconds / 1000000.)

    def saveEDL(self, filepath: str) -> None:
        source_file, _ = os.path.splitext(self.mediaPlayer.currentMedia().canonicalUrl().toLocalFile())
        edlsave = self.edl if self.edl.strip() else '%s.edl' % source_file
        edlsave, _ = QFileDialog.getSaveFileName(parent=self.parent, caption='Save EDL file',
                                                 directory=edlsave)
        if edlsave.strip():
            file = QFile(edlsave)
            if not file.open(QFile.WriteOnly | QFile.Text):
                QMessageBox.critical(self.parent, 'Save EDL file',
                                     'Cannot write EDL file %s:\n\n%s' % (edlsave, file.errorString()))
                return
            qApp.setOverrideCursor(Qt.WaitCursor)
            for clip in self.clipTimes:
                start_time = timedelta(hours=clip[0].hour(), minutes=clip[0].minute(), seconds=clip[0].second(),
                                       milliseconds=clip[0].msec())
                stop_time = timedelta(hours=clip[1].hour(), minutes=clip[1].minute(), seconds=clip[1].second(),
                                      milliseconds=clip[1].msec())
                QTextStream(file) << '%s\t%s\t%d\n' % (self._td2str(start_time), self._td2str(stop_time), 0)
            qApp.restoreOverrideCursor()
            self.parent.statusBar().showMessage('EDL file was successfully saved...', 2000)

    def loadMedia(self, filename: str) -> None:
        self.movieFilename = filename
        if not os.path.exists(filename):
            return
        self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(filename)))
        self.frameRate = self.videoService.framerate(filename)
        self.notifyInterval = qRound(1000 / self.frameRate)
        self.mediaPlayer.setNotifyInterval(self.notifyInterval)
        self.initMediaControls(True)
        self.cliplist.clear()
        self.clipTimes.clear()
        self.parent.setWindowTitle('%s - %s' % (qApp.applicationName(), os.path.basename(filename)))
        if not self.movieLoaded:
            self.videoLayout.replaceWidget(self.novideoWidget, self.videoplayerWidget)
            self.novideoMovie.stop()
            self.novideoMovie.deleteLater()
            self.novideoWidget.deleteLater()
            self.videoplayerWidget.show()
            self.videoWidget.show()
            self.movieLoaded = True
        if self.mediaPlayer.isVideoAvailable():
            self.mediaPlayer.setPosition(1)
        self.mediaPlayer.play()
        self.mediaPlayer.pause()

    def playMedia(self) -> None:
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()

        else:
            self.mediaPlayer.play()
            self.playAction.setVisible(False)
            self.pauseAction.setVisible(True)

    def initMediaControls(self, flag: bool = True) -> None:
        self.playAction.setEnabled(flag)
        self.saveAction.setEnabled(False)
        self.cutStartAction.setEnabled(flag)
        self.cutEndAction.setEnabled(False)
        self.mediaInfoAction.setEnabled(flag)
        if flag:
            self.seekSlider.setRestrictValue(0)
        self.openEDLAction.setEnabled(flag)
        self.saveEDLAction.setEnabled(False)

    def setPosition(self, position: int) -> None:
        self.mediaPlayer.setPosition(position)

    def positionChanged(self, progress: int) -> None:
        self.seekSlider.setValue(progress)
        currentTime = self.deltaToQTime(progress)
        totalTime = self.deltaToQTime(self.mediaPlayer.duration())
        self.timeCounter.setText(
            '%s / %s' % (currentTime.toString(self.timeformat), totalTime.toString(self.timeformat)))

    @pyqtSlot(QMediaPlayer.State)
    def mediaStateChanged(self, state: QMediaPlayer.State) -> None:
        if state == QMediaPlayer.PlayingState:
            self.playAction.setVisible(False)
            self.pauseAction.setVisible(True)
        else:
            self.playAction.setVisible(True)
            self.pauseAction.setVisible(False)

    def durationChanged(self, duration: int) -> None:
        self.seekSlider.setRange(0, duration)

    def muteAudio(self) -> None:
        if self.mediaPlayer.isMuted():
            self.muteButton.setIcon(self.unmuteIcon)
            self.muteButton.setToolTip('Mute')
        else:
            self.muteButton.setIcon(self.muteIcon)
            self.muteButton.setToolTip('Unmute')
        self.mediaPlayer.setMuted(not self.mediaPlayer.isMuted())

    def setVolume(self, volume: int) -> None:
        self.mediaPlayer.setVolume(volume)

    def toggleFullscreen(self) -> None:
        self.videoWidget.setFullScreen(not self.videoWidget.isFullScreen())

    def setCutStart(self) -> None:
        self.clipTimes.append([self.deltaToQTime(self.mediaPlayer.position()), '', self.captureImage()])
        self.cutStartAction.setDisabled(True)
        self.cutEndAction.setEnabled(True)
        self.seekSlider.setRestrictValue(self.seekSlider.value(), True)
        self.inCut = True
        self.renderTimes()

    def setCutEnd(self) -> None:
        item = self.clipTimes[len(self.clipTimes) - 1]
        selected = self.deltaToQTime(self.mediaPlayer.position())
        if selected.__lt__(item[0]):
            QMessageBox.critical(self.parent, 'Invalid END Time',
                                 'The clip end time must come AFTER it\'s start time. Please try again.')
            return
        item[1] = selected
        self.cutStartAction.setEnabled(True)
        self.cutEndAction.setDisabled(True)
        self.seekSlider.setRestrictValue(0, False)
        self.inCut = False
        self.renderTimes()

    @pyqtSlot(QModelIndex, int, int, QModelIndex, int)
    def syncClipList(self, parent: QModelIndex, start: int, end: int, destination: QModelIndex, row: int) -> None:
        if start < row:
            index = row - 1
        else:
            index = row
        clip = self.clipTimes.pop(start)
        self.clipTimes.insert(index, clip)

    def renderTimes(self) -> None:
        self.cliplist.clear()
        if len(self.clipTimes) > 4:
            self.cliplist.setFixedWidth(205)
        else:
            self.cliplist.setFixedWidth(190)
        self.totalRuntime = 0
        for clip in self.clipTimes:
            endItem = ''
            if type(clip[1]) is QTime:
                endItem = clip[1].toString(self.timeformat)
                self.totalRuntime += clip[0].msecsTo(clip[1])
            listitem = QListWidgetItem()
            listitem.setTextAlignment(Qt.AlignVCenter)
            if type(clip[2]) is QPixmap:
                listitem.setIcon(QIcon(clip[2]))
            self.cliplist.addItem(listitem)
            marker = QLabel('''<style>b { font-size:8pt; } p { margin:2px 3px; }</style>
                            <p><b>START</b><br/>%s<br/><b>END</b><br/>%s</p>'''
                            % (clip[0].toString(self.timeformat), endItem))
            marker.setStyleSheet('border:none;')
            self.cliplist.setItemWidget(listitem, marker)
            listitem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)
        if len(self.clipTimes) and not self.inCut:
            self.saveAction.setEnabled(True)
            self.saveEDLAction.setEnabled(True)
        if self.inCut or len(self.clipTimes) == 0 or not type(self.clipTimes[0][1]) is QTime:
            self.saveAction.setEnabled(False)
            self.saveEDLAction.setEnabled(False)
        self.setRunningTime(self.deltaToQTime(self.totalRuntime).toString(self.runtimeformat))

    @staticmethod
    def deltaToQTime(millisecs: int) -> QTime:
        secs = millisecs / 1000
        return QTime((secs / 3600) % 60, (secs / 60) % 60, secs % 60, (secs * 1000) % 1000)

    def captureImage(self, frametime=None) -> QPixmap:
        if frametime is None:
            frametime = self.deltaToQTime(self.mediaPlayer.position())
        else:
            frametime = self.deltaToQTime(frametime)
        inputfile = self.mediaPlayer.currentMedia().canonicalUrl().toLocalFile()
        imagecap = self.videoService.capture(inputfile, frametime.toString(self.timeformat))
        if type(imagecap) is QPixmap:
            return imagecap

    def cutVideo(self) -> bool:
        clips = len(self.clipTimes)
        filename, filelist = '', []
        source_file, source_ext = os.path.splitext(self.mediaPlayer.currentMedia().canonicalUrl().toLocalFile())
        if clips > 0:
            self.finalFilename, _ = QFileDialog.getSaveFileName(parent=self.parent, caption='Save video',
                                                                directory='%s_EDIT%s' % (source_file, source_ext),
                                                                filter='Video files (*%s)' % source_ext)
            if self.finalFilename == '':
                return False
            file, ext = os.path.splitext(self.finalFilename)
            if len(ext) == 0:
                ext = source_ext
                self.finalFilename += ext
            qApp.setOverrideCursor(Qt.WaitCursor)
            self.saveAction.setDisabled(True)
            self.showProgress(clips)
            index = 1
            self.progress.setLabelText('Cutting media files...')
            qApp.processEvents()
            for clip in self.clipTimes:
                duration = self.deltaToQTime(clip[0].msecsTo(clip[1])).toString(self.timeformat)
                filename = '%s_%s%s' % (file, '{0:0>2}'.format(index), ext)
                filelist.append(filename)
                self.videoService.cut('%s%s' % (source_file, source_ext), filename, clip[0].toString(self.timeformat),
                                      duration)
                index += 1
            if len(filelist) > 1:
                self.joinVideos(filelist, self.finalFilename)
            else:
                QFile.remove(self.finalFilename)
                QFile.rename(filename, self.finalFilename)
            self.progress.setLabelText('Complete...')
            self.progress.setValue(100)
            qApp.processEvents()
            self.progress.close()
            self.progress.deleteLater()
            qApp.restoreOverrideCursor()
            self.complete()
            return True
        return False

    def joinVideos(self, joinlist: list, filename: str) -> None:
        listfile = os.path.normpath(os.path.join(os.path.dirname(joinlist[0]), '.vidcutter.list'))
        fobj = open(listfile, 'w')
        for file in joinlist:
            fobj.write('file \'%s\'\n' % file.replace("'", "\\'"))
        fobj.close()
        self.videoService.join(listfile, filename)
        QFile.remove(listfile)
        for file in joinlist:
            if os.path.isfile(file):
                QFile.remove(file)

    def updateCheck(self) -> None:
        QDesktopServices.openUrl(QUrl(self.latest_release_url))

    def showProgress(self, steps: int, label: str = 'Analyzing media...') -> None:
        self.progress = QProgressDialog(label, None, 0, steps, self.parent, windowModality=Qt.ApplicationModal,
                                        windowIcon=self.parent.windowIcon(), minimumDuration=0, minimumWidth=500)
        self.progress.show()
        for i in range(steps):
            self.progress.setValue(i)
            qApp.processEvents()
            time.sleep(1)

    def complete(self) -> None:
        info = QFileInfo(self.finalFilename)
        mbox = QMessageBox(icon=self.thumbsupIcon, windowTitle='Your video is ready', minimumWidth=500,
                           textFormat=Qt.RichText)
        mbox.setIconPixmap(self.thumbsupIcon.pixmap(64, 64))
        mbox.setText('''
    <style>
        table.info { margin:6px; padding:4px 15px; }
        td.label { font-weight:bold; font-size:10pt; text-align:right; }
        td.value { font-size:10pt; }
    </style>
    <table class="info" cellpadding="4" cellspacing="0">
        <tr>
            <td class="label"><b>File:</b></td>
            <td class="value" nowrap>%s</td>
        </tr>
        <tr>
            <td class="label"><b>Size:</b></td>
            <td class="value">%s</td>
        </tr>
        <tr>
            <td class="label"><b>Length:</b></td>
            <td class="value">%s</td>
        </tr>
    </table><br/>''' % (
            QDir.toNativeSeparators(self.finalFilename), self.sizeof_fmt(int(info.size())),
            self.deltaToQTime(self.totalRuntime).toString(self.timeformat)))
        play = mbox.addButton('Play', QMessageBox.AcceptRole)
        play.setIcon(self.completePlayIcon)
        play.clicked.connect(self.openResult)
        fileman = mbox.addButton('Open', QMessageBox.AcceptRole)
        fileman.setIcon(self.completeOpenIcon)
        fileman.clicked.connect(self.openFolder)
        end = mbox.addButton('Exit', QMessageBox.AcceptRole)
        end.setIcon(self.completeExitIcon)
        end.clicked.connect(self.close)
        new = mbox.addButton('Restart', QMessageBox.AcceptRole)
        new.setIcon(self.completeRestartIcon)
        new.clicked.connect(self.parent.restart)
        mbox.setDefaultButton(new)
        mbox.setEscapeButton(new)
        mbox.adjustSize()
        mbox.exec_()

    def sizeof_fmt(self, num: float, suffix: chr = 'B') -> str:
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Y', suffix)

    @pyqtSlot()
    def openFolder(self) -> None:
        self.openResult(pathonly=True)

    @pyqtSlot(bool)
    def openResult(self, pathonly: bool = False) -> None:
        self.parent.restart()
        if len(self.finalFilename) and os.path.exists(self.finalFilename):
            target = self.finalFilename if not pathonly else os.path.dirname(self.finalFilename)
            QDesktopServices.openUrl(QUrl.fromLocalFile(target))

    @pyqtSlot()
    def startNew(self) -> None:
        qApp.restoreOverrideCursor()
        self.clearList()
        self.seekSlider.setValue(0)
        self.seekSlider.setRange(0, 0)
        self.mediaPlayer.setMedia(QMediaContent())
        self.initNoVideo()
        self.videoLayout.replaceWidget(self.videoplayerWidget, self.novideoWidget)
        self.initMediaControls(False)
        self.parent.setWindowTitle('%s' % qApp.applicationName())

    def ffmpeg_check(self) -> bool:
        valid = os.path.exists(self.videoService.backend) if self.videoService.backend is not None else False
        if not valid:
            if sys.platform == 'win32':
                exe = 'bin\\ffmpeg.exe'
            else:
                valid = os.path.exists(self.parent.get_path('bin/ffmpeg', override=True))
                exe = 'bin/ffmpeg'
            if sys.platform.startswith('linux'):
                link = self.ffmpeg_installer['linux'][self.parent.get_bitness()]
            else:
                link = self.ffmpeg_installer[sys.platform][self.parent.get_bitness()]
            QMessageBox.critical(None, 'Missing FFMpeg executable', '<style>li { margin: 1em 0; }</style>' +
                                 '<h3 style="color:#6A687D;">MISSING FFMPEG EXECUTABLE</h3>' +
                                 '<p>The FFMpeg utility is missing in your ' +
                                 'installation. It should have been installed when you first setup VidCutter.</p>' +
                                 '<p>You can easily fix this by manually downloading and installing it yourself by' +
                                 'following the steps provided below:</p><ol>' +
                                 '<li>Download the <b>static</b> version of FFMpeg from<br/>' +
                                 '<a href="%s" target="_blank"><b>this clickable link</b></a>.</li>' % link +
                                 '<li>Extract this file accordingly and locate the ffmpeg executable within.</li>' +
                                 '<li>Move or Cut &amp; Paste the executable to the following path on your system: ' +
                                 '<br/><br/>&nbsp;&nbsp;&nbsp;&nbsp;%s</li></ol>'
                                 % QDir.toNativeSeparators(self.parent.get_path(exe, override=True)) +
                                 '<p><b>NOTE:</b> You will most likely need Administrator rights (Windows) or ' +
                                 'root access (Linux/Mac) in order to do this.</p>')
        return valid

    @pyqtSlot(QMediaPlayer.Error)
    def handleError(self, error: QMediaPlayer.Error) -> None:
        qApp.restoreOverrideCursor()
        self.startNew()
        if error == QMediaPlayer.ResourceError:
            QMessageBox.critical(self.parent, 'Invalid Media',
                                 'Invalid media file detected at:<br/><br/><b>%s</b><br/><br/>%s'
                                 % (self.movieFilename, self.mediaPlayer.errorString()))
        else:
            QMessageBox.critical(self.parent, 'An error has occurred', self.mediaPlayer.errorString())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.mediaPlayer.isVideoAvailable() or self.mediaPlayer.isAudioAvailable():
            if event.angleDelta().y() > 0:
                newval = self.seekSlider.value() - self.notifyInterval
            else:
                newval = self.seekSlider.value() + self.notifyInterval
            self.seekSlider.setValue(newval)
            self.seekSlider.setSliderPosition(newval)
            self.mediaPlayer.setPosition(newval)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.mediaPlayer.isVideoAvailable() or self.mediaPlayer.isAudioAvailable():
            addtime = 0
            if event.key() == Qt.Key_Space:
                if self.cutStartAction.isEnabled():
                    self.setCutStart()
                elif self.cutEndAction.isEnabled():
                    self.setCutEnd()
            elif event.key() == Qt.Key_Left:
                addtime = -self.notifyInterval
            elif event.key() == Qt.Key_PageUp or event.key() == Qt.Key_Up:
                addtime = -(self.notifyInterval * 10)
            elif event.key() == Qt.Key_Right:
                addtime = self.notifyInterval
            elif event.key() == Qt.Key_PageDown or event.key() == Qt.Key_Down:
                addtime = self.notifyInterval * 10
            if addtime != 0:
                newval = self.seekSlider.value() + addtime
                self.seekSlider.setValue(newval)
                self.seekSlider.setSliderPosition(newval)
                self.mediaPlayer.setPosition(newval)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.BackButton and self.cutStartAction.isEnabled():
            self.setCutStart()
            event.accept()
        elif event.button() == Qt.ForwardButton and self.cutEndAction.isEnabled():
            self.setCutEnd()
            event.accept()
        else:
            super(VideoCutter, self).mousePressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.parent.closeEvent(event)


class VideoWidget(QVideoWidget):
    def __init__(self, parent=None):
        super(VideoWidget, self).__init__(parent)
        self.parent = parent
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        p = self.palette()
        p.setColor(QPalette.Window, Qt.black)
        self.setPalette(p)
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.setFullScreen(not self.isFullScreen())
        event.accept()
