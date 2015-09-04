# Definition of the class LinguisticaComponentsWorker for the Linguistica 5 GUI
# Jackson Lee, 2015

import multiprocessing as mp
import time

from PyQt5.QtCore import (QThread, pyqtSignal, QCoreApplication)

from .. import signature
from .. import ngram
from .. import trie
from .. import phon
from .. import manifold

# If we *have* to run the Linguistica components (e.g., the "ngram", "manifold", 
# "signature" programs)---because we load the corpus for the very first time or
# because we want to rerun the corpus for some reason---then we spawn another
# thread to set up a "Linguistica component worker" using QThread.
# In this way, this worker (with lots of heavy computational work) works in a
# separate thread that is not the main thread for the GUI, and therefore the GUI
# stays responsive and (most probably) nothing freezes.

class LinguisticaComponentsWorker(QThread):

    # progress_signal is a custom PyQt signal. It has to be defined within this
    # QThread subclass but *outside* __init__ here.

    progress_signal = pyqtSignal(str, int, bool)
    # str is for the progress label text
    # int is the progress percentage target, for updating the progress bar
    # bool (True or False) is whether the progress percentage increments
    #   gradually or not

    def __init__(self, corpus_filename, config, parent=None):
        QThread.__init__(self, parent)

        self.corpus_filename = corpus_filename
        self.config = config

    def run(self):
        # this "run" method is never explicitly called
        # it is run by the built-in "start" method of this QThread

        # What happens here:  Each of the Linguistica component
        # is run for the specified corpus file with the specified parameters.
        # When a component is done, emit a signal with info to update the
        # progress dialog label text and progress bar

        # we are using multiprocessing (specifically, the Process class)
        # to parallelize the {signature, trie, phon} components

        self.progress_signal.emit("Extracting word ngrams...", 30, True)
        self.run_ngram()

        # make sure that the progress bar has hit 20%
        self.progress_signal.emit(
            "Working on signatures, tries, phonology...", 30, False)
        QCoreApplication.processEvents()

        self.progress_signal.emit(
            "Working on signatures, tries, phonology...", 80, True)
        signature_process = mp.Process(target=self.run_signature)
        trie_process = mp.Process(target=self.run_trie)
        phon_process = mp.Process(target=self.run_phon)
        signature_process.start()
        trie_process.start()
        phon_process.start()

        # the three "join" statements make sure that they are ALL finished
        # before the manifold component is run
        signature_process.join()
        trie_process.join()
        phon_process.join()

        # make sure that the progress bar has hit 80%
        self.progress_signal.emit("Computing word neighbors...", 80, False)
        QCoreApplication.processEvents()
        time.sleep(0.5)

        self.progress_signal.emit("Computing word neighbors...", 99, True)
        self.run_manifold()

        self.progress_signal.emit("Corpus processed", 100, False)
        QCoreApplication.processEvents()

    def run_ngram(self):
        ngram.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"])

    def run_signature(self):
        signature.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"],
            MinimumStemLength=self.config["min_stem_length"],
            MaximumAffixLength=self.config["max_affix_length"],
            MinimumNumberofSigUses=self.config["min_sig_use"])

    def run_trie(self):
        trie.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"],
            MinimumStemLength=self.config["min_stem_length"],
            MinimumAffixLength=self.config["min_affix_length"],
            SF_threshold=self.config["min_sf_pf_count"])

    def run_phon(self):
        phon.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"])

    def run_manifold(self):
        manifold.main(filename=self.corpus_filename,
            maxwordtypes=self.config["max_word_types"],
            nNeighbors=self.config["n_neighbors"],
            nEigenvectors=self.config["n_eigenvectors"],
            mincontexts=self.config["min_context_use"])


