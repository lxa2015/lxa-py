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

import sys
import os
import json
from pathlib import Path

# It is important to get PyQt5 for the python 3 distribution of your system.
# if you're on ubuntu, do the following to get PyQt5:
# sudo apt-get install python3-sip python3-pyqt5 python3-pyqt5.qtwebkit
# -- Jackson Lee, 2015-08-19

try:
    import PyQt5
except ImportError:
    sys.exit("PyQt5 cannot be imported.\n"
             "Be sure it is properly installed for your Python 3 distribution.")

from PyQt5.QtCore import (Qt, QUrl)
from PyQt5.QtWidgets import (QDialog, QMainWindow, QApplication, QWidget,
                             QAction, QHBoxLayout, QVBoxLayout, QTreeWidget,
                             QFileDialog, QLabel, QPushButton, QMessageBox,
                             QLayout, QTabWidget, QDoubleSpinBox, QLineEdit,
                             QTreeWidgetItem, QTableWidget, QTableWidgetItem,
                             QSplitter)
from PyQt5.QtWebKitWidgets import QWebView

# the following modules are from the Linguistica team.

from lexicon import Lexicon
from linguistica.lxa5lib import (SEP_SIG, SEP_SIGTRANSFORM, sorted_alphabetized)

from linguistica import signature
from linguistica import ngram
from linguistica import trie
from linguistica import phon
from linguistica import manifold

# importing constants (all variable names in caps) and functions
from lxa5libgui import *

#------------------------------------------------------------------------------#

__version__ = "5.1.0"
__author__ = 'Jackson L. Lee'

#------------------------------------------------------------------------------#

