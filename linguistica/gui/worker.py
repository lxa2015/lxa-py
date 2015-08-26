# Definition of the class LinguisticaComponentsWorker for the Linguistica 5 GUI
# Jackson Lee, 2015

from PyQt5.QtCore import (QThread, pyqtSignal)

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

    progress_signal = pyqtSignal(str, int)
    # str is for the progress label text
    # int is for the progress number for updating the progress bar

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

        ngram.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"])
        self.progress_signal.emit("Finding morphological signatures...", 20)

        signature.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"],
            MinimumStemLength=self.config["min_stem_length"],
            MaximumAffixLength=self.config["max_affix_length"],
            MinimumNumberofSigUses=self.config["min_sig_use"])
        self.progress_signal.emit("Computing tries...", 40)

        trie.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"],
            MinimumStemLength=self.config["min_stem_length"],
            MinimumAffixLength=self.config["min_affix_length"],
            SF_threshold=self.config["min_sf_pf_count"])
        self.progress_signal.emit("Working on phonology...", 60)

        phon.main(filename=self.corpus_filename,
            maxwordtokens=self.config["max_word_tokens"])
        self.progress_signal.emit("Computing word neighbors...", 80)

        manifold.main(filename=self.corpus_filename,
            maxwordtypes=self.config["max_word_types"],
            nNeighbors=self.config["n_neighbors"],
            nEigenvectors=self.config["n_eigenvectors"],
            mincontexts=self.config["min_context_use"])
        self.progress_signal.emit("Corpus processed", 100)


