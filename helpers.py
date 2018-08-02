#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# VidCutter - media cutter & joiner
#
# copyright © 2018 Pete Alexandrou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######################################################################

import codecs
import os
import pydoc
import shutil
import subprocess
import sys

from distutils.spawn import find_executable

import vidcutter


class SetupHelpers:
    here = os.path.abspath(os.path.dirname(__file__))

    @staticmethod
    def get_bitness():
        from struct import calcsize
        return calcsize('P') * 8

    @staticmethod
    def get_include_dirs():
        _dirs = []
        if sys.platform == 'win32':
            _dirs = ['vidcutter/libs/pympv/include']
        return _dirs

    @staticmethod
    def get_library_dirs():
        _dirs = []
        if sys.platform == 'win32':
            _dirs = ['vidcutter/libs/pympv/win%s' % SetupHelpers.get_bitness()]
        return _dirs

    @staticmethod
    def get_description(filename='README.md'):
        with codecs.open(os.path.join(SetupHelpers.here, filename), encoding='utf-8') as f:
            file = list(f)
        desc = ''
        for item in file[11: len(file)]:
            desc += item
        return desc

    @staticmethod
    def get_data_files():
        files = []
        if sys.platform.startswith('linux') and 'QT_APPIMAGE' not in os.environ.keys():
            appid = vidcutter.__desktopid__
            files = [
                ('share/icons/hicolor/16x16/apps', ['data/icons/hicolor/16x16/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/22x22/apps', ['data/icons/hicolor/22x22/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/24x24/apps', ['data/icons/hicolor/24x24/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/32x32/apps', ['data/icons/hicolor/32x32/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/48x48/apps', ['data/icons/hicolor/48x48/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/64x64/apps', ['data/icons/hicolor/64x64/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/128x128/apps', ['data/icons/hicolor/128x128/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/256x256/apps', ['data/icons/hicolor/256x256/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/512x512/apps', ['data/icons/hicolor/512x512/apps/{}.png'.format(appid)]),
                ('share/icons/hicolor/scalable/apps', ['data/icons/hicolor/scalable/apps/{}.svg'.format(appid)]),
                ('share/applications', ['data/desktop/{}.desktop'.format(appid)]),
                ('share/metainfo', ['data/appdata/{}.appdata.xml'.format(appid)]),
                ('share/mime/packages', ['data/mime/{}.xml'.format(appid)]),
                ('share/doc/vidcutter', ['CHANGELOG', 'LICENSE', 'README.md'])
            ]
        return files

    @staticmethod
    def get_latest_win32_libmpv(arch: int=64):
        from urllib.request import urlopen
        import ssl
        import xmltodict
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        xml = urlopen('https://sourceforge.net/projects/mpv-player-windows/rss?path=/libmpv', context=ctx).read()
        data = xml.decode('utf-8')
        datadict = xmltodict.parse(data)
        link = datadict['rss']['channel']['item'][1 if arch == 32 else 0]['title']
        print(link)

    @staticmethod
    def get_latest_win32_libmpv_64():
        return SetupHelpers.get_latest_win32_libmpv()

    @staticmethod
    def get_latest_win32_libmpv_32():
        return SetupHelpers.get_latest_win32_libmpv(32)

    @staticmethod
    def pip_notes():
        os.system('cls' if sys.platform == 'win32' else 'clear')
        pydoc.pager('''
    If installing via PyPi (Python Pip) on Linux then you need to know that VidCutter
    depends on the following packages and distros. Install using your distro's
    software packager for a noticeably better integrated experience.
    
        ---[Ubuntu/Debian/Mint/etc]--------------------------
            
            python3-dev libmpv1 libmpv-dev python3-pyqt5
            python3-pyqt5.qtopengl python3-pyqt5.qtx11extras
            ffmpeg mediainfo python3-opengl
    
        ---[Arch Linux]--------------------------------------
    
            python mpv python-pyqt5 ffmpeg mediainfo
    
        ---[Fedora]------------------------------------------
        
            python3-devel mpv-libs mpv-libs-devel python3-qt5
            ffmpeg mediainfo python3-pyopengl
        
        ---[openSUSE]----------------------------------------
            
            python3-devel libmpv1 mpv-devel python3-qt5
            ffmpeg mediainfo 

    You need to build a Python extension module before you can run the
    app directly from source code. This is done for you automatically by
    the package installers but if you wish to simply run the app direct
    from source without having to install it (i.e. python3 setup.py install)
    you can do so by building the extension module with the following
    setuptools command, run from the top-most extracted source code folder:

        $ python3 setup.py build_ext -i
        
    And to then run the app directly from source, from the same top-most
    source code folder:
    
        $ python3 -m vidcutter

    To view all console output for debugging or general interest then
    append the debug parameter:

        $ python3 -m vidcutter --debug
        
    Make sure you build the extension module AFTER installing the
    dependencies covered above, in particular libmpv and the mpv + python3
    dev headers are all needed for it to compile successfully. Compiled
    extension modules under vidcutter/libs will look like:

        mpv.cpython-36m-x86_64-linux-gnu.so [linux]
        mpv.cp36-win_amd64.pyd              [win32]
        
    Windows users must do all this within a Visual Studio 2015/2017 Native x64/x86
    Developer Command Prompt accessible from your Visual Studio program group
    via the start menu. It's easier to just grab the pre-built Windows installers
    directly from:

        https://github.com/ozmartian/vidcutter/releases/latest
''')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        getattr(SetupHelpers, sys.argv[1])()
    else:
        print('\nRebuilding resource file...\n')
        exe = find_executable('pyrcc5')
        if exe is None:
            sys.stderr.write('Could not find pyrcc5 executable')
            sys.exit(1)
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CHANGELOG'),
                    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vidcutter', 'CHANGELOG'))
        subprocess.run('{0} -compress 9 -o "{1}" "{2}"'
                       .format(exe,
                               os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vidcutter', 'resources.py'),
                               os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vidcutter', 'resources.qrc')),
                       shell=True)
        os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vidcutter', 'CHANGELOG'))