class MainWindow(QMainWindow):

    def __init__(self, screen_height, screen_width, parent=None):
        super(MainWindow, self).__init__(parent)

        self.screen_width = screen_width
        self.screen_height = screen_height

        # basic main window settings
        self.dirty = False
        self.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        self.setWindowTitle('Linguistica {}'.format(__version__))

        # lexicon and lexicon tree
        self.lexicon = None

        self.lexiconTree = QTreeWidget()
        self.lexiconTree.setEnabled(True)
        self.lexiconTree.setMinimumWidth(TREEWIDGET_WIDTH_MIN)
        self.lexiconTree.setMaximumWidth(TREEWIDGET_WIDTH_MAX)
        self.lexiconTree.setMinimumHeight(TREEWIDGET_HEIGHT_MIN)
        self.lexiconTree.setHeaderLabel("")
        self.lexiconTree.setItemsExpandable(True)
        self.lexiconTree.itemClicked.connect(self.tree_item_clicked)

        # set up major display, parameter window, then load main window
        self.majorDisplay = QWidget()
        self.parameterWindow = QWidget()
        self.load_main_window()

        # "File" menu and actions
        fileSpecifyAction = self.createAction(text="&Read corpus...",
            slot=self.fileNewCorpusDialog, tip="Open a corpus file",
            shortcut="Ctrl+N")
        fileRunAction = self.createAction(text="&Rerun corpus...",
            slot=self.fileRunCorpus, tip="Rerun a corpus file",
            shortcut="Ctrl+D")
        filePreferencesAction = self.createAction(text="&Preferences",
            slot=self.filePreferencesDialog, tip="Preferences")

        fileMenu = self.menuBar().addMenu("&File")
        fileMenu.addActions((fileSpecifyAction, fileRunAction,
            filePreferencesAction))

        # corpus and wordlist
        self.corpus_filename = None
        self.corpus_name = None
        self.wordlist_filename = None
        self.wordlist_name = None

        # configuration file
        self.config_filename = CONFIG_FILENAME

        if Path(self.config_filename).exists():
            self.config = json.load(open(self.config_filename))
        else:
            self.config = CONFIG
            json.dump(self.config, open(self.config_filename, "w"))

        # read the parameters
        # if errors arise, use default values from CONFIG
        try:
            self.max_word_tokens = self.config["max_word_tokens"]
            self.min_stem_length = self.config["min_stem_length"]
            self.max_affix_length = self.config[""]
            self.min_sig_use = self.config["min_sig_use"]
            self.min_affix_length = self.config["min_affix_length"]
            self.min_sf_pf_count = self.config["min_sf_pf_count"]
            self.n_neighbors = self.config["n_neighbors"]
            self.n_eigenvectors = self.config["n_eigenvectors"]
            self.min_context_use = self.config["min_context_use"]
            self.max_word_types = self.config["max_word_types"]
        except KeyError:
            self.max_word_tokens = CONFIG["max_word_tokens"]
            self.min_stem_length = CONFIG["min_stem_length"]
            self.max_affix_length = CONFIG["max_affix_length"]
            self.min_sig_use = CONFIG["min_sig_use"]
            self.min_affix_length = CONFIG["min_affix_length"]
            self.min_sf_pf_count = CONFIG["min_sf_pf_count"]
            self.n_neighbors = CONFIG["n_neighbors"]
            self.n_eigenvectors = CONFIG["n_eigenvectors"]
            self.min_context_use = CONFIG["min_context_use"]
            self.max_word_types = CONFIG["max_word_types"]
        # TODO: allow user to change the parameters in the GUI somehow...

        # corpus filenames already run; last filename run
        try:
            self.last_filename = self.config["last_filename"]
        except KeyError:
            self.last_filename = None

        try:
            self.filenames_run = self.config["filenames_run"]
        except KeyError:
            self.filenames_run = list()


    def createAction(self, text=None, slot=None, tip=None, shortcut=None,
                     checkable=False):
        """this create actions for the File menu, things like
        Read Corpus, Rerun Corpus etc
        """
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if tip:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot:
            action.triggered.connect(slot)
        if checkable:
            action.setCheckable(True)
        return action


    def fileRunCorpus(self):
        self.run_corpus()
        self.create_lexicon()


    def fileNewCorpusDialog(self):
        """Pop up the "open a file" dialog and ask for which corpus text file
        to use
        """
        try:
            open_dir = self.config["last_filename"]
        except (TypeError, KeyError, FileNotFoundError):
            open_dir = "."

        fname = QFileDialog.getOpenFileName(self,
                                        "Open a new corpus data file", open_dir)

        # HACK: fname is supposed to be a string (at least according to the
        # PyQt5 documentation), but for some reason fname is a tuple.
        # So we need this hack to make sure that fname is a string of a filename
        # -- Jackson Lee, 6/22/2015
        if fname and any(fname) and (type(fname) is tuple):
            self.corpus_filename = fname[0]
        else:
            # if this hack isn't needed somehow...
            self.corpus_filename = fname

        assert isinstance(self.corpus_filename, str)
        # note that self.corpus_filename is an absolute full path
        self.corpus_name = Path(self.corpus_filename).name

        # check if this corpus run has been run before
        if self.corpus_filename in self.filenames_run:
            # no need to run the corpus
            print("The corpus text file {} "
                "has been run before.".format(self.corpus_filename), flush=True)
            if self.corpus_filename != self.last_filename:
                self.last_filename = self.corpus_filename
                self.write_new_config()
        else:
            # run the various linguistica programs on the selected corpus file
            self.run_corpus()

        # initialize the lexicon for the selected corpus and its output files
        self.create_lexicon()


    def run_corpus(self):
        if not self.valid_filename():
            return

        print("\nCorpus text file in use:\n{}\n".format(self.corpus_filename),
            flush=True)

        ngram.main(filename=self.corpus_filename,
            maxwordtokens=self.max_word_tokens)

        signature.main(filename=self.corpus_filename,
            maxwordtokens=self.max_word_tokens,
            MinimumStemLength=self.min_stem_length,
            MaximumAffixLength=self.max_affix_length,
            MinimumNumberofSigUses=self.min_sig_use)

        trie.main(filename=self.corpus_filename,
            maxwordtokens=self.max_word_tokens,
            MinimumStemLength=self.min_stem_length,
            MinimumAffixLength=self.min_affix_length,
            SF_threshold=self.min_sf_pf_count)

        phon.main(filename=self.corpus_filename,
            maxwordtokens=self.max_word_tokens)

        manifold.main(filename=self.corpus_filename,
            maxwordtypes=self.max_word_types,
            nNeighbors=self.n_neighbors,
            nEigenvectors=self.n_eigenvectors,
            mincontexts=self.min_context_use)

        # check if corpus has been run before, see if updating config is needed
        new_config = False
        if self.corpus_filename not in self.filenames_run:
            self.filenames_run.append(self.corpus_filename)
            new_config = True
        if self.corpus_filename != self.last_filename:
            self.last_filename = self.corpus_filename
            new_config = True
        if new_config:
            self.write_new_config()
            print("Configuration file updated", flush=True)

        print("\nAll Linguistica components run for the corpus", flush=True)


    def write_new_config(self):
        self.config["filenames_run"] = self.filenames_run
        self.config["last_filename"] = self.last_filename
        json.dump(self.config, open(self.config_filename, "w"))
        print("new configuration {} written".format(self.config_filename),
            flush=True)


    def create_lexicon(self):
        self.lexicon = Lexicon(self.corpus_filename)
        self.populate_lexicon_tree()


    def populate_lexicon_tree(self):
        self.lexiconTree.clear()
        self.lexiconTree.lexicon = self.lexicon

        # corpus name (in the tree header label)
        self.lexiconTree.setHeaderLabel("Corpus: " + self.corpus_name)

        # wordlist
        ancestor = QTreeWidgetItem(self.lexiconTree, [WORDLIST])
        self.lexiconTree.expandItem(ancestor)

        # word ngrams
        ancestor = QTreeWidgetItem(self.lexiconTree, [WORD_NGRAMS])
        self.lexiconTree.expandItem(ancestor)
        for item_str in [BIGRAMS, TRIGRAMS]:
            item = QTreeWidgetItem(ancestor, [item_str])
            self.lexiconTree.expandItem(item)

        # signatures
        ancestor = QTreeWidgetItem(self.lexiconTree, [SIGNATURES])
        self.lexiconTree.expandItem(ancestor)
        for item in [SIGS_TO_STEMS, WORDS_TO_SIGS]:
            self.lexiconTree.expandItem(QTreeWidgetItem(ancestor, [item]))

        # tries
        ancestor = QTreeWidgetItem(self.lexiconTree, [TRIES])
        self.lexiconTree.expandItem(ancestor)
        for item in [WORDS_AS_TRIES, SF_TRIES, PF_TRIES]:
            self.lexiconTree.expandItem(QTreeWidgetItem(ancestor, [item]))

        # phonology
        ancestor = QTreeWidgetItem(self.lexiconTree, [PHONOLOGY])
        self.lexiconTree.expandItem(ancestor)
        for item in [PHONES, BIPHONES, TRIPHONES]:
            self.lexiconTree.expandItem(QTreeWidgetItem(ancestor, [item]))

        # manifolds
        ancestor = QTreeWidgetItem(self.lexiconTree, [MANIFOLDS])
        self.lexiconTree.expandItem(ancestor)
        for item in [WORD_NEIGHBORS, VISUALIZED_GRAPH]:
            self.lexiconTree.expandItem(QTreeWidgetItem(ancestor, [item]))

        print("Lexicon navigation tree populated", flush=True)

    def valid_filename(self):
        """check if there's a valid corpus text filename
        """
        if not self.corpus_filename:
            QMessageBox.warning(self, "Warning", "No corpus file is specified.")
            return False

        if not Path(self.corpus_filename).exists():
            QMessageBox.warning(self, "Warning", "Corpus file does not exist.")
            return False

        return True # = filename is good

    def tree_item_clicked(self, item):
        """trigger the appropriate action when something in the lexicon tree
        is clicked, and update the major display plus parameter window
        """
        item_str = item.text(0)
        print("loading", item_str, flush=True)
        self.lexicon.retrieve_data(item_str)

        new_display = None
        new_parameter_window = None

        if item_str == WORDLIST:
            new_display = self.create_major_display_table(
                self.lexicon.word_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Word", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=0)

        elif item_str == BIGRAMS:
            new_display = self.create_major_display_table(
                self.lexicon.bigram_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Bigram", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=2000)

        elif item_str == TRIGRAMS:
            new_display = self.create_major_display_table(
                self.lexicon.trigram_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Trigram", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=2000)

        elif item_str == SIGS_TO_STEMS:
            new_display = self.create_major_display_table(
                self.lexicon.sig_to_stems.items(),
                key=lambda x:len(x[1]), reverse=True,
                headers=["Signature", "Stem count", "A few stems"],
                row_cell_functions=[lambda x : SEP_SIG.join(x[0]),
                    lambda x : len(x[1]),
                    lambda x : ", ".join(sorted(x[1])[:2]) + ", ..."],
                cutoff=0)

        elif item_str == WORDS_TO_SIGS:
            new_display = self.create_major_display_table(
                self.lexicon.word_to_sigs.items(),
                key=lambda x:len(x[1]), reverse=True,
                headers=["Word", "Signature count", "Signatures"],
                row_cell_functions=[lambda x: x[0],
                    lambda x : len(x[1]),
                    lambda x : ", ".join([SEP_SIG.join(sig)
                                          for sig in sorted(x[1])])],
                cutoff=2000)

        elif item_str == WORDS_AS_TRIES:
            words = self.lexicon.tries_LtoR.keys()
            word_to_tries = dict()
            # key: word (str)
            # value: tuple of (str, str), for left-to-right and right-to-left tries

            for word in words:
                LtoR_trie = " ".join(self.lexicon.tries_LtoR[word])
                RtoL_trie = " ".join([x[::-1]
                            for x in self.lexicon.tries_RtoL[word[::-1]][::-1]])
                word_to_tries[word] = (LtoR_trie, RtoL_trie)

            new_display = self.create_major_display_table(
                word_to_tries.items(),
                key=lambda x: x[0], reverse=False,
                headers=["Word", "Reversed word",
                         "Left-to-right trie", "Right-to-left trie"],
                row_cell_functions=[lambda x: x[0], lambda x: x[0][::-1],
                                    lambda x: x[1][0], lambda x: x[1][1]],
                cutoff=0, set_text_alignment=[(3, Qt.AlignRight)])

        elif item_str == PHONES:
            new_display = self.create_major_display_table(
                self.lexicon.phone_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Phone", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=0)

        elif item_str == BIPHONES:
            new_display = self.create_major_display_table(
                self.lexicon.biphone_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Biphone", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=0)

        elif item_str == TRIPHONES:
            new_display = self.create_major_display_table(
                self.lexicon.triphone_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Triphone", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:int(x[1])],
                cutoff=0)

        elif item_str == WORD_NEIGHBORS:
            word_to_freq = self.lexicon.word_to_freq
            new_display = self.create_major_display_table(
                self.lexicon.word_to_neighbors.items(),
                key=lambda x:int(word_to_freq[x[0]]), reverse=True,
                headers=["Word", "Word Frequency", "Neighbors"],
                row_cell_functions=[lambda x:x[0],
                    lambda x : int(word_to_freq[x[0]]), lambda x:" ".join(x[1])],
                cutoff=0)

        elif item_str == VISUALIZED_GRAPH:
            graph_width = self.screen_width - TREEWIDGET_WIDTH_MAX - 50
            graph_height = self.screen_height - 50
            html_name = "show_manifold.html"
            #html_name = "_test_show_manifold.html"

            manifold_name = "{}_{}_{}_manifold.json".format(
                Path(self.corpus_name).stem, self.max_word_types, self.n_neighbors)
            manifold_dir = Path(Path(self.corpus_filename).parent, "neighbors")
            manifold_filename = str(Path(manifold_dir, manifold_name))

            viz_html = Path(os.path.abspath("."), "visualization", html_name)
                # TODO: does this work in Windows? we need an *absolute* path here

            # write the show_manifold html file
            with viz_html.open("w") as f:
                print(SHOW_MANIFOLD_HTML.format(graph_width, graph_height,
                    manifold_filename), file=f)

            new_display = QWebView()
            new_display.setUrl(QUrl(viz_html.as_uri()))

        self.load_main_window(major_display=new_display,
                              parameter_window=new_parameter_window)


    def create_major_display_table(self, input_iterable,
            key=lambda x : x, reverse=False,
            headers=None, row_cell_functions=None, cutoff=0,
            set_text_alignment=None):
        """
            This is a general function for creating a tabular display for the
            major display.
        """

        if not input_iterable:
            print("Warning: input is empty", flush=True)
            return

        if not hasattr(input_iterable, "__iter__"):
            print("Warning: input is not an iterable", flush=True)
            return

        number_of_headers = len(headers)
        number_of_columns = len(row_cell_functions)

        if number_of_headers != number_of_columns:
            print("Warning: headers and cell functions do not match", flush=True)
            return

        len_input = len(input_iterable)

        table_widget = QTableWidget()
        table_widget.clear()
        table_widget.setSortingEnabled(False)

        # set up row count
        if cutoff and cutoff < len_input:
            actual_cutoff = cutoff
        else:
            actual_cutoff = len_input

        table_widget.setRowCount(actual_cutoff)

        # set up column count and table headers
        table_widget.setColumnCount(number_of_headers)
        table_widget.setHorizontalHeaderLabels(headers)

        # fill in the table
        for row, x in enumerate(sorted_alphabetized(input_iterable, key=key,
                                                    reverse=reverse)):
            for col, fn in enumerate(row_cell_functions):
                cell = fn(x)

                if isinstance(cell, (int, float)):
                    # cell is numeric
                    item = QTableWidgetItem()
                    item.setData(Qt.EditRole, cell)
                else:
                    # cell is not numeric
                    item = QTableWidgetItem(cell)

                if set_text_alignment:
                    for align_col, alignment in set_text_alignment:
                        if col == align_col:
                            item.setTextAlignment(alignment)

                table_widget.setItem(row, col, item)

            if not row < actual_cutoff:
                break

        table_widget.setSortingEnabled(True)
        table_widget.resizeColumnsToContents()

        return table_widget


    def load_main_window(self, major_display=None, parameter_window=None):
        """Refreshes the main window for the updated display content
        (most probably after a click or some event is triggered )
        """
        # get sizes of the three major PyQt objects
        major_display_size = self.majorDisplay.size()
        parameter_window_size = self.parameterWindow.size()
        lexicon_tree_size = self.lexiconTree.size()

        if major_display:
            self.majorDisplay = major_display
        if parameter_window:
            self.parameterWindow = parameter_window

        # apply sizes to the major three objects
        self.majorDisplay.resize(major_display_size)
        self.parameterWindow.resize(parameter_window_size)
        self.lexiconTree.resize(lexicon_tree_size)

        # set up:
        # 1) main splitter (b/w lexicon-tree+parameter window and major display)
        # 2) minor splitter (b/w lexicon-tree and parameter window)
        self.mainSplitter = QSplitter(Qt.Horizontal)
        self.mainSplitter.setHandleWidth(10)
        self.mainSplitter.setChildrenCollapsible(False)

        self.minorSplitter = QSplitter(Qt.Vertical)
        self.minorSplitter.setHandleWidth(10)
        self.minorSplitter.setChildrenCollapsible(False)

        self.minorSplitter.addWidget(self.lexiconTree)
        self.minorSplitter.addWidget(self.parameterWindow)

        self.mainSplitter.addWidget(self.minorSplitter)
        self.mainSplitter.addWidget(self.majorDisplay)

        self.setCentralWidget(self.mainSplitter)


    ### not yet in use ###
    def filePreferencesDialog(self):
        return
        # complete revamp of this function needed, J Lee 2015/8/10

        preferencesDialog = QDialog()
        preferencesDialog.resize(640, 480)
        preferencesDialog.setWindowTitle('Preferences')

        # tab for Lxa text-->signatures parameters
        lxaTab = QWidget()

        language, corpus, datafolder = self.loadConfig()

        self.para_language = QLineEdit()
        self.para_language.setText(language)
        self.para_corpus = QLineEdit()
        self.para_corpus.setText(corpus)
        self.para_datafolder = QLineEdit()
        self.para_datafolder.setText(datafolder)

        self.para_MinimumStemLength = QDoubleSpinBox()
        self.para_MinimumStemLength.setValue(4)
        self.para_MaximumAffixLength = QDoubleSpinBox()
        self.para_MaximumAffixLength.setValue(3)
        self.para_MinimumNumberofSigUses = QDoubleSpinBox()
        self.para_MinimumNumberofSigUses.setValue(50)

        lxaTabLayout = QVBoxLayout()
        lxaTabLayout.addWidget(QLabel("language"))
        lxaTabLayout.addWidget(self.para_language)
        lxaTabLayout.addWidget(QLabel("corpus filename"))
        lxaTabLayout.addWidget(self.para_corpus)
        lxaTabLayout.addWidget(QLabel("datafolder"))
        lxaTabLayout.addWidget(self.para_datafolder)
        lxaTabLayout.addWidget(self.para_MinimumStemLength)
        lxaTabLayout.addWidget(self.para_MaximumAffixLength)
        lxaTabLayout.addWidget(self.para_MinimumNumberofSigUses)

        lxaTab.setLayout(lxaTabLayout)

        # overall layout
        tabWidget = QTabWidget()
        tabWidget.addTab(lxaTab, "test")

        saveButton = QPushButton("Save")
        saveButton.clicked.connect(self.updatePreferences)

        runButton = QPushButton("Run")
        runButton.clicked.connect(self.runLxa)

        overallLayout = QVBoxLayout()
        overallLayout.addWidget(tabWidget)
        overallLayout.addWidget(saveButton)
        overallLayout.addWidget(runButton)

        preferencesDialog.setLayout(overallLayout)
        preferencesDialog.exec_()


    ### not yet in use ###
    def updatePreferences(self):
        # complete revamp of this function needed, J Lee 2015/8/10

        self.language = self.para_language.text()
        self.corpus = self.para_corpus.text()
        self.datafolder = self.para_datafolder.text()

        self.MinimumStemLength = self.para_MinimumStemLength.value()
        self.MaximumAffixLength = self.para_MaximumAffixLength.value()
        self.MinimumNumberofSigUses = self.para_MinimumNumberofSigUses.value()

        config_path = Path(self.configfilename)

        config = {'language': self.language,
                  'corpus': self.corpus,
                  'datafolder': self.datafolder}

        with config_path.open('w') as config_file:
            json.dump(config, config_file)

#------------------------------------------------------------------------------#

def main():
    app = QApplication(sys.argv)
    app.setStyle('cleanlooks')
    app.setApplicationName("Linguistica")

    # get screen resolution
    resolution = app.desktop().screenGeometry()
    screen_width = resolution.width()
    screen_height = resolution.height()

    # launch graphical user interface
    form = MainWindow(screen_height, screen_width)
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()

