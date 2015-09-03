# Definition of Lexicon and MainWindow_Lexicon for the Linguistica 5 GUI
# Jackson Lee, 2015

import json
import os
from pathlib import Path

from PyQt5.QtCore import (Qt, QUrl)
from PyQt5.QtWidgets import (QWidget, QTableWidget, QTableWidgetItem, QLabel,
                             QVBoxLayout, QSplitter)
from PyQt5.QtWebKitWidgets import QWebView

from .lxa5libgui import (
    WORDLIST, WORD_NGRAMS, BIGRAMS, TRIGRAMS,
    SIGNATURES, SIGS_TO_STEMS, WORDS_TO_SIGS,
    TRIES, WORDS_AS_TRIES, SF_TRIES, PF_TRIES,
    PHONOLOGY, PHONES, BIPHONES, TRIPHONES,
    MANIFOLDS, WORD_NEIGHBORS, VISUALIZED_GRAPH, SHOW_MANIFOLD_HTML,
    TREEWIDGET_WIDTH_MAX)

from ..lxa5lib import (sorted_alphabetized, SEP_SIG)

class MainWindow_Lexicon():

    def sig_to_stems_clicked(self, row, col):
        signature = self.sig_to_stems_major_table.item(row, 0).text()
        print(signature)
        stems = self.lexicon.sig_to_stems[signature]
        number_of_stems_per_column = 5

        # create a master list of sublists, where each sublist contains k stems
        # k = number_of_stems_per_column
        stemrow_list = list()
        stemrow = list()
        for i, stem in enumerate(stems, 1):
            stemrow.append(stem)
            if not i % number_of_stems_per_column:
                stemrow_list.append(stemrow)
                stemrow = list()
        if stemrow:
            stemrow_list.append(stemrow)

        # set up the minor table as table widget
        sig_to_stems_minor_table = QTableWidget()
        sig_to_stems_minor_table.horizontalHeader().hide()
        sig_to_stems_minor_table.verticalHeader().hide()
        sig_to_stems_minor_table.clear()
        sig_to_stems_minor_table.setRowCount(len(stemrow_list))
        sig_to_stems_minor_table.setColumnCount(number_of_stems_per_column)

        # fill in the minor table
        for row, stemrow in enumerate(stemrow_list):
            for col, stem in enumerate(stemrow):
                item = QTableWidgetItem(stem)
                sig_to_stems_minor_table.setItem(row, col, item)

        sig_to_stems_minor_table.resizeColumnsToContents()

        minor_table_title = QLabel(
            "{} (number of stems: {})".format(signature, len(stems)))

        minor_table_widget_with_title = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(minor_table_title)
        layout.addWidget(sig_to_stems_minor_table)
        minor_table_widget_with_title.setLayout(layout)

        new_display = QSplitter(Qt.Horizontal)
        new_display.setHandleWidth(10)
        new_display.setChildrenCollapsible(False)

        new_display.addWidget(self.sig_to_stems_major_table)
        new_display.addWidget(minor_table_widget_with_title)
        new_display_width = self.majorDisplay.width()/2
        new_display.setSizes(
            [new_display_width * 0.4, new_display_width * 0.6])

        self.load_main_window(major_display=new_display)
        self.status.clearMessage()
        self.status.showMessage("{} selected".format(signature))

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
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=0)

        elif item_str == BIGRAMS:
            new_display = self.create_major_display_table(
                self.lexicon.bigram_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Bigram", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=2000)

        elif item_str == TRIGRAMS:
            new_display = self.create_major_display_table(
                self.lexicon.trigram_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Trigram", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=2000)

        elif item_str == SIGS_TO_STEMS:
            self.sig_to_stems_major_table = self.create_major_display_table(
                self.lexicon.sig_to_stems.items(),
                key=lambda x:len(x[1]), reverse=True,
                headers=["Signature", "Stem count", "A few stems"],
                row_cell_functions=[lambda x : x[0], lambda x : len(x[1]),
                    lambda x : ", ".join(sorted(x[1])[:2]) + ", ..."],
                cutoff=0)
            self.sig_to_stems_major_table.cellClicked.connect(
                self.sig_to_stems_clicked)
            new_display = self.sig_to_stems_major_table

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
                RtoL_trie = " ".join(self.lexicon.tries_RtoL[word])
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
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=0)

        elif item_str == BIPHONES:
            new_display = self.create_major_display_table(
                self.lexicon.biphone_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Biphone", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=0)

        elif item_str == TRIPHONES:
            new_display = self.create_major_display_table(
                self.lexicon.triphone_to_freq.items(),
                key=lambda x:x[1], reverse=True, headers=["Triphone", "Frequency"],
                row_cell_functions=[lambda x:x[0], lambda x:x[1]],
                cutoff=0)

        elif item_str == WORD_NEIGHBORS:
            word_to_freq = self.lexicon.word_to_freq
            new_display = self.create_major_display_table(
                self.lexicon.word_to_neighbors.items(),
                key=lambda x: word_to_freq[x[0]], reverse=True,
                headers=["Word", "Word Frequency", "Neighbors"],
                row_cell_functions=[lambda x:x[0],
                    lambda x : word_to_freq[x[0]], lambda x:" ".join(x[1])],
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


class Lexicon:
    def __init__(self, corpus_filename):

        self.corpus_filename = corpus_filename
        #----------------------------------------------------------------------#
        ###   data directly generated by other .py programs   ###

        # results from ngrams.py
        self.word_to_freq = None
        self.bigram_to_freq = None
        self.trigram_to_freq = None

        self.word_to_freq_path = None
        self.bigram_to_freq_path = None
        self.trigram_to_freq_path = None

        # results from lxa5.py
        self.sig_to_stems = None
        self.word_to_sigs = None

        self.sig_to_stems_path = None
        self.word_to_sigs_path = None

        # results from tries.py
        self.tries_LtoR = None
        self.tries_RtoL = None

        self.tries_LtoR_path = None
        self.tries_RtoL_path = None

        # results from phon.py
        self.phone_to_freq = None
        self.biphone_to_freq = None
        self.triphone_to_freq = None

        self.phone_to_freq_path = None
        self.biphone_to_freq_path = None
        self.triphone_to_freq_path = None

        # results from manifold.py
        self.word_to_neighbors = None
        self.word_to_neighbors_path = None

        self.retrieve_data_paths()

        #----------------------------------------------------------------------#

        self.n_types = None
        self.n_tokens = None


    def clear_data(self):

        # why do we need this function? at any given moment, we are just
        # looking at results for *one* (not many) of the following things
        # so we need only one thing loaded at any given point and should
        # clear everything else so as to save memory
        # will we change our mind on this point?
        # -- Jackson Lee, 2015/8/11

        # results from ngrams.py
        self.word_to_freq = None
        self.bigram_to_freq = None
        self.trigram_to_freq = None

        # results from lxa5.py
        self.sig_to_stems = None
        self.word_to_sigs = None

        # results from tries.py
        self.tries_LtoR = None
        self.tries_RtoL = None

        # results from phon.py
        self.phone_to_freq = None
        self.biphone_to_freq = None
        self.triphone_to_freq = None

        # results from manifold.py
        self.word_to_neighbors = None


    def retrieve_data_paths(self):
        corpus_dir = Path(self.corpus_filename).parent
        corpus_stem = Path(self.corpus_filename).stem

        # results from ngrams.py
        ngrams_path = Path(corpus_dir, "ngrams")
        self.word_to_freq_path = Path(ngrams_path, corpus_stem + "_words.json")
        self.bigram_to_freq_path = Path(ngrams_path, corpus_stem + "_bigrams.json")
        self.trigram_to_freq_path = Path(ngrams_path,
            corpus_stem + "_trigrams.json")

        # results from lxa5.py
        lxa_path = Path(corpus_dir, "lxa")
        self.sig_to_stems_path = Path(lxa_path, corpus_stem + "_SigToStems.json")
        self.word_to_sigs_path = Path(lxa_path, corpus_stem + "_WordToSigs.json")

        # results from tries.py
        tries_path = Path(corpus_dir, "tries")
        self.tries_LtoR_path = Path(tries_path, corpus_stem + "_trieLtoR.json")
        self.tries_RtoL_path = Path(tries_path, corpus_stem + "_trieRtoL.json")

        # results from phon.py
        phon_path = Path(corpus_dir, "phon")
        self.phone_to_freq_path = Path(phon_path, corpus_stem + "_phones.json")
        self.biphone_to_freq_path = Path(phon_path, corpus_stem + "_biphones.json")
        self.triphone_to_freq_path = Path(phon_path,
            corpus_stem + "_triphones.json")

        # results from manifold.py
        manifold_path = Path(corpus_dir, "neighbors")
        self.word_to_neighbors_path = Path(manifold_path,
                                         corpus_stem + "_1000_9_neighbors.json")
            # TODO: allow other number of word types/neighbors


    def retrieve_data(self, item_str, cleardata=True):
        if cleardata:
            self.clear_data()

        if item_str == WORDLIST:
            self.word_to_freq = json.load(self.word_to_freq_path.open())
        elif item_str == BIGRAMS:
            self.bigram_to_freq = json.load(self.bigram_to_freq_path.open())
        elif item_str == TRIGRAMS:
            self.trigram_to_freq = json.load(self.trigram_to_freq_path.open())

        elif item_str == SIGS_TO_STEMS:
            self.sig_to_stems = json.load(self.sig_to_stems_path.open())
        elif item_str == WORDS_TO_SIGS:
            self.word_to_sigs = json.load(self.word_to_sigs_path.open())

        elif item_str == WORDS_AS_TRIES:
            self.tries_LtoR = json.load(self.tries_LtoR_path.open())
            self.tries_RtoL = json.load(self.tries_RtoL_path.open())

        elif item_str == PHONES:
            self.phone_to_freq = json.load(self.phone_to_freq_path.open())
        elif item_str == BIPHONES:
            self.biphone_to_freq = json.load(self.biphone_to_freq_path.open())
        elif item_str == TRIPHONES:
            self.triphone_to_freq = json.load(self.triphone_to_freq_path.open())

        elif item_str == WORD_NEIGHBORS:
            self.word_to_freq = json.load(self.word_to_freq_path.open())
            self.word_to_neighbors = json.load(self.word_to_neighbors_path.open())

        elif item_str == VISUALIZED_GRAPH:
            return

