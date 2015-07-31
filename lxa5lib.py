#!usr/bin/env python3

from collections import Counter
import sys
import json
from pathlib import Path
from distutils.util import strtobool
from collections import OrderedDict
from pprint import pprint
from itertools import zip_longest

#------------------------------------------------------------------------------#
#    constants
#------------------------------------------------------------------------------#

SEP_SIG = "-"          # separator between affixes in a sig (NULL-s-ed-ing)
SEP_SIGTRANSFORM = "." # separator between sig and affix (NULL-s-ed-ing.ed)

#------------------------------------------------------------------------------#
#    general functions used by various lxa5 components
#------------------------------------------------------------------------------#

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
        if rest:
            freq = int(rest[0])

        # if not, default to 1
        else:
            freq = 1

        word_frequencies[word] += freq

    return word_frequencies

def proceed_or_not():
    proceed = input("Should the program proceed? [Y/n] ")
    if proceed and not strtobool(proceed):
        # if "proceed" is empty, then false (= program good to go)
        sys.exit("Program terminated by user")
    print('--------------------------')


def get_language_corpus_datafolder(_language, _corpus, _datafolder,
                                   configfilename="config.json",
                                   description="", scriptname="<file>"):

    newconfig = False # need to write new config file or not

    print("\n===============================================================\n")
    print(description)
    print()

    print("If this program has parameters (shown above) and if any of them\n"
          "are undesirable, terminate the program now and run the program\n"
          "again by explicitly providing the command line arguments.\n"
          "For details, run \"python3 {} -h\"\n".format(scriptname))

    # -------------------------------------------------------------------------#
    # check current directory and config filename. Print them to stdout

    current_dir = Path.cwd()
    print("Your current directory:\n{}\n".format(current_dir))

    config_path = Path(configfilename)

    if config_path.exists():
        configtext = "(present in the current directory)"
    else:
        configtext = "(NOT present in the current directory)"
        newconfig = True

    print("Configuration filename:\n{} {}\n".format(configfilename, configtext))

    # -------------------------------------------------------------------------#
    # The following 3 chunks of code are meant to determine the values of
    # language, corpus, and datafolder.

    # 1. If user explicitly provides command line arguments for any of
    #   {language, corpus, datafolder},
    #   then the program should use them.

    language, corpus, datafolder = _language, _corpus, _datafolder

    print("\nAccording to your command line arguments --\n"
          "\tLanguage: {}\n"
          "\tCorpus: {}\n"
          "\tDatafolder path "
          "(relative to current directory): {}\n".format(language,
                                                         corpus, datafolder))

    # 2. If any of {language, corpus, datafolder} are None (= not explicitly
    #   given from the user's command line arguments),
    #   then:
    #       if config file is present:
    #           the program attempts to retrieve whichever values
    #           among {language, corpus, datafolder} are needed.

    if language or corpus or datafolder:
        # if true,
        # then at least one of these three arguments is explicitly entered
        # by user, which means we need to write the new config file
        newconfig = True

    if not language or not corpus or not datafolder:
        print("At least one of the three values above is None.\n")

        if config_path.exists():
            print("Because the configuration file {} is present,\n"
                  "the program now attempts to retrieve the missing values\n"
                  "from this configuration file.\n".format(configfilename))

            try:
                with config_path.open() as config_file:
                    config = json.load(config_file)
                    if not language:
                        try:
                            language = config['language']
                        except (KeyError, ValueError):
                            language = None
                    if not corpus:
                        try:
                            corpus = config['corpus']
                        except (KeyError, ValueError):
                            corpus = None
                    if not datafolder:
                        try:
                            datafolder = config['datafolder']
                        except (KeyError, ValueError):
                            datafolder = None

            except (FileNotFoundError, ValueError):
                print("Error in reading the configuration file {}\n"
                      "in the current directory!\n".format(config_path))

    # 3. If any of {language, corpus, datafolder} are still unknown,
    #   then the program asks the user
    #   to provide them using the input() function.

    if not language:
        language = input('Enter language name: ')
        newconfig = True
    if not corpus:
        corpus = input('Enter corpus filename: ')
        newconfig = True
    if not datafolder:
        datafolder = input('Enter datafolder relative path: ')
        newconfig = True

    # -------------------------------------------------------------------------#
    # write the configuration file

    if newconfig:
        config = {'language': language,
                  'corpus': corpus,
                  'datafolder': datafolder}
        with config_path.open('w') as config_file:
            json.dump(config, config_file)
            print('New configuration file \"{}\" written.'.format(config_path))

    # -------------------------------------------------------------------------#
    # print to stdout the latest info for language, corpus, and datafolder

    print("\nNow the program has the following --")

    print("\tLanguage: {}".format(language))
    print("\tCorpus: {}".format(corpus))
    print("\tDatafolder path "
          "(relative to current directory): {}".format(datafolder))

    testPath = Path(datafolder, language, corpus)

    # -------------------------------------------------------------------------#
    # print to stdout to show user what corpus file is being expected
    # ask user if the program should proceed or not

    print("\nBased on these three values, the program is looking for the\n"
          "following corpus file relative to the current directory:\n"
          "{}".format(testPath))

    print("\nIf any of {language, corpus, datafolder} or the expected corpus\n"
          "file is undesirable, terminate the program now and run again by\n"
          "explicitly providing the command line arguments.\n")

    proceed_or_not()

    # -------------------------------------------------------------------------#
    # make sure the expected corpus file exists. If not, exit the program.

    if not testPath.exists():
        sys.exit('\nCorpus file "{}" does not exist.\n'
                 'Check file paths and names.'.format(testPath))
    # -------------------------------------------------------------------------#

    print('--------------------------')

    return language, corpus, datafolder


