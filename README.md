Linguistica 5.0
===============

This is the Python version of Linguistica, version 5.0, currently under active development. Everything runs under Python 3.4+. The core components are the following (more are being added):

- lxa5.py
- ngrams.py

Run this for what parameters can be changed:

    $ python3 <file> -h

Currently, the following three major parameters are especially important:

- [language]: the name of the language under study
- [corpus]: the filename of the corpus text (including the file extension, if any)
- [datafolder]: the directory where the folder [language] (containing [corpus]) is located

The following directory structure is assumed to be in place before anything runs:

    [datafolder]/
        [language]/
            [corpus]

All results and derived datasets will be stored under the `[language]` folder.

An example of the directory structure looks like this:

    data/
        english/
            english-brown.txt

Sample corpus files (including `english-brown.txt` for the English Brown corpus) can be found [here](https://github.com/JacksonLLee/datasets) (to be forked to the lxa2015 group here when it matures).

