Linguistica 5.1
===============

This is the Python version of Linguistica, version 5.1, currently under active development. Everything runs under Python 3.4+. The core components are the following (more are being added):

- lxa5.py
- ngrams.py
- manifold.py
- tries.py
- phon.py

Note: For `manifold.py`, the following packages are required: [networkx](https://networkx.github.io/), [numpy](http://www.numpy.org/), and [scipy](http://www.scipy.org/). To install these, please be sure to do so for your Python 3 distribution, not Python 2. (If you are using Ubuntu, run this: `sudo apt-get install python3-networkx python3-numpy python3-scipy`)

For any of the core components, run this for what parameters can be changed:

    $ python3 <file> -h

Currently, the following three major parameters are especially important:

- [language]: the name of the language under study
- [corpus]: the filename of the corpus text (including the file extension, if any)
- [datafolder]: the directory where the folder `[language]` (containing `[corpus]`) is located

The following directory structure is assumed to be in place before anything runs:

    [datafolder]/
        [language]/
            [corpus]

All results and derived datasets will be stored under the `[language]` folder.

An example of the directory structure looks like this:

    data/
        english/
            english-brown.txt

To run any of the core components with this directory structure (assuming the `.py` file is in the same directory as and parallel to  the `data` folder):

    $ python3 <file> --language=english --corpus=english-brown.txt --datafolder=data

After a command like this is run for the first time, `config.json` is created to store the parameters just entered. This allows the user to conveniently run again and reuse the same parameters simply by `python3 <file>` without the optional arguments.

Sample corpus files (including `english-brown.txt` for the English Brown corpus) can be found [here](https://github.com/lxa2015/datasets).

