# Linguistica 5.1 (under development)

This is the Python version of Linguistica, version 5.1, currently under active development.
It consists of a suite of tools for the unsupervised learning of lingusitic structure,
with a corpus text file as input data.

The current branch at https://github.com/lxa2015/lxa-py/tree/gui-test is a test
version, in the anticipation of a graphical user interface.

Linguistica 5.1 is a collection of several core components (more are being added):

- `ngram`
- `signature`
- `trie`
- `phon`
- `manifold`
- `neighbors` (work in progress; currently disabled)
- `wordbreaker` (work in progress; currently disabled)

With an unannotated corpus text as input, these components learn linguistic structure
at various levels. The input-output relatioships between the components (in caps below) and their outputs are as follows:

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


## Requirements

Linguistica 5.1 runs on Python 3.4+.

The Python packages [networkx](https://networkx.github.io/), 
[numpy](http://www.numpy.org/), and [scipy](http://www.scipy.org/) are required. 
To install these, please be sure to do so for your Python 3 distribution, not Python 2. 
(If you are using Ubuntu, run this: `sudo apt-get install python3-networkx python3-numpy python3-scipy`)

If you intend to run Linguistica using the graphical user interface,
[PyQt5](https://riverbankcomputing.com/software/pyqt/download5)
(including the WebKit module) is required. (If you are on Ubuntu, run this:
`sudo apt-get install python3-sip python3-pyqt5 python3-pyqt5.qtwebkit`)


## Download

To try out this test version of Linguistica 5.1, run the following:

    $ git clone -b gui-test https://github.com/lxa2015/lxa-py.git
    $ cd lxa-py/

(`gui-test` is the name of this branch.)

Now you are at the directory `lxa-py/` and ready to either launch the graphical user
interface or use any of the core components of Linguistica as command line tools.

## Running Linguistica 5

Linguistica 5 can be run by either the graphical user interface (GUI) or the
command line interface.

### 1. Graphical user interface (GUI)

`main.pyw` is the central hub of the GUI. Before launching the GUI, be sure that
it is an executable:

    $ chmod +x main.pyw
    $ ./main.pyw

After the GUI pops up, go to `File` --> `Read corpus...` to specify a corpus
text file. (If the GUI determines that the selected corpus file has not been
run before, all Linguistica components will automatically be run for this file.)
A navigation tree will appear on the left of the GUI.
Clicking the items on the tree will trigger the corresponding content to show
up in the major display area on the right of the GUI.
(Some items and features are not yet added/activated -- work in progress.)


### 2. Command line interface

To run Linguistica 5.1 using the command line interface, run this:

    $ python3 lxa5.py all

If you run this for the very first time, you will be prompted to enter information
about where the corpus text file is on your local drive. Currently, three parameters
jointly determine the location of the corpus file:

- [language]: the name of the language under study
- [corpus]: the filename of the corpus text (including the file extension, if any)
- [datafolder]: the directory where the folder `[language]` (containing `[corpus]`) is located

The following directory structure is assumed to be in place:

    [datafolder]/
        [language]/
            [corpus]

All results and derived datasets will be stored under the `[language]` folder. Please see the details below in the "Outputs" section.

The argument `all` means that *all* Linguistica components will be run for the
specified corpus text file. Alternatively, individual components can be run
separately by replacing `all` with one of the following: `ngram`, `signature`,
`trie`, `phon`, `manifold`.

Linguistica 5.1 has numerous parameters defined for different components. These
parameters can be changed by the user via the optional arguments in the command
line interface. For details, run this for the help message:

    $ python3 lxa5.py -h

Examples of running Linguistica 5.1 by the command line interface are given below.


## Examples of running Linguistica 5.1 by command line

Here, we provide some examples of how to run Linguistica 5.1
using the command line interface.
For all the examples, suppose that you have the following directory structure:

    data/
        english/
            english-brown.txt
    lxa-py/
        (all files etc from this branch of the lxa-py repository)
        lxa5.py
        ...

Note that the directories `data/` and `lxa-py/` are at the same directory level.
`english-brown.txt` is the corpus text file in the folder `english/` under `data/`. All results will be found under the `english/` folder.

### Example 1: Running all Linguistica components

To run the corpus `english-brown.txt` with this directory structure
for all Linguistica 5.1 components
(assuming that you are now at the directory `lxa-py` on the terminal):

    $ python3 lxa5.py all --datafolder=../data --language=english --corpus=english-brown.txt

Note that the `[datafolder]` argument takes a *relative* path. The values of `[datafolder]`, `[language]`, and `[corpus]` tell the program to look for the file
`../data/english/english-brown.txt` relative to the current directory at `lxa-py/`.
After a command like this is run for the first time,
`config.json` is created to store the configuration parameters.
This allows the user to conveniently run again and reuse the same parameters
simply by `python3 lxa5.py all` without the optional arguments.

### Example 2: Running one component only

If you would like to run, say, the `signature` component only and would like to set the value of minimum signature use to be 10 (default is 5):

    $ python3 lxa5.py signature --min_sig_use=10

### Example 3: Using a wordlist instead of a corpus text file

It is sometimes the case that only a wordlist (= a text file with a list of word
types, one word per line) but not a corpus text file
for a particular language is available. While it is impossible to run the `manifold` component in this case (due to the lack of word bigrams and trigrams),
it may still be of interest
to run components that rely only on a wordlist. Currently, these components include
`signature`, `trie`, and `phon`. To run any of these components with a wordlist as
input, simply treat the wordlist file as if it were a corpus text file and use
the appropriate command line arguments. These components explicitly ask the user
if the input file is a wordlist or a corpus text file.


## Sample input corpus

Sample corpus files (including `english-brown.txt` for the English Brown corpus) can be found [here](https://github.com/lxa2015/datasets).


## Outputs

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

    * `xxx_1000_9_ContextToWords.json` (in `word_contexts/`)
    * `xxx_1000_9_WordToContexts.json` (in `word_contexts/`)

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

- `neighbors` (subfolder: `neighbors/`)

    * (neighbor graphs for the given seed words)

- `wordbreaker` (subfolder: `wordbreaking/`)

    * (work in progress)


