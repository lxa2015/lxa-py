Linguistica 5.1
===============

This is the Python version of Linguistica, version 5.1, currently under active development. It consists of a suite of tools for the unsupervised learning of lingusitic structure, with a corpus text file as input data.

Download
--------

Run the following:

    $ git clone https://github.com/lxa2015/lxa-py.git
    $ cd lxa-py/

Now you are at the directory `lxa-py/` and ready to use any of the core components of Linguistica.

Core components
---------------

The core components are the following (more are being added):

- `lxa5.py`
- `ngrams.py`
- `manifold.py`
- `tries.py`
- `phon.py`
- `wordbreaker.py` (code refactoring/optimization in progress)

Note: For `manifold.py`, the following packages are required: [networkx](https://networkx.github.io/), [numpy](http://www.numpy.org/), and [scipy](http://www.scipy.org/). To install these, please be sure to do so for your Python 3 distribution, not Python 2. (If you are using Ubuntu, run this: `sudo apt-get install python3-networkx python3-numpy python3-scipy`)


The input-output relatioships between various core components and their outputs are as follows:

    corpus text ---ngrams.py---> wordlist ---lxa5.py----> morphological signatures
              |            |            |
              |            |            | ---tries.py---> tries
              |            |            |
              |            |            | ---phon.py----> phonlist, biphons, triphons
              |            |
              |            | ---> word bigrams, ---manifold.py---> word neighbors,
              |                   word trigrams                    neighbor graph
              |
              | ---wordbreaker.py---> word segmentation


Running the core components
---------------------------

For any of the core components, run this for what parameters can be changed (assuming you are at the directory `lxa-py/`):

    $ python3 <file> -h

Currently, the following three major parameters are especially important:

- [language]: the name of the language under study
- [corpus]: the filename of the corpus text (including the file extension, if any)
- [datafolder]: the directory where the folder `[language]` (containing `[corpus]`) is located

The following directory structure is assumed to be in place before anything runs:

    [datafolder]/
        [language]/
            [corpus]

All results and derived datasets will be stored under the `[language]` folder. Please see the details below in the "Outputs" section.

As a concrete example, a directory structure may look like this:

    data/
        english/
            english-brown.txt
    lxa-py/
        (all .py files etc from the lxa-py repository)

To run any of the core components with this directory structure (assuming that you are now at the directory `lxa-py`):

    $ python3 <file> --language=english --corpus=english-brown.txt --datafolder=../data

Note that `[datafolder]` takes a *relative* path. After a command like this is run for the first time, `config.json` is created to store the parameters just entered. This allows the user to conveniently run again and reuse the same parameters simply by `python3 <file>` without the optional arguments.


Sample input corpus
-------------------

Sample corpus files (including `english-brown.txt` for the English Brown corpus) can be found [here](https://github.com/lxa2015/datasets).


Outputs
-------

All results and derived datasets are stored in subfolders under the `[language]` folder. Many of them are outputs of Python dictionaries; their filenames are in the form of "AToB", for a map from A to B. All outputs are human-readable `.txt` files, while some of them also have a corresponding `.json` version which is read back into Python in the pipeline.

Output files generated by the core components (with `xxx.txt` as the corpus text input):

- `lxa5.py` (subfolder: `lxa/`)

    * `xxx_WordToSigtransforms.json`
    * `xxx_WordToSigs.json`
    * `xxx_SigToStems.json`

    * `xxx_AffixToSigs.txt`
    * `xxx_SigToStems.txt`
    * `xxx_SigToWords.txt`
    * `xxx_WordToSigs.txt`
    * `xxx_WordToSigtransforms.txt`
    * `xxx_mostFreqWordsNotInSigs.txt`
    * `xxx_WordsInSigs.txt`
    * `xxx_WordsNotInSigs.txt`

- `ngrams.py` (subfolders: `ngrams/`, `dx1/`)

    * `xxx_words.txt`
    * `xxx_bigrams.txt`
    * `xxx_trigrams.txt`
    * `xxx.dx1` (in the `dx1/` subfolder)

- `manifold.py` (subfolder: `neighbors/`)

   (assuming the default settings of 1000 word types and 9 neighbors)

    * `xxx_1000_9_nearest_neighbors.txt`
    * `xxx_1000_9_nearest_neighbors.json`
    * `xxx_1000_9_nearest_neighbors.gexf` (graph data file for Gephi)
    * `xxx_1000_9_shared_contexts.txt`

- `tries.py` (subfolder: `tries/`)

    * `xxx_SF.txt` (successor frequencies)
    * `xxx_PF.txt` (predecessor frequencies)
    * `xxx_trieLtoR.txt`
    * `xxx_trieRtoL.txt`
    * `xxx_Signatures.txt`

- `phon.py` (subfolder: `phon/`)

    * `xxx_phones.json`
    * `xxx_biphones.json`
    * `xxx_triphones.json`
    * `xxx_phones.txt`
    * `xxx_biphones.txt`
    * `xxx_triphones.txt`

- `wordbreaker.py` (subfolder: `wordbreaking/`)

    * (work in progress)


