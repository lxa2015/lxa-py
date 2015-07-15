#!/usr/bin/env python3

# John Goldsmith, 2012-
# Jackson Lee, 2015-
# Anton Melnikov, 2015-

#------------------------------------------------------------------------------#

import argparse
import time
from pathlib import Path

from lxa5_module import (read_word_freq_file, MakeBiSignatures,
                         MakeStemToWords, OutputLargeDict, OutputLargeDict2,
                         OutputStemFile, MakeSigToStems,
                         MakeStemToSig, MakeWordToSigs,
                         MakeAffixToSigs, OutputAffixFile)

from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix)

#------------------------------------------------------------------------------#
#        user modified variables
#------------------------------------------------------------------------------#

NumberOfCorrections = 100  # TODO: keep or not?

#------------------------------------------------------------------------------#

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
    parser.add_argument("--minstem", help="Minimum stem length; "
                        "usually from 2 to 5, where a smaller number means "
                        "you can find shorter stems although the program "
                        "may run a lot slower",
                        type=int, default=4)
    parser.add_argument("--maxaffix", help="Maximum affix length; "
                        "usually from 1 to 5, where a larger number means "
                        "you can find longer affixes",
                        type=int, default=3)
    parser.add_argument("--minsig", help="Minimum number of signature use; "
                        "a small number like 5 is pretty much the smallest "
                        "to use in order to filter spurious signatures; may "
                        "try larger numbers like 10 or 20 and so forth",
                        type=int, default=5)
    parser.add_argument("--maxwordtokens", help="maximum number of word tokens;"
                        " if this is zero, then the program counts "
                        "all word tokens in the corpus",
                        type=int, default=0)
    return parser


def create_wordlist(language, filename, datafolder,
                    minimum_stem_length=None, maxwordtokens=0):
    ngram_path = Path(datafolder, language, 'ngrams')
    infilepath = Path(ngram_path, filename)
    word_freq_dict = read_word_freq_file(infilepath,
                                         minimum_stem_length, maxwordtokens)

    wordlist = sorted(word_freq_dict.keys())
    return wordlist, word_freq_dict


