# General util library for Linguistica 5
# Jackson Lee, 2015

# Note that there is the "lxa5libgui.py" as well, which is only for the GUI.

import sys
import json
from pathlib import Path
from distutils.util import strtobool
from collections import (OrderedDict, Counter)
from itertools import (zip_longest, groupby)

#------------------------------------------------------------------------------#
#    constants
#------------------------------------------------------------------------------#

__version__ = "5.1.0"
__author__ = 'Jackson L. Lee'

SEP_SIG = "/"          # separator between affixes in a sig (NULL/s/ed/ing)
SEP_SIGTRANSFORM = "." # separator between sig and affix (NULL-s-ed-ing.ed)

SEP_NGRAM = "\t" # separator between words in an ngram
    # (e.g., the context "the\tunited\tstates" means "the united states".
    #                    "the\t_\tof" means "the _ of" )

#------------------------------------------------------------------------------#

# configuration, with the "factory settings"

# What programs use what parameters:
#   ngram.py:    max_word_tokens
#   signature.py: max_word_tokens, min_stem_length, max_affix_length, min_sig_use
#   phon.py:      max_word_tokens
#   trie.py:     max_word_tokens, min_stem_length, min_affix_length, min_sf_pf_count
#   manifold.py   max_word_types, n_neighbors, n_eigenvectors, min_context_use
# (See the individual programs for what these parameters mean.)

CONFIG = {"max_word_tokens": 0, # zero means all word tokens
          "min_stem_length": 4,
          "max_affix_length": 4,
          "min_sig_use": 5,
          "min_affix_length": 1,
          "min_sf_pf_count": 3,
          "n_neighbors": 9,
          "n_eigenvectors": 11,
          "min_context_use": 3,
          "max_word_types": 1000,

          "last_filename": "",
          "filenames_run": list(),

          "language" : "",
          "corpus" : "",
          "datafolder" : "",
         }

CONFIG_FILENAME = "config.json"

#------------------------------------------------------------------------------#

# constants for the various programs

PROGRAMS = {"all", "signature", "ngram", "trie", "phon", "manifold"}

PROGRAM_TO_DESCRIPTION = {
    "ngram": "This program extracts word n-grams.",
    "signature": "This program computes morphological signatures.",
    "phon": "This program extracts phon n-grams and works on phonotactics.",
    "trie": "This program computes tries and successor/predecessor frequencies.",
    "manifold": "This program computes word neighbors.",
}


PROGRAM_TO_PARAMETERS = { # useful to know what parameters each program cares about
    "ngram": ["max_word_tokens"],
    "signature": ["max_word_tokens", "min_stem_length", "max_affix_length", 
                  "min_sig_use"],
    "phon": ["max_word_tokens"],
    "trie": ["max_word_tokens", "min_stem_length", "min_affix_length",
             "min_sf_pf_count"],
    "manifold": ["max_word_types", "n_neighbors", "n_eigenvectors",
                 "min_context_use"],
    "all": ["max_word_tokens", "min_stem_length", "max_affix_length",
            "min_sig_use", "min_affix_length", "min_sf_pf_count",
            "n_neighbors", "n_eigenvectors", "min_context_use",
            "max_word_types"],
}


#------------------------------------------------------------------------------#
#    general functions used by various lxa5 components
#------------------------------------------------------------------------------#

def get_wordlist_path_corpus_stem(language, corpus, datafolder, filename, 
                                  maxwordtokens, use_corpus):
    """get wordlist_path and corpus_stem"""
    if maxwordtokens:
        word_token_suffix = "_{}-tokens".format(maxwordtokens)
    else:
        word_token_suffix = ""

    if filename:
        # if "filename" has a corpus filename,
        # then "use_corpus" is also True and doesn't have to be checked

        corpus = Path(filename).name
        corpus_stem = Path(corpus).stem + word_token_suffix
        wordlist_path = Path(Path(filename).parent, "ngrams",
                             corpus_stem + "_words.txt")
    elif use_corpus:
        # "use_corpus" is True, but "filename" has no corpus filename

        corpus_stem = Path(corpus).stem + word_token_suffix
        wordlist_path = Path(datafolder, language, "ngrams",
                             corpus_stem + "_words.txt")
    else:
        # input parameters are for a wordlist, not for a corpus text file
        corpus_stem = Path(corpus).stem
        wordlist_path = Path(datafolder, language, corpus)

    return (wordlist_path, corpus_stem)


