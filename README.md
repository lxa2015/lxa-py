Linguistica 5.1
===============

This is the Python version of Linguistica, version 5.1, currently under active development.
It consists of a suite of tools for the unsupervised learning of lingusitic structure,
with a corpus text file as input data.

The current branch at https://github.com/lxa2015/lxa-py/tree/gui-test is a test
version, in the anticipation of a graphical user interface.


Download
--------

To try out this test version of Linguistica 5, run the following
(`gui-test` is the name of this branch):

    $ git clone -b gui-test https://github.com/lxa2015/lxa-py.git
    $ cd lxa-py/

(`gui-test` is the name of this branch. This command clones this branch only.)

Now you are at the directory `lxa-py/` and ready to launch the graphical user
interface (GUI) or use any of the core components of Linguistica as command line tools.

GUI
---

`main.pyw` is the central hub of the GUI. Be sure that it is an executable
before launching the GUI:

    $ chmod +x main.pyw
    $ ./main.pyw

After the GUI pops up, go to `File` --> `Read corpus...` to specify a corpus
text file. (If the GUI determines that the selected corpus file has not been
run before, all Linguistica components will automatically be run for this file.)
A navigation tree will appear on the left of the GUI.
Clicking the items on the tree will trigger the corresponding content to show
up on the right of the GUI -- try `Visualized graph` in particular.
(Some of the items are not yet activated -- work in progress.)

Core components
---------------

The core components are the following (more are being added):

- `signature`
- `ngram`
- `manifold`
- `trie`
- `phon`
- `neighbors` (work in progress; currently disabled)
- `wordbreaker` (work in progress; currently disabled)

Note: The `manifold` and `neighbors` components depend on the following packages: 
[networkx](https://networkx.github.io/), 
[numpy](http://www.numpy.org/), and [scipy](http://www.scipy.org/). 
To install these, please be sure to do so for your Python 3 distribution, not Python 2. 
(If you are using Ubuntu, run this: `sudo apt-get install python3-networkx python3-numpy python3-scipy`)


The input-output relatioships between various core components (in caps below) and their outputs are as follows:

    corpus text ---NGRAM---> wordlist ---SIGNATURE----> morphological signatures
          |            |            |
          |            |            | ---TRIE---> tries, successor/predecessor frequencies
          |            |            |
          |            |            | ---PHON----> phonlist, biphons, triphons
          |            |
          |            | ---> word bigrams, ---MANIFOLD---> word neighbors,
          |                   word trigrams                    master neighbor graph
          |                                                      |
          |                                                      | NEIGHBORS
          |                                                      v
          |                                                    neighbor graph
          |                                                    by seed words
          | ---WORDBREAKER---> word segmentation


Running the core components
---------------------------

For what parameters can be changed (assuming you are at the directory `lxa-py/`):

    $ python3 lxa5.py -h

To run any of the core components:

    $ python3 lxa5.py <component> [optional-arguments]

`<component>` should be replaced by one of the names of the core components introduced above.

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
        (all files etc from this branch of the lxa-py repository)
        lxa5.py
        linguistica/
        ...

To run, say, the `signature` component with this directory structure (assuming that you are now at the directory `lxa-py`):

    $ python3 lxa5.py signature --language=english --corpus=english-brown.txt --datafolder=../data

Note that `[datafolder]` takes a *relative* path. The values of `[language]`, `[corpus]`, and `[datafolder]` tell the program to look for the file `../data/english/english-brown.txt` relative to the current directory at `lxa-py`. After a command like this is run for the first time, `config.json` is created to store the configuration parameters. This allows the user to conveniently run again and reuse the same parameters simply by `python3 lxa5.py signature` without the optional arguments.


Sample input corpus
-------------------

Sample corpus files (including `english-brown.txt` for the English Brown corpus) can be found [here](https://github.com/lxa2015/datasets).


Outputs
-------

All results and derived datasets are stored in subfolders under the `[language]` folder. Many of them are outputs of Python dictionaries; their filenames are in the form of "AToB", for a map from A to B. All outputs are human-readable `.txt` files, while some of them also have a corresponding `.json` version which is read back into Python in the pipeline. Sample files for English and French are in the [datasets](https://github.com/lxa2015/datasets) repository.

Output files generated by the core components (with `xxx.txt` as the corpus text input):

- `signature` (subfolder: `lxa/`)

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

- `ngram` (subfolders: `ngrams/`, `dx1/`)

    * `xxx_words.txt`
    * `xxx_bigrams.txt`
    * `xxx_trigrams.txt`
    * `xxx_words.json`
    * `xxx_bigrams.json`
    * `xxx_trigrams.json`
    * `xxx.dx1` (in the `dx1/` subfolder)

- `manifold` (subfolder: `neighbors/`, `word_contexts/`)

   (assuming the default settings of 1000 word types and 9 neighbors)

    * `xxx_1000_9_neighbors.txt`
    * `xxx_1000_9_neighbors.json`
    * `xxx_1000_9_neighbors.gexf` (graph data file for Gephi)
    * `xxx_1000_9_manifold.json` (for GUI d3 visualization)
    * `xxx_1000_9_shared_contexts.txt`
    * `xxx_1000_9_ImportantContextToWords.txt`

    * `xxx_1000_9_contextdict.json` (in `word_contexts/`)
    * `xxx_1000_9_worddict.json` (in `word_contexts/`)
    * `xxx_1000_9_ContextToWords.json` (in `word_contexts/`)
    * `xxx_1000_9_WordToContexts.json` (in `word_contexts/`)

- `neighbors` (subfolder: `neighbors/`)

    * (neighbor graphs for the given seed words)

- `trie` (subfolder: `tries/`)

    * `xxx_SF.txt` (successor frequencies)
    * `xxx_PF.txt` (predecessor frequencies)
    * `xxx_SF.json`
    * `xxx_PF.json`
    * `xxx_trieLtoR.txt`
    * `xxx_trieRtoL.txt`
    * `xxx_trieLtoR.json`
    * `xxx_trieRtoL.json`
    * `xxx_Signatures.txt`

- `phon` (subfolder: `phon/`)

    * `xxx_phones.json`
    * `xxx_biphones.json`
    * `xxx_triphones.json`
    * `xxx_phones.txt`
    * `xxx_biphones.txt`
    * `xxx_triphones.txt`

- `wordbreaker` (subfolder: `wordbreaking/`)

    * (work in progress)


