# Definition of the main window for the Linguistica 5 GUI
# Jackson Lee, 2015

import os
import json
from pathlib import Path

from PyQt5.QtCore import (Qt, QUrl, QCoreApplication)
from PyQt5.QtWidgets import (QDialog, QMainWindow, QWidget,
                             QAction, QHBoxLayout, QVBoxLayout, QTreeWidget,
                             QFileDialog, QLabel, QPushButton, QMessageBox,
                             QTabWidget, QDoubleSpinBox, QLineEdit,
                             QTreeWidgetItem, QTableWidget, QTableWidgetItem,
                             QSplitter, QProgressDialog)
from PyQt5.QtWebKitWidgets import QWebView

from .lexicon import Lexicon
from .worker import LinguisticaComponentsWorker

from .lxa5libgui import (MAIN_WINDOW_WIDTH, MAIN_WINDOW_HEIGHT,
    TREEWIDGET_WIDTH_MIN, TREEWIDGET_WIDTH_MAX, TREEWIDGET_HEIGHT_MIN,
    WORDLIST, WORD_NGRAMS, BIGRAMS, TRIGRAMS,
    SIGNATURES, SIGS_TO_STEMS, WORDS_TO_SIGS,
    TRIES, WORDS_AS_TRIES, SF_TRIES, PF_TRIES,
    PHONOLOGY, PHONES, BIPHONES, TRIPHONES,
    MANIFOLDS, WORD_NEIGHBORS, VISUALIZED_GRAPH, SHOW_MANIFOLD_HTML)

from ..lxa5lib import (CONFIG_FILENAME, CONFIG, SEP_SIG, sorted_alphabetized)

class MainWindow(QMainWindow):

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


    def update_progress(self, progress_text, progress_number):
        """Update the progress dialog. This function is triggered by the
        "progress_signal" emitted from the linguistica component worker thread.
        """
        self.progressDialog.setLabelText(progress_text)
        self.progressDialog.setValue(progress_number)


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
        self.progressDialog.setValue(5)
            # 0 would make it look like no progress at the beginning...
            # we set it as 5 (= 5% at the beginning) so the user thinks
            # the program is working :-)
        self.progressDialog.setWindowTitle(
            "Processing {}".format(self.corpus_name))
        self.progressDialog.setCancelButton(None)
            # We disable the "cancel" button
            # Setting up a "cancel" mechanism may not be a good idea,
            # since it would probably involve killing the linguistica component
            # worker at *any* point of its processing.
            # This may have undesirable effects (e.g., freezing the GUI) -- BAD!
        self.progressDialog.resize(400, 100)
        self.progressDialog.show()

        # make sure all GUI stuff up to this point has been processed before
        # doing the real work of running the Lxa components
        QCoreApplication.processEvents() 

        # Now the real work begins here!
        self.lxa_worker.start()

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


    def tree_item_clicked(self, item):
        """trigger the appropriate action when something in the lexicon tree
        is clicked, and update the major display plus parameter window
        """
        item_str = item.text(0)

        if item_str in {WORD_NGRAMS, SIGNATURES, TRIES, SF_TRIES, PF_TRIES,
                        PHONOLOGY, MANIFOLDS}:
            # TODO: work on the SF and PF tries... -- show them etc
            return

        print("loading", item_str, flush=True)

        self.status.clearMessage()
        self.status.showMessage("Loading {}...".format(item_str))

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
            # TODO: show a secondary table on the right of this tabular table
            #       this secondary table probably shows stems and other info
            #       of interest for a selected signature

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

            # TODO: Reorganize the visualization-related files
            # where should the "visualization" be? (rename it to "viz"?)
            # is there a way to generate what d3 needs without having to
            # generate the html/javascript code and file

            graph_width = self.screen_width - TREEWIDGET_WIDTH_MAX - 50
            graph_height = self.screen_height - 70
            html_name = "show_manifold.html"
            #html_name = "_test_show_manifold.html"

            manifold_name = "{}_{}_{}_manifold.json".format(
                Path(self.corpus_name).stem, self.max_word_types, self.n_neighbors)
            manifold_dir = Path(Path(self.corpus_filename).parent, "neighbors")
            manifold_filename = str(Path(manifold_dir, manifold_name))
            print("manifold_filename", manifold_filename)

            viz_html = Path(os.path.abspath("."), "visualization", html_name)
                # TODO: does this work in Windows? we need an *absolute* path here
            print("viz_html", viz_html)

            # write the show_manifold html file
            with viz_html.open("w") as f:
                print(SHOW_MANIFOLD_HTML.format(graph_width, graph_height,
                    manifold_filename), file=f)

            new_display = QWebView()
            new_display.setUrl(QUrl(viz_html.as_uri()))

        self.load_main_window(major_display=new_display,
                              parameter_window=new_parameter_window)

        self.status.clearMessage()
        self.status.showMessage("{} selected".format(item_str))


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

    ######################
    ### not yet in use ###
    ######################
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

    ######################
    ### not yet in use ###
    ######################
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



