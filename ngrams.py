#!usr/bin/env python3

from collections import Counter
import argparse
from pathlib import Path

from lxa5lib import (get_language_corpus_datafolder, stdout_list,
                     load_config_for_command_line_help)

#------------------------------------------------------------------------------#
#
#    This program creates a trigram file, bigram file, and a word list.
#
#    Input is a corpus text.
#
#    John Goldsmith and Wang Xiuli 2012
#    Jackson Lee 2014-
#
#------------------------------------------------------------------------------#

def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="This program extracts ngrams from a corpus.\n\n{}"
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
                        " if this is zero, then the program reads "
                        "all word tokens in the corpus",
                        type=int, default=0)
    return parser


def main(language, corpus, datafolder, maxwordtokens=0):

    infilename = Path(datafolder, language, corpus)
    outfolder = Path(datafolder, language, "ngrams")
    outfolderDx1 = Path(datafolder, language, "dx1")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    if not outfolderDx1.exists():
        outfolderDx1.mkdir(parents=True)

    if maxwordtokens:
        corpusName = Path(corpus).stem + "_{}-tokens".format(maxwordtokens)
    else:
        corpusName = Path(corpus).stem

    outfilenameWords = Path(outfolder, corpusName + "_words.txt")
    outfilenameBigrams = Path(outfolder, corpusName + "_bigrams.txt")
    outfilenameTrigrams = Path(outfolder, corpusName + "_trigrams.txt")
    outfilenameDx1 = Path(outfolderDx1, corpusName + ".dx1")

    wordDict = Counter()
    trigramDict = Counter()
    bigramDict = Counter()
    sep = "\t"
    corpusCurrentSize = 0 # running word token count

    print('Reading the corpus file now...')

    with infilename.open() as f:
        lines = f.readlines()

        for line in lines:
            if not line:
                continue

            # to ensure that there are no unwanted end-of-line characters
            line = line.lower().replace('\n', '').replace('\r', '')

            # TODO: modify/combine these with "scrubbing", cf. Alchemist and Lxa4
            line = line.replace(".", " . ")
            line = line.replace(",", " , ")
            line = line.replace(";", " ; ")
            line = line.replace("!", " ! ")
            line = line.replace("?", " ? ")
            line = line.replace(":", " : ")
            line = line.replace(")", " ) ")
            line = line.replace("(", " ( ")

            words = line.split()
            lenWords = len(words)

            corpusCurrentSize += lenWords

            for i in range(lenWords-2):

                word1 = words[i]
                word2 = words[i+1]
                word3 = words[i+2]

                wordDict[word1] += 1
                wordDict[word2] += 1
                wordDict[word3] += 1

                if i == 0:
                    bigram = word1 + sep + word2
                    bigramDict[bigram] += 1

                bigram = word2 + sep + word3
                trigram = word1 + sep + word2 + sep + word3

                trigramDict[trigram] += 1
                bigramDict[bigram] += 1

            if maxwordtokens and corpusCurrentSize > maxwordtokens:
                break

    print("\nCompleted counting words, bigrams, and trigrams.")
    print("Token count: {}".format(corpusCurrentSize))

    intro_string = "# data source: {}\n# token count: {}".format(str(infilename),
                                                                   corpusCurrentSize)

    wordsSorted = [x for x in wordDict.items()]
    wordsSorted.sort(key=lambda x: x[1], reverse=True)

    bigramsSorted = [x for x in bigramDict.items()]
    bigramsSorted.sort(key=lambda x:x[1], reverse=True)

    trigramsSorted = [x for x in trigramDict.items()]
    trigramsSorted.sort(key=lambda x:x[1], reverse=True)

    with outfilenameWords.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(wordsSorted)), file=f)
        for (word, freq) in wordsSorted:
            print(word + sep + str(freq), file=f)

    with outfilenameBigrams.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(bigramsSorted)), file=f)
        for (bigram, freq) in bigramsSorted:
            print(bigram + sep +  str(freq), file=f)

    with outfilenameTrigrams.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(trigramsSorted)), file=f)
        for (trigram, freq) in trigramsSorted:
            print(trigram + sep + str(freq), file=f)

    with outfilenameDx1.open('w') as f:
        for (word, freq) in wordsSorted:
            print(word, freq, ' '.join(word), file=f)

    print('wordlist, bigram and trigram files ready')
    print('dx1 file ready')

    stdout_list("Output files:", outfilenameWords,
                                 outfilenameBigrams,
                                 outfilenameTrigrams,
                                 outfilenameDx1)


if __name__ == "__main__":

    args = makeArgParser().parse_args()

    maxwordtokens = args.maxwordtokens

    description="You are running {}.\n".format(__file__) + \
                "This program extracts word n-grams.\n" + \
                "maxwordtokens = {} (zero means all word tokens)".format(maxwordtokens)

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    main(language, corpus, datafolder, maxwordtokens)

