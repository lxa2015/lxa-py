#!usr/bin/env python3

from collections import Counter
import argparse
from pathlib import Path

import ngrams
from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix, stdout_list,
                     load_config_for_command_line_help,
                     determine_use_corpus, get_wordlist_path_corpus_stem,
                     sorted_alphabetized)

#------------------------------------------------------------------------------#
#
#    This program creates a phone file, a biphone file, and a triphone file.
#
#    Input is a wordlist.
#
#    Jackson Lee 2015-
#
#------------------------------------------------------------------------------#

def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="Extracting phone/letter ngrams from a wordlist; also other"
                    "phonology-related stuff\n\n{}"
                    .format(configtext),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--config", help="configuration filename",
                        type=str, default=configfilename)

    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)

    parser.add_argument("--maxwordtokens", help="maximum number of word tokens;"
                        " if this is zero, then the program counts "
                        "all word tokens in the corpus",
                        type=int, default=0)
    return parser


def main(language, corpus, datafolder,
         maxwordtokens=0, use_corpus=True):

    corpusName = Path(corpus).stem

    outfolder = Path(datafolder, language, "phon")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    infilename, corpusName = get_wordlist_path_corpus_stem(language, corpus,
                                         datafolder, maxwordtokens, use_corpus)

    if not infilename.exists():
        if use_corpus:
            if maxwordtokens:
                warning = " ({} tokens)".format(maxwordtokens)
            else:
                warning = ""
            print("\nWordlist for {}{} not found.\n"
                  "ngrams.py is now run.\n".format(corpus, warning))
            ngrams.main(language, corpus, datafolder, maxwordtokens)
        else:
            sys.exit("\nThe specified wordlist ""\n"
                     "is not found.".format(infilename))

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

            line = line.strip().casefold()

            phones, *rest = line.split()

            try:
                freq = int(rest[0])
            except (ValueError, IndexError):
                freq = 1

            phones = "#{}#".format(phones) # add word boundaries
            lenPhones = len(phones)

            for i in range(lenPhones-2):

                phone1 = phones[i]
                phone2 = phones[i+1]
                phone3 = phones[i+2]

                phoneDict[phone3] += freq

                if i == 0:
                    phoneDict[phone1] += freq
                    phoneDict[phone2] += freq
                    biphone = phone1 + sep + phone2
                    biphoneDict[biphone] += freq

                biphone = phone2 + sep + phone3
                triphone = phone1 + sep + phone2 + sep + phone3

                triphoneDict[triphone] += freq
                biphoneDict[biphone] += freq

    print("\nCompleted counting phones, biphones, and triphones.")

    intro_string = "# data source: {}".format(str(infilename))

    phonesSorted = sorted_alphabetized(phoneDict.items(),
                                       key=lambda x: x[1], reverse=True)

    biphonesSorted = sorted_alphabetized(biphoneDict.items(),
                                         key=lambda x: x[1], reverse=True)

    triphonesSorted = sorted_alphabetized(triphoneDict.items(),
                                          key=lambda x: x[1], reverse=True)

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

    outfilenamePhones_json = changeFilenameSuffix(outfilenamePhones, '.json')
    with outfilenamePhones_json.open('w') as f:
        json_pdump(phoneDict, f, key=lambda x:x[1], reverse=True)

    outfilenameBiphones_json = changeFilenameSuffix(outfilenameBiphones, '.json')
    with outfilenameBiphones_json.open('w') as f:
        json_pdump(biphoneDict, f, key=lambda x:x[1], reverse=True)

    outfilenameTriphones_json = changeFilenameSuffix(outfilenameTriphones, '.json')
    with outfilenameTriphones_json.open('w') as f:
        json_pdump(triphoneDict, f, key=lambda x:x[1], reverse=True)

    print('phone, biphone and triphone files ready')

    stdout_list("Output files:",
        outfilenamePhones, outfilenameBiphones, outfilenameTriphones,
        outfilenamePhones_json, outfilenameBiphones_json, outfilenameTriphones_json)

if __name__ == "__main__":

    args = makeArgParser().parse_args()
    maxwordtokens = args.maxwordtokens

    description="You are running {}.\n".format(__file__) + \
                "This program works on the phonology-related tasks.\n" + \
                "maxwordtokens = {} (zero means all word tokens)".format(maxwordtokens)

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    use_corpus = determine_use_corpus()

    main(language, corpus, datafolder,
         maxwordtokens, use_corpus)


