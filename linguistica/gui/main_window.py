# Definition of the main window for the Linguistica 5 GUI
# Jackson Lee, 2015

import os
import json
import time
from pathlib import Path

from PyQt5.QtCore import (Qt, QUrl, QCoreApplication)
from PyQt5.QtWidgets import (QDialog, QMainWindow, QWidget,
                             QAction, QHBoxLayout, QVBoxLayout, QTreeWidget,
                             QFileDialog, QLabel, QPushButton, QMessageBox,
                             QTabWidget, QDoubleSpinBox, QLineEdit,
                             QTreeWidgetItem, 
                             QSplitter, QProgressDialog)

from .lexicon import (Lexicon, MainWindow_Lexicon)
from .worker import LinguisticaComponentsWorker
from .preferences import MainWindow_Preferences

from .lxa5libgui import (MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT,
    TREEWIDGET_WIDTH_MIN, TREEWIDGET_WIDTH_MAX, TREEWIDGET_HEIGHT_MIN,
    WORDLIST, WORD_NGRAMS, BIGRAMS, TRIGRAMS,
    SIGNATURES, SIGS_TO_STEMS, WORDS_TO_SIGS,
    TRIES, WORDS_AS_TRIES, SF_TRIES, PF_TRIES,
    PHONOLOGY, PHONES, BIPHONES, TRIPHONES,
    MANIFOLDS, WORD_NEIGHBORS, VISUALIZED_GRAPH, SHOW_MANIFOLD_HTML)

from ..lxa5lib import (CONFIG_FILENAME, CONFIG)

class MainWindow(QMainWindow, MainWindow_Lexicon, MainWindow_Preferences):

    def __init__(self, screen_height, screen_width,
            version, author, parent=None):
        super(MainWindow, self).__init__(parent)

        self.screen_width = screen_width
        self.screen_height = screen_height
        self.version = version

        # basic main window settings
        self.dirty = False
        self.resize(MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT)
        self.setWindowTitle('Linguistica {}'.format(self.version))

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

        self.status = self.statusBar()
        self.status.setSizeGripEnabled(False)
        self.status.showMessage("No corpus text file loaded. "
                                "To select one: File --> Read corpus...")

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
        except (TypeError, KeyError):
            open_dir = "." # current directory

        open_file_dialog = QFileDialog()
        fname = QFileDialog.getOpenFileName(self,
                                        "Open a new corpus data file", open_dir)

        # HACK: fname is supposed to be a string (at least according to the
        # PyQt5 documentation), but for some reason fname is a tuple.
        # So we need this hack to make sure that fname is a string of a filename
        # -- Jackson Lee, 2015/06/22

        # update: it's turned out that this behavior is due to compatibility
        # between PyQt and PySide. The "tuple" behavior is in line with the
        # newer API2 for PyQt. (PyQt on python 3 uses API2 by default.)
        # more here: http://srinikom.github.io/pyside-bz-archive/343.html
        # so perhaps we keep our current hack for now?
        # -- Jackson Lee, 2015/08/24

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


    def update_progress(self, progress_text, target_percentage, gradual=True):
        """Update the progress dialog. This function is triggered by the
        "progress_signal" emitted from the linguistica component worker thread.
        """
        self.progressDialog.setLabelText(progress_text)
        if gradual:
            current_percentage = self.progressDialog.value()
            for percentage in range(current_percentage, target_percentage + 1):
                self.progressDialog.setValue(percentage)
                QCoreApplication.processEvents()
                time.sleep(0.1)
        else:
            self.progressDialog.setValue(target_percentage)
            QCoreApplication.processEvents()


    def run_corpus(self):
        if not self.valid_filename():
            return

        self.status.clearMessage()
        self.status.showMessage(
            "Running the corpus {} now...".format(self.corpus_name))

        print("\nCorpus text file in use:\n{}\n".format(self.corpus_filename),
            flush=True)

        # set up the Linguistica components worker
        # The worker is a QThread. We spawn this thread, and the linguistica
        # components run on this new thread but not the "main" thread for the GUI.
        # This makes the GUI still responsive
        # while the long and heavy running process of
        # the Linguistica components is ongoing.
        self.lxa_worker = LinguisticaComponentsWorker(
                            self.corpus_filename, self.config)
        self.lxa_worker.progress_signal.connect(self.update_progress)

        # set up progress dialog
        self.progressDialog = QProgressDialog()
        self.progressDialog.setRange(0, 100) # it's like from 0% to 100%
        self.progressDialog.setLabelText("Extracting word ngrams...")
        self.progressDialog.setValue(0) # initialize as 0 (= 0%)
        self.progressDialog.setWindowTitle(
            "Processing {}".format(self.corpus_name))
        self.progressDialog.setCancelButton(None)
            # We disable the "cancel" button
            # Setting up a "cancel" mechanism may not be a good idea,
            # since it would probably involve killing the linguistica component
            # worker at *any* point of its processing.
            # This may have undesirable effects (e.g., freezing the GUI) -- BAD!
        self.progressDialog.show()

        # make sure all GUI stuff up to this point has been processed before
        # doing the real work of running the Lxa components
        QCoreApplication.processEvents() 

        # Now the real work begins here!
        self.lxa_worker.start()

        if self.progressDialog.value() < 100:
            self.progressDialog.setValue(100)
        QCoreApplication.processEvents()

        # check if corpus has been run before
        # see if updating config is needed (by writing a new config json file)
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
        self.status.clearMessage()
        self.status.showMessage("{} processed".format(self.corpus_name))


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

        self.status.clearMessage()
        self.status.showMessage("Navigation tree populated")
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


