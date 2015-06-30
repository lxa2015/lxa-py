#!usr/bin/env python3

import sys
from collections import Counter
import argparse
import json
from pathlib import Path
from distutils.util import strtobool

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

def makeArgParser():
    parser = argparse.ArgumentParser(
        description="This program extracts ngrams from a corpus.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)
    parser.add_argument("--maxwordtokens", help="maximum number of word tokens",
                        type=int, default=0)
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


def main(language, corpus, datafolder, maxwordtokens=0):

    infilename = Path(datafolder, language, corpus)
    outfolder = Path(datafolder, language, "ngrams")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    if maxwordtokens:
        corpusName = Path(corpus).stem + "-" + str(maxwordtokens)
    else:
        corpusName = Path(corpus).stem

    outfilenameWords = Path(outfolder, corpusName + "_words.txt")
    outfilenameBigrams = Path(outfolder, corpusName + "_bigrams.txt")
    outfilenameTrigrams = Path(outfolder, corpusName + "_trigrams.txt")

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
            line = line.replace(".", " .")
            line = line.replace(",", " ,")
            line = line.replace(";", " ;")
            line = line.replace("!", " !")
            line = line.replace("?", " ?")
            line = line.replace(":", " :")
            line = line.replace(")", " )")
            line = line.replace("(", "( ")

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

    print('wordlist, bigram and trigram files ready')


if __name__ == "__main__":

    # TODO: we may need to move all config-related code to a separate
    #   module, as there will be other parameters to be brought into the picture
    #   and we'd like to make things easier to manage for the overal architecture
    #   as well as for both GUI and non-GUI usage 

    args = makeArgParser().parse_args()

    maxwordtokens = args.maxwordtokens

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

    main(language, corpus, datafolder, maxwordtokens)

