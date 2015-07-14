#!usr/bin/env python3

import sys
import json
from pathlib import Path
from distutils.util import strtobool
from collections import OrderedDict
from pprint import pprint


#------------------------------------------------------------------------------#
#
#    general functions used by various lxa5 components
#
#------------------------------------------------------------------------------#


def proceed_or_not():
    proceed = input("Should the program proceed? [Y/n] ")
    if proceed and not strtobool(proceed):
        # if "proceed" is empty, then false (= program good to go)
        sys.exit("Program terminated by user")
    print('--------------------------')


def get_language_corpus_datafolder(_language, _corpus, _datafolder,
                                   configfilename="config.json",
                                   description=""):

    newconfig = False # need to write new config file or not

    print("\n===============================================================\n")
    print(description)
    print()

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

    proceed_or_not()

    # -------------------------------------------------------------------------#

    # -------------------------------------------------------------------------#
    # The following 3 chunks of code are meant to determine the values of
    # language, corpus, and datafolder.

    # 1. If user explicitly provides command line arguments for any of
    #   {language, corpus, datafolder},
    #   then the program should use them.

    language, corpus, datafolder = _language, _corpus, _datafolder

    print("\nAccording to your command line arguments --\n"
          "Language: {}\n"
          "Corpus: {}\n"
          "Datafolder path "
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

                    print("{} contains the following "
                          "key-value pairs:".format(configfilename))
                    pprint(config)
                    print()

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

    # -------------------------------------------------------------------------#
    # print to stdout the latest info for language, corpus, and datafolder

    print("\nNow the program has the following --")

    print("Language: {}".format(language))
    print("Corpus: {}".format(corpus))
    print("Datafolder path "
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
               sort_function=lambda x:x, reverse=False,
               ensure_ascii=False,
               indent=4, separators=(',', ': ')):
    "json pretty dump"

    if not hasattr(sort_function, "__call__"):
        raise Exception("invalid sort function")

    outputdict = OrderedDict(sorted(inputdict.items(),
                                    key=sort_function, reverse=reverse))

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


