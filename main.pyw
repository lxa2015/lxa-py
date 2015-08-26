#!/usr/bin/env python3

#------------------------------------------------------------------------------#
# Linguistica 5 GUI, in Python 3.4+ and PyQt5
#
# Jackson Lee, 2015
#------------------------------------------------------------------------------#
#
#   major windows:
#
#                               MainWindow
#       =====================================================================
#       |                          mainSplitter                             |
#       | ================================================================= |
#       | | minorSplitter  |                MajorDisplay                  | |
#       | | ============== | ============================================ | |
#       | | |            | | |                                          | | |
#       | | |            | | |                                          | | |
#       | | |            | | |                                          | | |
#       | | |TreeWidget  | | |                                          | | |
#       | | |(lexicon)   | | |                                          | | |
#       | | |            | | |                                          | | |
#       | | |============| | |                                          | | |
#       | | |parameter   | | |                                          | | |
#       | | |window      | | |                                          | | |
#       | | ============== | ============================================ | |
#       | ================================================================= |
#       =====================================================================
#
#   How things work in general:
#
#   When a corpus text file is specified, the program checks if the expected
#   output files are there. (If not, the various components
#   {ngram, lxa5, manifold, ...}.py will be run to generate the output files.)
#
#   Then the lexicon is initialized and shown in the TreeWidget.
#   The lexicon shows names of things that the user can click.
#   The major display and parameter window change according to what has been
#   clicked.
#------------------------------------------------------------------------------#

# It is important to get PyQt5 for the python 3 distribution of your system.
# if you're on ubuntu, do the following to get PyQt5:
# sudo apt-get install python3-sip python3-pyqt5 python3-pyqt5.qtwebkit
# -- Jackson Lee, 2015-08-19

import sys

try:
    import PyQt5
except ImportError:
    sys.exit("PyQt5 cannot be imported.\n"
             "Be sure it is properly installed for your Python 3 distribution.")

from PyQt5.QtWidgets import QApplication

from linguistica.gui.main_window import MainWindow
from linguistica.lxa5lib import (__version__, __author__)

#------------------------------------------------------------------------------#

def main():
    app = QApplication(sys.argv)
    app.setStyle('cleanlooks')
    app.setApplicationName("Linguistica")

    # Get screen resolution
    # Why do we need to know screen resolution?
    # Because this information is useful for setting the size of particular
    # widgets, e.g., the webview for visualizing the word neighbor manifold
    # (the bigger the webview size, the better it is for visualization!)
    resolution = app.desktop().screenGeometry()
    screen_width = resolution.width()
    screen_height = resolution.height()

    # launch graphical user interface
    form = MainWindow(screen_height, screen_width, __version__, __author__)
    form.show()
    app.exec_()

#------------------------------------------------------------------------------#

if __name__ == "__main__":
    main()