def main(language, corpus, datafolder,
         MinimumStemLength, MaximumAffixLength, MinimumNumberofSigUses,
         maxwordtokens):

    if maxwordtokens:
        corpusName = Path(corpus).stem + "-" + str(maxwordtokens)
    else:
        corpusName = Path(corpus).stem

    # -------------------------------------------------------------------------#
    #       decide suffixing or prefixing
    # -------------------------------------------------------------------------#

    suffix_languages = {"english",
                        "french",
                        "hungarian",
                        "turkish",
                        "russian",
                        "german",
                        "spanish",
                        'test'}
    prefix_languages = {"swahili"}

    if language in suffix_languages:
        FindSuffixesFlag = True  # suffixal

    else:
        FindSuffixesFlag = False  # prefixal

    wordlist, wordFreqDict = create_wordlist(language, corpus, datafolder,
                                             maxwordtokens=maxwordtokens)

    outfolder = Path(datafolder, language, 'lxa')

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    # TODO -- filenames not yet used in main()
    outfile_Signatures_name = str(outfolder) + corpusName + "_Signatures.txt"
    outfile_SigTransforms_name = str(outfolder) + corpusName + "_SigTransforms.txt"
    outfile_FSA_name = str(outfolder) + corpusName + "_FSA.txt"
    outfile_FSA_graphics_name = str(outfolder) + corpusName + "_FSA_graphics.png"

    # -------------------------------------------------------------------------#
    #   create: BisigToTuple
    #                  (key: tuple of bisig | value: set of (stem, word1, word2)
    #           StemToWords (key: stem | value: set of words)
    #           SigToStems  (key: tuple of sig | value: set of stems )
    #           StemToSig   (key: str of stem  | value: tuple of sig )
    #           WordToSigs  (key: str of word  | value: set of sigs )
    #           AffixToSigs (key: str of affix | value: set of sigs )
    # -------------------------------------------------------------------------#

    BisigToTuple = MakeBiSignatures(wordlist, FindSuffixesFlag,
                                    MinimumStemLength, MaximumAffixLength)
    print("BisigToTuple ready", flush=True)

    StemToWords = MakeStemToWords(BisigToTuple, MinimumNumberofSigUses)
    print("StemToWords ready", flush=True)

    SigToStems = MakeSigToStems(StemToWords, FindSuffixesFlag,
                                MaximumAffixLength, MinimumNumberofSigUses)
    print("SigToStems ready", flush=True)

    StemToSig = MakeStemToSig(SigToStems)
    print("StemToSig ready", flush=True)

    WordToSigs = MakeWordToSigs(StemToWords, StemToSig)
    print("WordToSigs ready", flush=True)

    AffixToSigs = MakeAffixToSigs(SigToStems)
    print("AffixToSigs ready", flush=True)

    # -------------------------------------------------------------------------#
    #   generate graphs for several dicts
    # -------------------------------------------------------------------------#
    #    GenerateGraphFromDict(StemToWords, outfolder, 'StemToWords.gexf')
    #    GenerateGraphFromDict(SigToStems, outfolder, 'SigToStems.gexf')
    #    GenerateGraphFromDict(WordToSigs, outfolder, 'WordToSigs.gexf')
    #    GenerateGraphFromDict(StemToSig, outfolder, 'StemToSig.gexf')
    # -------------------------------------------------------------------------#

    # -------------------------------------------------------------------------#
    #      output stem file
    # -------------------------------------------------------------------------#

    stemfilename = Path(outfolder, '{}_StemToWords.txt'.format(corpusName))
    #OutputStemFile(stemfilename, StemToWords, wordFreqDict)
    OutputLargeDict2(stemfilename, StemToWords)

    print('===> stem file generated:', stemfilename, flush=True)

    # -------------------------------------------------------------------------#
    #      output affix file
    # -------------------------------------------------------------------------#

    affixfilename = Path(outfolder, '{}_AffixToSigs.txt'.format(corpusName))
