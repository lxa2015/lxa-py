#!usr/bin/env python3

import sys
import json
from pathlib import Path
from distutils.util import strtobool
from collections import OrderedDict


#------------------------------------------------------------------------------#
#
#    general functions used by various lxa5 components
#
#------------------------------------------------------------------------------#


def get_language_corpus_datafolder(_language, _corpus, _datafolder,
                                   filename="config.json"):
    language, corpus, datafolder = load_config(_language, _corpus, _datafolder,
                                               filename)

    print("language: {}".format(language))
    print("corpus file: {}".format(corpus))
    print("datafolder: {}".format(datafolder))
    proceed = input("proceed? [Y/n] ")
    if proceed and not strtobool(proceed):
        sys.exit() # if "proceed" is empty, then false (= good to go)

    testPath = Path(datafolder, language, corpus)
    if not testPath.exists():
        sys.exit('Corpus file "{}" does not exist. '
                 'Check file paths and names.'.format(str(testPath) ))

    return language, corpus, datafolder


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


