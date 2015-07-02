#!usr/bin/env python3

from collections import Counter
import argparse
from pathlib import Path

import ngrams
from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix, stdout_list)

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

    outfilenamePhones_json = changeFilenameSuffix(outfilenamePhones, '.json')
    with outfilenamePhones_json.open('w') as f:
        json_pdump(phoneDict, f, sort_function=lambda x:x[1], reverse=True)

    outfilenameBiphones_json = changeFilenameSuffix(outfilenameBiphones, '.json')
    with outfilenameBiphones_json.open('w') as f:
        json_pdump(biphoneDict, f, sort_function=lambda x:x[1], reverse=True)

    outfilenameTriphones_json = changeFilenameSuffix(outfilenameTriphones, '.json')
    with outfilenameTriphones_json.open('w') as f:
        json_pdump(triphoneDict, f, sort_function=lambda x:x[1], reverse=True)

    print('phone, biphone and triphone files ready')

    stdout_list("Output files:",
        outfilenamePhones, outfilenameBiphones, outfilenameTriphones,
        outfilenamePhones_json, outfilenameBiphones_json, outfilenameTriphones_json)

if __name__ == "__main__":

    args = makeArgParser().parse_args()

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                                   args.corpus, args.datafolder)

    main(language, corpus, datafolder)

