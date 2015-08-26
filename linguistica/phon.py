#!usr/bin/env python3

from collections import Counter
import argparse
from pathlib import Path

from . import ngram
from .lxa5lib import (json_dump, changeFilenameSuffix, stdout_list,
                     get_wordlist_path_corpus_stem, sorted_alphabetized)

#------------------------------------------------------------------------------#
#
#    This program creates a phone file, a biphone file, and a triphone file.
#
#    Input is a wordlist.
#
#    Jackson Lee 2015-
#
#------------------------------------------------------------------------------#


def main(language=None, corpus=None, datafolder=None, filename=None,
         maxwordtokens=0, use_corpus=True):

    print("\n*****************************************************\n"
          "Running the phon component of Linguistica now...\n", flush=True)

    infilename, corpusName = get_wordlist_path_corpus_stem(language, corpus,
                                datafolder, filename, maxwordtokens, use_corpus)

    if not infilename.exists():
        if use_corpus:
            if maxwordtokens:
                warning = " ({} tokens)".format(maxwordtokens)
            else:
                warning = ""
            print("\nWordlist for {}{} not found.\nThe ngram component "
                  "is now run.\n".format(corpus, warning), flush=True)
            ngram.main(language=language, corpus=corpus,
                        datafolder=datafolder, filename=filename,
                        maxwordtokens=maxwordtokens)
        else:
            sys.exit("\nThe specified wordlist ""\n"
                     "is not found.".format(infilename))

    if filename:
        outfolder = Path(Path(filename).parent, "phon")
    else:
        outfolder = Path(datafolder, language, 'phon')

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    outfilenamePhones = Path(outfolder, corpusName + "_phones.txt")
    outfilenameBiphones = Path(outfolder, corpusName + "_biphones.txt")
    outfilenameTriphones = Path(outfolder, corpusName + "_triphones.txt")

    phoneDict = Counter()
    triphoneDict = Counter()
    biphoneDict = Counter()
    sep = "\t"

    print('Reading the wordlist file now...', flush=True)

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

    print("\nCompleted counting phones, biphones, and triphones.", flush=True)

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
        json_dump(phoneDict, f)

    outfilenameBiphones_json = changeFilenameSuffix(outfilenameBiphones, '.json')
    with outfilenameBiphones_json.open('w') as f:
        json_dump(biphoneDict, f)

    outfilenameTriphones_json = changeFilenameSuffix(outfilenameTriphones, '.json')
    with outfilenameTriphones_json.open('w') as f:
        json_dump(triphoneDict, f)

    print('phone, biphone and triphone files ready', flush=True)

    stdout_list("Output files:",
        outfilenamePhones, outfilenameBiphones, outfilenameTriphones,
        outfilenamePhones_json, outfilenameBiphones_json, outfilenameTriphones_json)


