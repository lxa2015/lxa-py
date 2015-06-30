#!usr/bin/env python3

import sys
from collections import Counter
import argparse
import json
from pathlib import Path
from distutils.util import strtobool
from collections import OrderedDict

import ngrams

#------------------------------------------------------------------------------#
#
#    This program creates a phone file, a biphone file, and a triphone file.
#
#    Input is a wordlist.
#
#    Jackson Lee 2015-
#
#------------------------------------------------------------------------------#

def makeArgParser():
    parser = argparse.ArgumentParser(
        description="Extracting phone/letter ngrams from a wordlist.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)
    return parser


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
        except (FileNotFoundError, KeyError):
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
               sort="key", reverse=False,
               indent=4, separators=(',', ': ')):
    """json pretty dump
       either sort_keys or sort_values, but not both, must be True"""

    if sort.casefold() == "key":
        if not reverse:
            json.dump(inputdict, outfile,
                      sort_keys=True, indent=indent, separators=separators)

        else:
            outputdict = OrderedDict(sorted(inputdict.items(),
                                            key=lambda t: t[0], reverse=True))
            json.dump(outputdict, outfile,
                      indent=indent, separators=separators)

    elif sort.casefold() == "value":
        if not reverse:
            outputdict = OrderedDict(sorted(inputdict.items(),
                                            key=lambda t: t[1]))
            json.dump(outputdict, outfile,
                      indent=indent, separators=separators)

        else:
            outputdict = OrderedDict(sorted(inputdict.items(),
                                            key=lambda t: t[1], reverse=True))
            json.dump(outputdict, outfile,
                      indent=indent, separators=separators)

    else:
        raise Exception("invalid sort argument "
                        "(either key or value): {}".format(sort))

def changeFilenameSuffix(filename: Path, newsuffix):
    return Path(filename.parent, filename.stem + newsuffix)


def main(language, corpus, datafolder):

    corpusName = Path(corpus).stem

    outfolder = Path(datafolder, language, "phon")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    infilename = Path(datafolder, language, "ngrams", corpusName + "_words.txt")

    if not infilename.exists():
        ngrams.main(language, corpus, datafolder)

    outfilenamePhones = Path(outfolder, corpusName + "_phones.txt")
    outfilenameBiphones = Path(outfolder, corpusName + "_biphones.txt")
    outfilenameTriphones = Path(outfolder, corpusName + "_triphones.txt")

    phoneDict = Counter()
    triphoneDict = Counter()
    biphoneDict = Counter()
    sep = "\t"

    print('Reading the wordlist file now...')

    with infilename.open() as f:
        lines = f.readlines()

        for line in lines:
            if not line or line.startswith("#"):
                continue

            # to ensure that there are no unwanted end-of-line characters
            line = line.lower().replace('\n', '').replace('\r', '')

            phones, freq = line.split()
            freq = int(freq)
            phones = "#{}#".format(phones) # add word boundaries
            lenPhones = len(phones)

            for i in range(lenPhones-2):

                phone1 = phones[i]
                phone2 = phones[i+1]
                phone3 = phones[i+2]

                phoneDict[phone1] += freq
                phoneDict[phone2] += freq
                phoneDict[phone3] += freq

                if i == 0:
                    biphone = phone1 + sep + phone2
                    biphoneDict[biphone] += freq

                biphone = phone2 + sep + phone3
                triphone = phone1 + sep + phone2 + sep + phone3

                triphoneDict[triphone] += freq
                biphoneDict[biphone] += freq

    print("\nCompleted counting phones, biphones, and triphones.")

    intro_string = "# data source: {}".format(str(infilename))

    phonesSorted = [x for x in phoneDict.items()]
    phonesSorted.sort(key=lambda x: x[1], reverse=True)

    biphonesSorted = [x for x in biphoneDict.items()]
    biphonesSorted.sort(key=lambda x:x[1], reverse=True)

    triphonesSorted = [x for x in triphoneDict.items()]
    triphonesSorted.sort(key=lambda x:x[1], reverse=True)

    #--------------------------------------------------------------------------#
    # generate .txt output files
    #--------------------------------------------------------------------------#

    with outfilenamePhones.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(phonesSorted)), file=f)
        print("# token count: {}".format(str(sum(phoneDict.values()))), file=f)
        for (phone, freq) in phonesSorted:
            print(phone + sep + str(freq), file=f)

    with outfilenameBiphones.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(biphonesSorted)), file=f)
        print("# token count: {}".format(str(sum(biphoneDict.values()))),
                                                                        file=f)
        for (biphone, freq) in biphonesSorted:
            print(biphone + sep +  str(freq), file=f)

    with outfilenameTriphones.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(triphonesSorted)), file=f)
        print("# token count: {}".format(str(sum(triphoneDict.values()))),
                                                                        file=f)
        for (triphone, freq) in triphonesSorted:
            print(triphone + sep + str(freq), file=f)

    #--------------------------------------------------------------------------#
    # generate .json output files
    #--------------------------------------------------------------------------#

    with changeFilenameSuffix(outfilenamePhones, '.json').open('w') as f:
        json_pdump(phoneDict, f, sort="value", reverse=True)

    with changeFilenameSuffix(outfilenameBiphones, '.json').open('w') as f:
        json_pdump(biphoneDict, f, sort="value", reverse=True)

    with changeFilenameSuffix(outfilenameTriphones, '.json').open('w') as f:
        json_pdump(triphoneDict, f, sort="value", reverse=True)

    print('phone, biphone and triphone files ready')


if __name__ == "__main__":

    # TODO: we may need to move all config-related code to a separate
    #   module, as there will be other parameters to be brought into the picture
    #   and we'd like to make things easier to manage for the overal architecture
    #   as well as for both GUI and non-GUI usage 

    args = makeArgParser().parse_args()

    language, corpus, datafolder = load_config(args.language,
                                               args.corpus, args.datafolder)

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

    main(language, corpus, datafolder)