def load_config_for_command_line_help(configfilename="config.json"):

    config_path = Path(configfilename)
    try:
        with config_path.open() as config_file:
            config = json.load(config_file)
        language = config['language']
        corpus = config['corpus']
        datafolder = config['datafolder']

        configtext = "The configuration file {} is present: ".format(configfilename) + \
                     "[language: {}] ".format(language) + \
                     "[corpus file: {}] ".format(corpus) + \
                     "[data folder relative to " + \
                     "current directory: \"{}\"]\n".format(datafolder)

    except (FileNotFoundError, KeyError, ValueError):
        language = None
        corpus = None
        datafolder = None

        configtext = "No valid configuration file located."

    return language, corpus, datafolder, configtext


# load_config() not used by get_language_corpus_datafolder() now
# but don't delete this function yet
# Anton may still be using it -- check with him
def load_config(language, corpus, datafolder, filename='config.json',
                writenew=True):
    config_path = Path(filename)
    if not language or not corpus or not datafolder:
        try:
            # see if it's there
            with config_path.open() as config_file:
                config = json.load(config_file)
            language = config['language']
            corpus = config['corpus']
            datafolder = config['datafolder']
            writenew = False
        except (FileNotFoundError, KeyError, ValueError):
            language = input('enter language name: ')
            corpus = input('enter corpus filename: ')
            datafolder = input('enter data path: ')

    if writenew:
        config = {'language': language,
                  'corpus': corpus,
                  'datafolder': datafolder}
        with config_path.open('w') as config_file:
            json.dump(config, config_file)

    return language, corpus, datafolder


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


def changeFilenameSuffix(filename: Path, newsuffix):
    return Path(filename.parent, filename.stem + newsuffix)


def stdout_list(header, *args):
    print(header, flush=True)
    for x in args:
        print(x, flush=True)


def sorted_alphabetized(input_object, key=lambda x: x, reverse=False):
    sorted_list = sorted(input_object, key=key, reverse=reverse)
    sortkey_list = [key(item) for item in sorted_list]

    new_sorted_list = list()

    current_sortkey = sortkey_list[0]
    item_sublist = [sorted_list[0]]

    for item, sortkey in zip(sorted_list[1:], sortkey_list[1:]):
        if sortkey == current_sortkey:
            item_sublist.append(item)
        else:
            new_sorted_list += sorted(item_sublist)

            item_sublist = list()
            current_sortkey = sortkey

    if item_sublist:
        new_sorted_list += sorted(item_sublist)

    return new_sorted_list


