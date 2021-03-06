#!usr/bin/env python3

# This program creates a left-to-right trie and a right-to-left trie,
# as well as both successors and predecessors.
#
# John Goldsmith 2015
# Jackson Lee 2015

import sys
import argparse
from pathlib import Path

import ngrams
from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix, stdout_list,
                     load_config_for_command_line_help,
                     determine_use_corpus, get_wordlist_path_corpus_stem,
                     read_word_freq)

import ngrams

def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="The program computes tries given corpus data.\n\n{}"
                    .format(configtext),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--config", help="configuration filename",
                        type=str, default=configfilename)

    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="relative path of the data folder",
                        type=str, default=None)

    parser.add_argument("--minstem", help="Minimum stem length; "
                        "usually from 2 to 5, where a smaller number means "
                        "you can find shorter stems although the program "
                        "may run a lot slower",
                        type=int, default=4)
    parser.add_argument("--minaffix", help="Minimum affix length",
                        type=int, default=1)
    parser.add_argument("--minsize",  help="Minimum size of "
                                           "successors/predecessors for output",
                        type=int, default=3)
    parser.add_argument("--maxwordtokens", help="maximum number of word tokens;"
                        " if this is zero, then the program counts "
                        "all word tokens in the corpus",
                        type=int, default=0)
    return parser


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
        WordsBroken[thisword] = list()
        breakList = sorted(breakListDict[i])

        if not breakList:
            WordsBroken[thisword].append(thisword)
        else:
            thispiece = ""
            for x in range(len(thisword)):
                thispiece += thisword[x]
                if x+1 in breakList:
                    WordsBroken[thisword].append(thispiece)
                    thispiece = ""
            if thispiece:
                WordsBroken[thisword].append(thispiece)

    return WordsBroken


def GetSuccessors(wordlist, WordsBroken):
    successors = dict()
    for i, thisword in enumerate(wordlist):
        wordbeginning = ""
        thiswordparsed = WordsBroken[thisword]
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

    for wordbegin in successors: #turn these into an alphabetized list
        successors[wordbegin]=list (successors[wordbegin])
        successors[wordbegin].sort()

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

def OutputSignatures1(outfilename, successors):
    stemlist = list(successors.keys())
    stemlist.sort()
    sigs = dict()
    columnwidth = 12
    howmanyperline = 5
    with outfilename.open("w") as f:
        for stem in stemlist:
            suffixes= successors[stem]
            if len(suffixes) == 1 and suffixes[0]=="NULL":
                continue
            suffix_string = "-".join(suffixes)
            print (   stem, suffixes , file = f)
            if suffix_string not in sigs:
                sigs[suffix_string] = dict()
            sigs[suffix_string][stem]= 1

        siglist = list(sigs.keys())
        siglist.sort(key= lambda x:len(sigs[x]),reverse=True)   

        print (file=f)

        for sig in siglist:
            print ("\n\n________________________________", file=f)	
            print (sig, file=f)	
            print ("________________________________", file=f)
            i = 0    
            for stem in sigs[sig]:    
                print (stem, " "*(columnwidth-len(stem)), end="", file=f)    		
                i=i+1
                if i==howmanyperline:
                    i = 0
                    print (file=f)

def OutputTrie(outfile, wordlist, WordsBroken, reverse=False):

    if reverse:
        # dealing with predecessors, not successors
        WordsBroken_new = dict()
        for i, BrokenWord in WordsBroken.items():
            WordsBroken_new[i] = [x[::-1] for x in BrokenWord][::-1]
        WordsBroken = WordsBroken_new

    with outfile.open("w") as f:
        for thisword in wordlist:
            for j in range(len(WordsBroken[thisword])):
                thispiece = WordsBroken[thisword][j]
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