#    OutputAffixFile(affixfilename, AffixToSigs)
    OutputLargeDict(affixfilename, AffixToSigs, howmanyperline=5)
    print('===> affix file generated:', affixfilename, flush=True)

    # -------------------------------------------------------------------------#
    #   pickle SigToStems # TODO: probably switching to json
    # -------------------------------------------------------------------------#
    #    SigToStems_pkl_fname = Path(outfolder, corpusName + "_SigToStems.pkl")
    #    with SigToStems_pkl_fname.open('wb') as f:
    #        pickle.dump(SigToStems, f)
    #    print('===> pickle file generated:', SigToStems_pkl_fname, flush=True)
    # -------------------------------------------------------------------------#

    # -------------------------------------------------------------------------#
    #   output SigToStems
    # -------------------------------------------------------------------------#

    SigToStems_outfilename = Path(outfolder, corpusName + "_SigToStems.txt")
    OutputLargeDict(SigToStems_outfilename, SigToStems)

    SigToStems_outfilename_json = changeFilenameSuffix(SigToStems_outfilename,
                                                       ".json")
    json_pdump(SigToStems, SigToStems_outfilename_json.open("w"),
               sort_function=lambda x : len(x[1]), reverse=True)

    print('===> output file generated:', SigToStems_outfilename, flush=True)
    print('===> output file generated:', SigToStems_outfilename_json, flush=True)

    # -------------------------------------------------------------------------#
    #   output WordToSigs
    # -------------------------------------------------------------------------#

    WordToSigs_outfilename = Path(outfolder, corpusName + "_WordToSigs.txt")
    OutputLargeDict2(WordToSigs_outfilename, WordToSigs,SignatureFlag = True)

    WordToSigs_outfilename_json = changeFilenameSuffix(WordToSigs_outfilename,
                                                       ".json")
    json_pdump(WordToSigs, WordToSigs_outfilename_json.open("w"),
               sort_function=lambda x : len(x[1]), reverse=True)

    print('===> output file generated:', WordToSigs_outfilename, flush=True)
    print('===> output file generated:', WordToSigs_outfilename_json, flush=True)

    # -------------------------------------------------------------------------#
    #   output the most freq word types not in any induced paradigms {the, of..}
    # -------------------------------------------------------------------------#

    mostFreqWordsNotInSigs_outfilename = Path(outfolder,
                                              corpusName +
                                              "_mostFreqWordsNotInSigs.txt")

    with mostFreqWordsNotInSigs_outfilename.open('w') as f:

        for (word, freq) in sorted(wordFreqDict.items(),
                                   key=lambda x: x[1], reverse=True):
            if word in WordToSigs:
                break
            else:
                print(word, freq, file=f)

    print('===> output file generated:',
          mostFreqWordsNotInSigs_outfilename, flush=True)

    # -------------------------------------------------------------------------#
    #   output the word types in induced paradigms
    # -------------------------------------------------------------------------#

    WordsInSigs_outfilename = Path(outfolder, corpusName + "_WordsInSigs.txt")

    with WordsInSigs_outfilename.open('w') as f:

        wordFreqInSigListSorted = [(word, freq) for (word, freq) in
                                   sorted(wordFreqDict.items(),
                                          key=lambda x: x[1], reverse=True)
                                   if word in WordToSigs]

        for (word, freq) in wordFreqInSigListSorted:
            print(word, freq, file=f)

    print('===> output file generated:',
          WordsInSigs_outfilename, flush=True)

    # -------------------------------------------------------------------------#
    #   output the word types NOT in induced paradigms
    # -------------------------------------------------------------------------#

    WordsNotInSigs_outfilename = Path(outfolder,
                                      corpusName + "_WordsNotInSigs.txt")

    with WordsNotInSigs_outfilename.open('w') as f:

        wordFreqInSigListSorted = [(word, freq) for (word, freq) in
                                   sorted(wordFreqDict.items(),
                                          key=lambda x: x[1], reverse=True)
                                   if word not in WordToSigs]

        for (word, freq) in wordFreqInSigListSorted:
            print(word, freq, file=f)

    print('===> output file generated:',
          WordsNotInSigs_outfilename, flush=True)


# -----------------------------------------------------------------------------#

# TODO: bring the following back later