def OutputLargeDict(outfilename, inputdict,
                    key=lambda x:x, summary=True, reverse=False,
                    howmanyperline=10, min_cell_width=0,
                    SignatureKeys=False, SignatureValues=False,
                    sigtransforms=False):

    # if SignatureKeys is True, each key in inputdict is a tuple of strings
    # if SignatureKeys is False, each key in inputdict is a string

    # if SignatureValues is True, each value in inputdict is a set/list of tuples of strings
    # if SignatureValues is False, each value in inputdict is a set/list of strings

    inputdictSortedList = sorted_alphabetized(inputdict.items(),
                                              key=key, reverse=reverse)

    nItems = len(inputdictSortedList)

    if SignatureKeys:
        input_keys = ['-'.join(k) for k,v in inputdictSortedList]
    else:
        input_keys = [k for k,v in inputdictSortedList]

    if SignatureValues:
        input_values = [sorted(['-'.join(x) for x in v])
                        for k,v in inputdictSortedList]
    elif not sigtransforms:
        input_values = [sorted(v) for k,v in inputdictSortedList]
    else:
        # sigtransforms is True
        input_values = [sorted(['-'.join(sig) + SEP_SIGTRANSFORM + affix for sig, affix in v])
                        for k,v in inputdictSortedList]

    max_key_length = max([len(x) for x in input_keys])

    with outfilename.open('w') as f:
        if summary:
            for i in range(nItems):
                print("{} {}".format(str(input_keys[i]).ljust(max_key_length),
                                     len(input_values[i])), file=f)
            print(file=f)

        for i in range(nItems):
            print("{} {}".format(str(input_keys[i]).ljust(max_key_length),
                                 len(input_values[i])), file=f)

            row = input_values[i]
            output_list = list()
            sublist = list()

            for j, item in enumerate(row, 1):
                sublist.append(item)
                if j % howmanyperline == 0:
                    output_list.append(sublist)
                    sublist = list()

            if sublist:
                output_list.append(sublist)

            output_list_transposed = zip_longest(*output_list, fillvalue="")

            cell_width_list = [max([len(item) for item in str_list])
                               for str_list in output_list_transposed]

            if min_cell_width:
                for j in range(len(cell_width_list)):
                    if min_cell_width > cell_width_list[j]:
                        cell_width_list[j] = min_cell_width

            for item_list in output_list:
                for j, item in enumerate(item_list):
                    print(str(item).ljust(cell_width_list[j]), end=" ", file=f)
                print(file=f)

            print(file=f)

"""John created a slight variant of preceding function, but for WordToSigs;
left the old one untouched since I didn't know what other functions called it"""

# currently not used
def OutputLargeDict2(outfilename, inputdict, SignatureFlag=True):
    if SignatureFlag:
        punctuation = SEP_SIG
    else:
        punctuation = ""

    items_sorted_list = sorted(inputdict.keys())
    MaxStemLength = 0
    MaxLength = 0
    MaxColumnWidth = {}

    # Find out the maximum number of sigs for each stem
    for stem in items_sorted_list:

        if len(inputdict[stem]) > MaxLength:
            MaxLength = len(inputdict[stem])
        if len(stem) > MaxStemLength:
            MaxStemLength = len(stem)

    MaxStemLength += 1

    # Create a dict for each column's width
    for length in range(MaxLength + 1):
        MaxColumnWidth[length] = 0

    # a list of lines to be written to a file later
    these_lines = []

    # Find the longest entry in each column
    for stem in items_sorted_list:
        these_items = inputdict[stem]
        for signo in range(len(these_items)):
            this_item = these_items[signo]

            if SignatureFlag:
                if len(punctuation.join(this_item)) > MaxColumnWidth[signo]:
                    MaxColumnWidth[signo] = len(punctuation.join(this_item))
            else:
                if len(this_item) > MaxColumnWidth[signo]:
                    MaxColumnWidth[signo] = len(punctuation.join(this_item))

        # find the longest entry in each column

        for stem in items_sorted_list:
            these_items = inputdict[stem]

            this_line = []
            this_line.append(stem + " " * (MaxStemLength - len(stem)))

            for signo in range(len(these_items)):
                this_item = these_items[signo]

                if SignatureFlag:
                    this_line.append(punctuation.join(this_item)
                                 + " " * (MaxColumnWidth[signo] + 1 - len(this_item)))
                else:
                    this_line.append(this_item
                                     + " " * (MaxColumnWidth[signo] + 1 - len(this_item)))

            these_lines.append(''.join(this_line))

    with outfilename.open('w') as file:
        for this_line in these_lines:
            print(this_line, file=file)