def main(language=None, corpus=None, datafolder=None, filename=None,
         MinimumStemLength=4, MinimumAffixLength=1, SF_threshold=3,
         maxwordtokens=0, use_corpus=True):

    print("\n*****************************************************\n"
          "Running the tries.py program now...\n")

    #--------------------------------------------------------------------##
    #        read wordlist
    #--------------------------------------------------------------------##

    print("reading wordlist...", flush=True)

    wordlist_path, corpusName = get_wordlist_path_corpus_stem(language, corpus,
                                datafolder, filename, maxwordtokens, use_corpus)

    print("wordlist file path:\n{}\n".format(wordlist_path))

    if not wordlist_path.exists():
        if use_corpus:
            if maxwordtokens:
                warning = " ({} tokens)".format(maxwordtokens)
            else:
                warning = ""
            print("\nWordlist for {}{} not found.\n"
                  "ngrams.py is now run.\n".format(corpus, warning))
            ngrams.main(language=language, corpus=corpus,
                        datafolder=datafolder, filename=filename,
                        maxwordtokens=maxwordtokens)
        else:
            sys.exit("\nThe specified wordlist ""\n"
                     "is not found.".format(wordlist_path))

    wordFreqDict = read_word_freq(wordlist_path)
    wordlist = sorted(wordFreqDict.keys())
    reversedwordlist = sorted([x[::-1] for x in wordlist])

    #--------------------------------------------------------------------##
    #        output settings
    #--------------------------------------------------------------------##

    if filename:
        outfolder = Path(Path(filename).parent, "tries")
    else:
        outfolder = Path(datafolder, language, "tries")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    outfile_SF_name = Path(outfolder, corpusName + "_SF.txt")
    outfile_trieLtoR_name = Path(outfolder, corpusName + "_trieLtoR.txt")
     
    outfile_trieRtoL_name = Path(outfolder, corpusName + "_trieRtoL.txt")
    outfile_PF_name = Path(outfolder, corpusName + "_PF.txt")

    outfile_Signatures_name = Path(outfolder, corpusName + "_Signatures.txt")

    #--------------------------------------------------------------------##
    #        Find breaks in words (left-to-right and right-to-left)
    #--------------------------------------------------------------------##

    print("finding breaks in words...", flush=True)

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

    print("computing successors and predecessors...", flush=True)

    successors = GetSuccessors(wordlist, WordsBrokenLtoR)
    OutputSuccessors(outfile_SF_name, successors, SF_threshold)

    predecessors = GetSuccessors(reversedwordlist, WordsBrokenRtoL)
    OutputSuccessors(outfile_PF_name, predecessors, SF_threshold, reverse=True)

    outfile_SF_name_json = changeFilenameSuffix(outfile_SF_name, ".json")
    json_pdump(successors, outfile_SF_name_json.open("w"))

    outfile_PF_name_json = changeFilenameSuffix(outfile_PF_name, ".json")
    json_pdump(predecessors, outfile_PF_name_json.open("w"))

    print("printing signatures...", flush=True)
    OutputSignatures1(outfile_Signatures_name, successors)

    #--------------------------------------------------------------------------#
    #        Print tries (left-to-right, right-to-left)
    #--------------------------------------------------------------------------# 

    print("printing tries...", flush=True)

    OutputTrie(outfile_trieLtoR_name, wordlist, WordsBrokenLtoR)
    OutputTrie(outfile_trieRtoL_name, reversedwordlist, WordsBrokenRtoL, reverse=True)

    outfile_trieLtoR_name_json = changeFilenameSuffix(outfile_trieLtoR_name, ".json")
    json_pdump(WordsBrokenLtoR, outfile_trieLtoR_name_json.open("w"))

    outfile_trieRtoL_name_json = changeFilenameSuffix(outfile_trieRtoL_name, ".json")
    json_pdump(WordsBrokenRtoL, outfile_trieRtoL_name_json.open("w"))

    stdout_list("Output files:", outfile_SF_name, outfile_PF_name,
                                 outfile_trieLtoR_name, outfile_trieRtoL_name,
                                 outfile_Signatures_name,
                                 outfile_SF_name_json, outfile_PF_name_json,
                                 outfile_trieLtoR_name_json,
                                 outfile_trieRtoL_name_json)


if __name__ == "__main__":

    args = makeArgParser().parse_args()

    MinimumStemLength = args.minstem
    MinimumAffixLength = args.minaffix
    SF_threshold = args.minsize
    maxwordtokens = args.maxwordtokens

    description="You are running {}.\n".format(__file__) + \
                "This program computes tries.\n" + \
                "MinimumStemLength = {}\n".format(MinimumStemLength) + \
                "MinimumAffixLength = {}\n".format(MinimumAffixLength) + \
                "SF_threshold = {}\n".format(SF_threshold) + \
                "maxwordtokens = {} (zero means all word tokens)".format(maxwordtokens)

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    use_corpus = determine_use_corpus()

    main(language=language, corpus=corpus, datafolder=datafolder,
         MinimumStemLength=MinimumStemLength,
         MinimumAffixLength=MinimumAffixLength,
         SF_threshold=SF_threshold,
         maxwordtokens=maxwordtokens, use_corpus=use_corpus)