def determine_use_corpus():
    """determine if a corpus text or a wordlist is used as input dataset"""
    use_corpus = True
    while True:
        user_input = input("\nWhat kind of input data are you using? "
                           "[\"c\" = corpus text, \"w\" = wordlist]\n>>> ")
        user_input = user_input.strip().casefold()
        if user_input and user_input in {"c", "w"}:
            if user_input == "c":
                use_corpus = True
            else:
                use_corpus = False
            break
        else:
            print("Invalid user input.")
    print('--------------------------')
    return use_corpus


# a function with a more transparent name, without removing
# "read_corpus_file" below for now (not sure if it's used elsewhere)
def read_word_freq(infilename: Path, casefold=True):
    return read_corpus_file(infilename, casefold)

# rename this function? (we *are* using this function, via "read_word_freq" above)
def read_corpus_file(corpus_path: Path, casefold=True) -> Counter:
    with corpus_path.open() as corpus_file:
        lines = corpus_file.readlines()
    word_frequencies = Counter()

    for line in lines:

        # remove trailing whitespace and see if anything useful is left
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        word, *rest = line.split()

        if casefold:
            word = word.casefold()

        # if additional information (e.g. frequency) is present
        try:
            # if freq is present
            freq = int(rest[0])
        except (IndexError, ValueError):
            # if not, freq default to 1
            freq = 1

        word_frequencies[word] += freq

    return word_frequencies


def proceed_or_not():
    proceed = input("Should the program proceed? [Y/n] ")
    if proceed and not strtobool(proceed):
        # if "proceed" is empty, then false (= program good to go)
        sys.exit("Program terminated by user")
    print('--------------------------')

# TODO: abandoning json_pload and json_pdump
def json_pdump(inputdict, outfile,
               key=lambda x:x, reverse=False,
               asis=False,
               ensure_ascii=False,
               indent=4, separators=(',', ': ')):
    "json pretty dump"

    if asis:
        # don't touch inputdict
        outputdict = inputdict
    else:
        outputdict = OrderedDict(sorted_alphabetized(inputdict.items(),
                                    key=key, reverse=reverse))

    # dumping could be tricky, as keys and values can potentially be of any
    # basic and non-basic data types.
    # So for now we ensure that json.dump can dump outputdict
    # by converting everything to str
    # This entails that we have to be careful when trying to load things back
    # to python in GUI etc...
    outputdict = OrderedDict([(str(k), str(v)) for (k,v) in outputdict.items()])

    json.dump(outputdict, outfile,
              ensure_ascii=ensure_ascii,
              indent=indent, separators=separators)

# TODO: abandoning json_pload and json_pdump
def json_pload(infile):
    '''json pretty load'''
    outdict = json.load(infile)

    try:
        _keys = [eval(k) for k in outdict.keys()]
    except (NameError, SyntaxError):
        convertkeys = False
    else:
        convertkeys = True

    try:
        _values = [eval(v) for v in outdict.values()]
    except (NameError, SyntaxError):
        convertvalues = False
    else:
        convertvalues = True

    if convertkeys and convertvalues:
        return {eval(k):eval(v) for k, v in outdict.items()}
    elif convertkeys:
        return {eval(k):v for k, v in outdict.items()}
    elif convertvalues:
        return {k:eval(v) for k, v in outdict.items()}
    else:
        return {k:v for k, v in outdict.items()}


def changeFilenameSuffix(filename: Path, newsuffix):
    return Path(filename.parent, filename.stem + newsuffix)


def stdout_list(header, *args):
    print(header, flush=True)
    for x in args:
        print(x, flush=True)


def sorted_alphabetized(input_object, key=lambda x: x, reverse=False,
                        subkey=lambda x:x, subreverse=False):
    if not input_object:
        print("Warning: object is empty. Sorting aborted.")
        return

    new_sorted_list = list()
    sorted_list = sorted(input_object, key=key, reverse=reverse)

    for k, group in groupby(sorted_list, key=key): # groupby from itertools

        # must use "list(group)", cannot use just "group"!
        sublist = sorted(list(group), key=subkey, reverse=subreverse)
        # see python 3.4 documentation:
        # https://docs.python.org/3/library/itertools.html#itertools.groupby
        # "The returned group is itself an iterator that shares the underlying
        # iterable with groupby(). Because the source is shared, when the 
        # groupby() object is advanced, the previous group is no longer visible.
        # So, if that data is needed later, it should be stored as a list"

        new_sorted_list.extend(sublist)

    return new_sorted_list