def to_be_handled():
    # ------------------------------------------------------------------------------#
    #        input and output files
    # ------------------------------------------------------------------------------#

    Signatures_outfile = open(outfile_Signatures_name, 'w')

    SigTransforms_outfile = open(outfile_SigTransforms_name, 'w')

    FSA_outfile = open(outfile_FSA_name, 'w')

    # July 15, 2014, Jackson Lee

    outfile_Signatures_name_JL = outfolder + corpusName + "_Signatures-JL.txt"
    Signatures_outfile_JL = open(outfile_Signatures_name_JL, 'w')



    # ------------------------------------------------------------------------------#
    #       write log file header | TODO keep this part or rewrite?
    # ------------------------------------------------------------------------------#

    #    outfile_log_name            = outfolder + corpusName + "_log.txt"
    #    log_file = open(outfile_log_name, "w")
    #    print("Language:", language, file=log_file)
    #    print("Minimum Stem Length:", MinimumStemLength,
    #          "\nMaximum Affix Length:", MaximumAffixLength,
    #          "\n Minimum Number of Signature uses:", MinimumNumberofSigUses,
    #          file=log_file)
    #    print("Date:", end=' ', file=log_file)





    # ------------------------------------------------------------------------------#
    # ------------------------------------------------------------------------------#
    #                     Main part of program                              #
    # ------------------------------------------------------------------------------#
    # ------------------------------------------------------------------------------#

    # For the following dicts ---
    # BisigToTuple:  keys are tuples of bisig   Its values are (stem, word1, word2)
    # SigToStems:    keys are signatures.  Its values are *sets* of stems. 
    # StemToWord:    keys are stems.       Its values are *sets* of words.
    # StemToSig:     keys are stems.       Its values are individual signatures.
    # WordToSig:     keys are words.       Its values are *lists* of signatures.
    # StemCounts:    keys are words.      Its values are corpus counts of stems.


    BisigToTuple = {}
    SigToStems = {}
    WordToSig = {}
    StemToWord = {}
    StemCounts = {}
    StemToSig = {}
    numberofwords = len(wordlist)



    # ------------------------------------------------------------------------------#
    #    1. Make signatures, and WordToSig dictionary,
    #       and Signature dictionary-of-stem-lists, and StemToSig dictionary
    # ------------------------------------------------------------------------------#
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("1.                Make signatures 1")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    # ------------------------------------------------------------------------------#
    #    1a. Declare a linguistica-style FSA
    # ------------------------------------------------------------------------------#

    splitEndState = True
    morphology = FSA_lxa(splitEndState)

    # ------------------------------------------------------------------------------#
    #    1b. Find signatures, and put them in the FSA also.
    # ------------------------------------------------------------------------------#

    SigToStems, WordToSig, StemToSig = MakeSignatures(StemToWord,
                                                      FindSuffixesFlag, MinimumNumberofSigUses)

    # ------------------------------------------------------------------------------#
    #    1c. Print the FSA to file.
    # ------------------------------------------------------------------------------#

    # print "line 220", outfile_FSA_name # TODO: what's this line for?

    # morphology.printFSA(FSA_outfile)


    # ------------ Added Sept 24 (year 2013) for Jackson's program -----------------#
    if True:
        printSignatures(SigToStems, WordToSig, StemCounts,
                        Signatures_outfile, g_encoding, FindSuffixesFlag)
        # added July 15, 2014, Jackson Lee
        printSignaturesJL(SigToStems, WordToSig, StemCounts,
                          Signatures_outfile_JL, g_encoding, FindSuffixesFlag)
    Signatures_outfile_JL.close()



    # ------------------------------------------------------------------------------#
    # 5. Look to see which signatures could be improved, and score the improvement
    #    quantitatively with robustness.
    # Then we improve the one whose robustness increase is the greatest.
    # ------------------------------------------------------------------------------#

    print("***", file=Signatures_outfile)
    print("*** 5. Finding robust suffixes in stem sets\n\n", file=Signatures_outfile)


    # ------------------------------------------------------------------------------#
    #    5a. Find morphemes within edges: how many times? NumberOfCorrections
    # ------------------------------------------------------------------------------#

    for loopno in range(NumberOfCorrections):
        # -------------------------------------------------------------------------#
        #    5b. For each edge, find best peripheral piece that might be 
        #           a separate morpheme.
        # -------------------------------------------------------------------------#
        morphology.find_highest_weight_affix_in_an_edge(Signatures_outfile,
                                                        FindSuffixesFlag)

    # ------------------------------------------------------------------------------#
    #    5c. Print graphics based on each state.
    # ------------------------------------------------------------------------------#
    if True:
        for state in morphology.States:
            graph = morphology.createPySubgraph(state)
            if len(graph.edges()) < 4:
                continue
            graph.layout(prog='dot')
            filename = outfolder + 'morphology' + str(state.index) + '.png'
            graph.draw(filename)
            filename = outfolder + 'morphology' + str(state.index) + '.dot'
            graph.write(filename)


    # ------------------------------------------------------------------------------#
    #    5d. Print FSA again, with these changes.
    # ------------------------------------------------------------------------------#

    if True:
        morphology.printFSA(FSA_outfile)


    # ------------------------------------------------------------------------------#
    localtime1 = time.asctime(time.localtime(time.time()))
    print("Local current time :", localtime1)

    morphology.dictOfLists_parses = morphology.parseWords(wordlist)

    localtime2 = time.asctime(time.localtime(time.time()))
    # print "Time to parse all words: ", localtime2 - localtime1


    # ------------------------------------------------------------------------------#


    print("Finding common stems across edges.", file=FSA_outfile)
    HowManyTimesToCollapseEdges = 9
    for loop in range(HowManyTimesToCollapseEdges):
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Loop number", loop)
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        (commonEdgePairs, EdgeToEdgeCommonMorphs) = morphology.findCommonStems()
        # We now have a list of pairs of edges, sorted by how many stems they share in common. 
        # In the current implementation, we consider only pairs of edges that have a common mother or daughter....    


        if len(commonEdgePairs) == 0:
            print("There are no more pairs of edges to consider.")
            break
        edge1, edge2 = commonEdgePairs[0]
        state1 = edge1.fromState
        state2 = edge2.fromState
        state3 = edge1.toState
        state4 = edge2.toState
        print("\n\nWe are considering merging edge ", edge1.index, "(", edge1.fromState.index, "->",
              edge1.toState.index, ") and  edge", edge2.index, "(", edge2.fromState.index, "->", edge2.toState.index,
              ")")

        print("Printed graph", str(loop), "before_merger")
        graph = morphology.createDoublePySubgraph(state1, state2)
        graph.layout(prog='dot')
        filename = outfolder + corpusName + str(loop) + '_before_merger' + str(state1.index) + "-" + str(
            state2.index) + '.png'
        graph.draw(filename)

        if state1 == state2:
            print("The from-States are identical")
            state_changed_1 = state1
            state_changed_2 = state2
            morphology.mergeTwoStatesCommonMother(state3, state4)
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        elif state3 == state4:
            print("The to-States are identical")
            state_changed_1 = state3
            state_changed_2 = state4
            morphology.mergeTwoStatesCommonDaughter(state1, state2)
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        elif morphology.mergeTwoStatesCommonMother(state1, state2):
            print("Now we have merged two sister edges from line 374 **********")
            state_changed_1 = state1
            state_changed_2 = state2
            morphology.EdgePairsToIgnore.append((edge1, edge2))


        elif morphology.mergeTwoStatesCommonDaughter((state3, state4)):
            print("Now we have merged two daughter edges from line 377 **********")
            state_changed_1 = state3
            state_changed_2 = state4
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        graph = morphology.createDoublePySubgraphcreatePySubgraph(state1)
        graph.layout(prog='dot')
        filename = outfolder + str(loop) + '_after_merger_' + str(state_changed_1.index) + "-" + str(
            state_changed_2.index) + '.png'
        print("Printed graph", str(loop), "after_merger")
        graph.draw(outfile_FSA_graphics_name)

    # ---------------------------------------------------------------------------------------------------------------------------#
    # We create a list of words, each word with its signature transform (so DOGS is turned into NULL.s_s, for example)

    if True:
        printWordsToSigTransforms(SigToStems, WordToSig, StemCounts, SigTransforms_outfile, g_encoding,
                                  FindSuffixesFlag)


    # ---------------------------------------------------------------------------------------------------------------------------#
    # ---------------------------------------------------------------------------------#
    #    Close output files
    # ---------------------------------------------------------------------------------#

    FSA_outfile.close()
    Signatures_outfile.close()
    SigTransforms_outfile.close()


    # ---------------------------------------------------------------------------------#
    #    Logging information
    # ---------------------------------------------------------------------------------#

    localtime = time.asctime(time.localtime(time.time()))
    print("Local current time :", localtime)

    numberofwords = len(wordlist)
    logfilename = outfolder + "logfile.txt"
    logfile = open(logfilename, "a")

    print(outfile_Signatures_name.ljust(60),
          '%30s wordcount: %8d data source:' % (localtime, numberofwords),
          infilename.ljust(50), file=logfile)


if __name__ == "__main__":

    args = makeArgParser().parse_args()

    MinimumStemLength = args.minstem
    MaximumAffixLength = args.maxaffix
    MinimumNumberofSigUses = args.minsig
    maxwordtokens = args.maxwordtokens

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                                   args.corpus, args.datafolder)

    main(language, corpus, datafolder,
         MinimumStemLength, MaximumAffixLength, MinimumNumberofSigUses,
         maxwordtokens)

