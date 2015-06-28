#!usr/bin/env python3

# This program creates a left-to-right trie and a right-to-left trie,
# as well as both successors and predecessors.
#
# John Goldsmith 2015
# Jackson Lee 2015

import sys
import argparse
import json
from pathlib import Path

import ngrams


def makeArgParser():
    parser = argparse.ArgumentParser(
        description="If neither config.json nor {language, corpus, datafolder} "
                    "arguments are found, user inputs are prompted.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)
    parser.add_argument("--minstem", help="Minimum stem length",
                        type=int, default=4)
    parser.add_argument("--minaffix", help="Minimum affix length",
                        type=int, default=1)
    parser.add_argument("--minsize",  help="Minimum size of "
                                           "successors/predecessors for output",
                        type=int, default=3)
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


def findBreaksInWords(wordlist, MinimumStemLength):
    FoundPrefixes = set()

    breaks = dict()
    for i in range(len(wordlist)):
        breaks[i] = set()

    previousword = wordlist[0]

    for i in range(1, len(wordlist)):
        thisword = wordlist[i]
        m = lengthofcommonprefix(previousword, thisword)
            
        if m < MinimumStemLength:
            previousword = thisword
            continue

        commonprefix = thisword[ : m]

        if commonprefix in FoundPrefixes:
            previousword = thisword
            continue

        for j in range(i-1, -1, -1):
            if wordlist[j].startswith(commonprefix):
                breaks[j].add(m)
            else:
                break
        for j in range(i, len(wordlist)):
            if wordlist[j].startswith(commonprefix):
                breaks[j].add(m)
            else:
                break

        FoundPrefixes.add(commonprefix)
        previousword = thisword

    return breaks


def BreakUpEachWord(wordlist, breakListDict):
    WordsBroken = dict()

    for i, thisword in enumerate(wordlist):
        WordsBroken[i] = list()
        breakList = sorted(breakListDict[i])

        if not breakList:
            WordsBroken[i].append(thisword)
        else:
            thispiece = ""
            for x in range(len(thisword)):
                thispiece += thisword[x]
                if x+1 in breakList:
                    WordsBroken[i].append(thispiece)
                    thispiece = ""
            if thispiece:
                WordsBroken[i].append(thispiece)

    return WordsBroken


def GetSuccessors(wordlist, WordsBroken):
    successors = dict()
    for i, thisword in enumerate(wordlist):
        wordbeginning = ""
        thiswordparsed = WordsBroken[i]
        thiswordnumberofpieces = len(thiswordparsed)

        if not thiswordparsed:
            successors[thisword] = set()
            successors[thisword].add("NULL")
            continue
        wordbeginning = thiswordparsed[0]

        if wordbeginning not in successors:
            successors[wordbeginning] = set()

        for j in range(1, thiswordnumberofpieces):
            newpiece = thiswordparsed[j]
            if wordbeginning not in successors:
                successors[wordbeginning] = set()
            successors[wordbeginning].add(newpiece) 
            wordbeginning += newpiece

        if wordbeginning not in successors: #whole word, now
            successors[wordbeginning] = set()

        successors[wordbeginning].add("NULL")
    return successors


def OutputSuccessors(outfilename, successors, SF_threshold, reverse=False):

    if reverse:
        #  we are dealing with precedessors here, not successors

        successors_new = dict()
        for stem, affixSet in successors.items():
            successors_new[stem[::-1]] = set([x[::-1] for x in affixSet])
        successors = successors_new

    stemlist =  sorted(successors)

    with outfilename.open("w") as f:
        for word in stemlist:
            SF_size = len(successors[word])

            if SF_size < SF_threshold:
                continue

            print(word + "\t" + str(SF_size) + "\t" + \
                  "\t".join(sorted(successors[word])), file=f)

def OutputTrie(outfile, WordsBroken, reverse=False):

    if reverse:
        # dealing with predecessors, not successors
        WordsBroken_new = dict()
        for i, BrokenWord in WordsBroken.items():
            WordsBroken_new[i] = [x[::-1] for x in BrokenWord][::-1]
        WordsBroken = WordsBroken_new

    with outfile.open("w") as f:
        for i in range(len(WordsBroken)):
            for j in range(len(WordsBroken[i])):
                thispiece = WordsBroken[i][j]
                print(thispiece, file=f, end="\t")
            print(file=f)


def lengthofcommonprefix(s1, s2):
    # ensure that s1 is not longer than s2
    length = len(s1)
    if length > len(s2):
        lengthofcommonprefix(s2, s1)

    for i in range(length):
        if s1[i] != s2[i]:
            return i
    return length


def main(language, corpus, datafolder,
         MinimumStemLength, MinimumAffixLength, SF_threshold):

    corpusName = Path(corpus).stem

    outfolder = Path(datafolder, language, "tries")
    infolder = Path(datafolder, language, "ngrams")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    infilename = Path(infolder, corpusName + "_words.txt")

    if not infilename.exists():
        ngrams.main(language, corpus, datafolder)

    outfile_SF_name = Path(outfolder, corpusName + "_SF.txt")
    outfile_trieLtoR_name = Path(outfolder, corpusName + "_trieLtoR.txt")
     
    outfile_trieRtoL_name = Path(outfolder, corpusName + "_trieRtoL.txt")
    outfile_PF_name = Path(outfolder, corpusName + "_PF.txt")

    #--------------------------------------------------------------------##
    #        read wordlist
    #--------------------------------------------------------------------##

    wordlist = list()
    with infilename.open() as f:

        filelines= f.readlines()

        for line in filelines:
            if (not line) or line[0] == "#":
                continue
            pieces = line.split()
            wordlist.append(pieces[0])

    wordlist.sort()
    reversedwordlist = sorted([x[::-1] for x in wordlist])

    #--------------------------------------------------------------------##
    #        Find breaks in words (left-to-right and right-to-left)
    #--------------------------------------------------------------------##

    breaks_LtoR = findBreaksInWords(wordlist, MinimumStemLength)
    breaks_RtoL = findBreaksInWords(reversedwordlist, MinimumStemLength)

    #--------------------------------------------------------------------##
    #        Break up each word (left-to-right and right-to-left)
    #--------------------------------------------------------------------##

    WordsBrokenLtoR = BreakUpEachWord(wordlist, breaks_LtoR)
    WordsBrokenRtoL = BreakUpEachWord(reversedwordlist, breaks_RtoL)

    #--------------------------------------------------------------------------#
    #        Compute successors and predecessors
    #--------------------------------------------------------------------------# 

    successors = GetSuccessors(wordlist, WordsBrokenLtoR)
    OutputSuccessors(outfile_SF_name, successors, SF_threshold)

    predecessors = GetSuccessors(reversedwordlist, WordsBrokenRtoL)
    OutputSuccessors(outfile_PF_name, predecessors, SF_threshold, reverse=True)

    #--------------------------------------------------------------------------#
    #        Print tries (left-to-right, right-to-left)
    #--------------------------------------------------------------------------# 

    OutputTrie(outfile_trieLtoR_name, WordsBrokenLtoR)
    OutputTrie(outfile_trieRtoL_name, WordsBrokenRtoL, reverse=True)


if __name__ == "__main__":

    args = makeArgParser().parse_args()

    MinimumStemLength = args.minstem
    MinimumAffixLength = args.minaffix
    SF_threshold = args.minsize

    language, corpus, datafolder = load_config(args.language,
                                               args.corpus, args.datafolder)

    print("language: {}".format(language))
    print("corpus file: {}".format(corpus))
    print("datafolder: {}".format(datafolder))
    proceed = input("proceed? [Y/n] ")
    if proceed and (proceed[0].lower() == "n"):
        sys.exit()

    testPath = Path(datafolder, language, corpus)
    if not testPath.exists():
        print("Corpus file does not exist. Check file paths and names.")
        sys.exit()

    main(language, corpus, datafolder,
         MinimumStemLength, MinimumAffixLength, SF_threshold)