def OutputLargeDict(outfilename, inputdict,
                    key=lambda x:x, summary=True, reverse=False,
                    howmanyperline=10, min_cell_width=0,
                    SignatureKeys=False, SignatureValues=False,
                    sigtransforms=False):

    if not inputdict:
        print("inputdict is empty!")
        return

    # if SignatureKeys is True, each key in inputdict is a tuple of strings
    # if SignatureKeys is False, each key in inputdict is a string

    # if SignatureValues is True, each value in inputdict is a set/list of tuples of strings
    # if SignatureValues is False, each value in inputdict is a set/list of strings

    inputdictSortedList = sorted_alphabetized(inputdict.items(),
                                              key=key, reverse=reverse)

    nItems = len(inputdictSortedList)

    if SignatureKeys:
        input_keys = [SEP_SIG.join(k) for k,v in inputdictSortedList]
    else:
        input_keys = [k for k,v in inputdictSortedList]

    if SignatureValues:
        input_values = [sorted([SEP_SIG.join(x) for x in v])
                        for k,v in inputdictSortedList]
    elif not sigtransforms:
        input_values = [sorted(v) for k,v in inputdictSortedList]
    else:
        # sigtransforms is True
        input_values = [sorted([SEP_SIG.join(sig) + SEP_SIGTRANSFORM + affix
                                for sig, affix in v])
                        for k,v in inputdictSortedList]

    max_key_length = max([len(x) for x in input_keys])

    with outfilename.open('w') as f:
        if summary:
            # print a summary (typically the list of keys with the size of the
            # corresponding value)
            for i in range(nItems):
                print("{} {}".format(str(input_keys[i]).ljust(max_key_length),
                                     len(input_values[i])), file=f)
            print(file=f)

        # for each key, print its value in a nice way
        for i in range(nItems):

            # print key and the size of value
            print("{} {}".format(str(input_keys[i]).ljust(max_key_length),
                                 len(input_values[i])), file=f)

            row = input_values[i]
            output_list = list()
            sublist = list()

            # output_list stores everything to be printed
            # output_list has sublists as elements
            # each sublist has the things to be printed in each output row
            # the size of each sublist is controlled by howmanyperline
            # so overall what's being printed is like a table

            for j, item in enumerate(row, 1):
                sublist.append(item)
                if j % howmanyperline == 0:
                    output_list.append(sublist)
                    sublist = list()

            if sublist:
                output_list.append(sublist)

            # now we're trying to find out what the cell width should be
            # for each column of the output table

            # treat output_list as a matrix-like object, transpose it using the
            # the zip_longest function so that we can easily compute the
            # required cell width for each column (stored in cell_width_list).

            output_list_transposed = zip_longest(*output_list, fillvalue="")

            cell_width_list = [max([len(item) for item in str_list])
                               for str_list in output_list_transposed]

            # if min_cell_width is not zero, we are forcing a particular
            # min_cell_width value to be used
            # we use it if and only if min_cell_width is larger than a column
            # cell width

            if min_cell_width:
                for j in range(len(cell_width_list)):
                    if min_cell_width > cell_width_list[j]:
                        cell_width_list[j] = min_cell_width

            # print the stuff from output_list to the output text file
            for item_list in output_list:
                for j, item in enumerate(item_list):
                    print(str(item).ljust(cell_width_list[j]), end=" ", file=f)
                print(file=f)

            print(file=f)


def is_complex(s):
    """Test if string s is a complex number"""
    try:
        test = complex(s)
    except (ValueError, TypeError):
        return False
    else:
        return True

class LinguisticaJSONEncoder(json.JSONEncoder):
    """We define this custom JSONEncoder subclass to deal with what the standard
    json encoder cannot deal with:

    - set: change it into an array
    - complex number: get the real part only
    See example here: https://docs.python.org/3/library/json.html
    """
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        if (not isinstance(obj, int)) and (not isinstance(obj, float)) and \
            is_complex(obj):
            return obj.real
        return json.JSONEncoder.default(self, obj)


def json_dump(obj, outfile_opened, ensure_ascii=False, indent=4,
        separators=(',', ': '), sort_keys=True, cls=LinguisticaJSONEncoder):
    """json.dump with our preferred parameters
    """
    json.dump(obj, outfile_opened, ensure_ascii=ensure_ascii,
              indent=indent, sort_keys=sort_keys, separators=separators,
              cls=cls)


