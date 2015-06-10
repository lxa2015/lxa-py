#!/usr/bin/env python3

# John Goldsmith, 2012-
# Jackson Lee, 2015-

# TODO: trie structure

#------------------------------------------------------------------------------#

import time
import datetime
import operator
import sys
import os
import string
import copy
import argparse
import pickle
from collections import defaultdict

from lxa5_module import *

#------------------------------------------------------------------------------#
#        user modified variables
#------------------------------------------------------------------------------#

NumberOfCorrections = 100 # TODO: keep or not?

#------------------------------------------------------------------------------#

def makeArgParser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--language", help="Language name", type=str,
            default="english")
    parser.add_argument("--corpus", help="Corpus to use", type=str,
            default="brown")
    parser.add_argument("--minstem", help="Minimum stem length", type=int,
            default=4)
    parser.add_argument("--maxaffix", help="Maximum affix length", type=int,
            default=3)
    parser.add_argument("--minsig", help="Minimum number of signatures", type=int,
            default=50)
    return parser

def main(argv):
    args = makeArgParser().parse_args()

    #--------------------------------------------------------------------------#
    #      set up language and corpus names; set up all paths and filenames
    #--------------------------------------------------------------------------#
    language = args.language
    corpus = args.corpus
    MinimumStemLength     = args.minstem
    MaximumAffixLength     = args.maxaffix
    MinimumNumberofSigUses     = args.minsig

    datafolder            = "../../data/" 
    ngramfolder           = datafolder + language + "/ngrams/"
    outfolder             = datafolder + language + "/lxa/"

    if not os.path.exists(outfolder):
        os.makedirs(outfolder)

    short_filename = language + '-' + corpus

    infilename = ngramfolder  + short_filename     + "_words.txt"

    stemfilename                = outfolder  + short_filename     + "_stems.txt"

    # TODO -- filenames not yet used in main()
    outfile_Signatures_name     = outfolder + short_filename + "_Signatures.txt"  
    outfile_SigTransforms_name  = outfolder + short_filename + "_SigTransforms.txt"
    outfile_FSA_name            = outfolder + short_filename + "_FSA.txt"
    outfile_FSA_graphics_name   = outfolder + short_filename + "_FSA_graphics.png"

    #--------------------------------------------------------------------------#
    #       decide suffixing or prefixing
    #--------------------------------------------------------------------------#

    suffix_languages = ["english", "french", "hungarian", "turkish", "test", "german", "spanish"]
    prefix_languages = ["swahili"]

    if language in suffix_languages:
        FindSuffixesFlag = True # suffixal

    if language in prefix_languages:
        FindSuffixesFlag = False # prefixal

    #--------------------------------------------------------------------------#
    #      create word+freq dict from file; derive wordlist
    #--------------------------------------------------------------------------#

    wordFreqDict = ReadWordFreqFile(infilename, MinimumStemLength)

    wordlist = list(wordFreqDict.keys())
    wordlist.sort()

    #--------------------------------------------------------------------------#
    #   create: BisigToTuple
    #                  (key: tuple of bisig | value: set of (stem, word1, word2)
    #           StemToWords (key: stem | value: set of words)
    #           StemCounts (key: stem | value: int --- sum of counts 
    #                                       for each word in StemToWords[stem] )
    #--------------------------------------------------------------------------#
    BisigToTuple = MakeBiSignatures(wordlist, FindSuffixesFlag,
                                  MinimumStemLength, MaximumAffixLength)
    print("BisigToTuple ready", flush=True)

    StemToWords = MakeStemToWords(BisigToTuple, MinimumNumberofSigUses)
    print("StemToWords ready", flush=True)

    StemCounts = MakeStemCounts(StemToWords, wordFreqDict)
    print('StemCounts ready', flush=True)

    #--------------------------------------------------------------------------#
    #      output stem file
    #--------------------------------------------------------------------------#
    OutputStemFile(stemfilename, StemToWords, StemCounts)
    print('===> stem file generated:', stemfilename, flush=True)

    #--------------------------------------------------------------------------#
    #   create: SigToStems  (key: tuple of sig | value: set of stems )
    #           StemToSig   (key: str of stem  | value: tuple of sig )
    #           WordToSigs  (key: str of word  | value: set of sigs )
    #--------------------------------------------------------------------------#
    SigToStems = MakeSigToStems(StemToWords, FindSuffixesFlag,
                                    MaximumAffixLength, MinimumNumberofSigUses)
    print("SigToStems ready", flush=True)

    StemToSig = MakeStemToSig(SigToStems)
    print("StemToSig ready", flush=True)

    WordToSigs = MakeWordToSigs(StemToWords, StemToSig)
    print("WordToSigs ready", flush=True)


    #--------------------------------------------------------------------------#
    #   pickle SigToStems
    #--------------------------------------------------------------------------#
    SigToStems_pkl_fname = outfolder  + short_filename     + "_SigToStems.pkl"
    with open(SigToStems_pkl_fname, 'wb') as f:
        pickle.dump(SigToStems, f)
    print('===> pickle file generated:', SigToStems_pkl_fname, flush=True)

        #    # read python dict back from the file
        #    pkl_file = open('myfile.pkl', 'rb')
        #    mydict2 = pickle.load(pkl_file)
        #    pkl_file.close()




    #--------------------------------------------------------------------------#
    #   generate graphs for several dicts
    #--------------------------------------------------------------------------#
#    GenerateGraphFromDict(StemToWords, outfolder, 'StemToWords.gexf')
#    GenerateGraphFromDict(SigToStems, outfolder, 'SigToStems.gexf')
#    GenerateGraphFromDict(WordToSigs, outfolder, 'WordToSigs.gexf')
#    GenerateGraphFromDict(StemToSig, outfolder, 'StemToSig.gexf')

    #--------------------------------------------------------------------------#

    nWordsInParadigms = 0
    SigToStemsSortedList = sorted(SigToStems.items(),
                                  key=lambda x : len(x[1]), reverse=True)
    print('nSigs', len(SigToStemsSortedList))
    for (idx, (sig, stemList)) in enumerate(SigToStemsSortedList):
        nStems = len(stemList)
        nWordsInParadigms = nWordsInParadigms + nStems * len(sig)
#        print(idx, sig)
#        print(nStems, end=' ')
#        print(sig, len(stemList))
#        if idx > 20:
#            break

    print('nWordsInParadigms:', nWordsInParadigms)
    #--------------------------------------------------------------------------#

    #--------------------------------------------------------------------------#
    #   output SigToStems
    #--------------------------------------------------------------------------#

    SigToStems_outfilename = outfolder  + short_filename     + "_SigToStems.txt"
    with open(SigToStems_outfilename, 'w') as f:
        for (idx, (sig, stemList)) in enumerate(SigToStemsSortedList):
            print(sig, len(stemList), file=f)

        print(file=f)

        for (sig, stemList) in SigToStemsSortedList:
            print(sig, len(stemList), file=f)
            for (idx, stem) in enumerate(sorted(stemList), 1):
                print(stem, end=' ', file=f)
                if idx % 10 == 0:
                    print(file=f)
            print(file=f)
            print(file=f)

    print('===> output file generated:', SigToStems_outfilename, flush=True)

    #--------------------------------------------------------------------------#
    #   output the most freq word types not in any induced paradigms {the, of..}
    #--------------------------------------------------------------------------#

    mostFreqWordsNotInSigs_outfilename = outfolder  + \
                                short_filename  + "_mostFreqWordsNotInSigs.txt"

    with open(mostFreqWordsNotInSigs_outfilename, 'w') as f:

        for (word, freq) in sorted(wordFreqDict.items(),
                                   key=lambda x:x[1], reverse=True):
            if word in WordToSigs:
                break
            else:
                print(word, freq, file=f)

    print('===> output file generated:',
          mostFreqWordsNotInSigs_outfilename, flush=True)

    #--------------------------------------------------------------------------#
    #   output the word types in induced paradigms
    #--------------------------------------------------------------------------#

    WordsInSigs_outfilename = outfolder  + \
                                short_filename  + "_WordsInSigs.txt"

    with open(WordsInSigs_outfilename, 'w') as f:

        wordFreqInSigListSorted = [(word, freq) for (word, freq) in
                                   sorted(wordFreqDict.items(),
                                          key=lambda x:x[1], reverse=True)
                                   if word in WordToSigs]

        for (word, freq) in wordFreqInSigListSorted:
            print(word, freq, file=f)

    print('===> output file generated:',
          WordsInSigs_outfilename, flush=True)

#------------------------------------------------------------------------------#

# TODO: bring the following back later

def to_be_handled():

    #------------------------------------------------------------------------------#
    #        input and output files
    #------------------------------------------------------------------------------#

    Signatures_outfile = open(outfile_Signatures_name, 'w')
    SigTransforms_outfile = open(outfile_SigTransforms_name, 'w')
    FSA_outfile = open(outfile_FSA_name, 'w')

    # July 15, 2014, Jackson Lee
    outfile_Signatures_name_JL = outfolder + short_filename + "_Signatures-JL.txt"
    Signatures_outfile_JL = open(outfile_Signatures_name_JL, 'w')



    #------------------------------------------------------------------------------#
    #       write log file header | TODO keep this part or rewrite?
    #------------------------------------------------------------------------------#

#    outfile_log_name            = outfolder + short_filename + "_log.txt"
#    log_file = open(outfile_log_name, "w")
#    print("Language:", language, file=log_file)
#    print("Minimum Stem Length:", MinimumStemLength,
#          "\nMaximum Affix Length:", MaximumAffixLength,
#          "\n Minimum Number of Signature uses:", MinimumNumberofSigUses,
#          file=log_file)
#    print("Date:", end=' ', file=log_file)





    #------------------------------------------------------------------------------#
    #------------------------------------------------------------------------------#
    #                     Main part of program                              #
    #------------------------------------------------------------------------------#
    #------------------------------------------------------------------------------#

    # For the following dicts ---
    # BisigToTuple:  keys are tuples of bisig   Its values are (stem, word1, word2)
    # SigToStems:    keys are signatures.  Its values are *sets* of stems. 
    # StemToWord:    keys are stems.       Its values are *sets* of words.
    # StemToSig:     keys are stems.       Its values are individual signatures.
    # WordToSig:     keys are words.       Its values are *lists* of signatures.
    # StemCounts:    keys are words.      Its values are corpus counts of stems.


    BisigToTuple      = {}
    SigToStems        = {}
    WordToSig         = {}
    StemToWord        = {}
    StemCounts        = {}
    StemToSig         = {}
    numberofwords     = len(wordlist)



    #------------------------------------------------------------------------------#
    #    1. Make signatures, and WordToSig dictionary,
    #       and Signature dictionary-of-stem-lists, and StemToSig dictionary
    #------------------------------------------------------------------------------#
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("1.                Make signatures 1")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    #------------------------------------------------------------------------------#
    #    1a. Declare a linguistica-style FSA
    #------------------------------------------------------------------------------#

    splitEndState = True
    morphology = FSA_lxa(splitEndState)

    #------------------------------------------------------------------------------#
    #    1b. Find signatures, and put them in the FSA also.
    #------------------------------------------------------------------------------# 

    SigToStems, WordToSig, StemToSig =  MakeSignatures(StemToWord,
                FindSuffixesFlag, MinimumNumberofSigUses)

    #------------------------------------------------------------------------------#
    #    1c. Print the FSA to file.
    #------------------------------------------------------------------------------#

    #print "line 220", outfile_FSA_name # TODO: what's this line for?

    #morphology.printFSA(FSA_outfile) 


    #------------ Added Sept 24 (year 2013) for Jackson's program -----------------#
    if True:
        printSignatures(SigToStems, WordToSig, StemCounts,
                        Signatures_outfile, g_encoding, FindSuffixesFlag)
        # added July 15, 2014, Jackson Lee
        printSignaturesJL(SigToStems, WordToSig, StemCounts,
                          Signatures_outfile_JL, g_encoding, FindSuffixesFlag) 
    Signatures_outfile_JL.close() 


     
    #------------------------------------------------------------------------------#
    # 5. Look to see which signatures could be improved, and score the improvement
    #    quantitatively with robustness.
    # Then we improve the one whose robustness increase is the greatest.
    #------------------------------------------------------------------------------#

    print("***", file=Signatures_outfile)
    print("*** 5. Finding robust suffixes in stem sets\n\n", file=Signatures_outfile)


    #------------------------------------------------------------------------------#
    #    5a. Find morphemes within edges: how many times? NumberOfCorrections
    #------------------------------------------------------------------------------#

    for loopno in range( NumberOfCorrections):
        #-------------------------------------------------------------------------#
        #    5b. For each edge, find best peripheral piece that might be 
        #           a separate morpheme.
        #-------------------------------------------------------------------------#
        morphology.find_highest_weight_affix_in_an_edge (Signatures_outfile,
                                                         FindSuffixesFlag)

    #------------------------------------------------------------------------------#
    #    5c. Print graphics based on each state.
    #------------------------------------------------------------------------------# 
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
         
         
    #------------------------------------------------------------------------------#
    #    5d. Print FSA again, with these changes.
    #------------------------------------------------------------------------------# 

    if True:
        morphology.printFSA(FSA_outfile)
     
     
    #------------------------------------------------------------------------------#
    localtime1 = time.asctime( time.localtime(time.time()) )
    print("Local current time :", localtime1)

    morphology.dictOfLists_parses = morphology.parseWords(wordlist)

    localtime2 = time.asctime( time.localtime(time.time()) )
    #print "Time to parse all words: ", localtime2 - localtime1


    #------------------------------------------------------------------------------#

     
    print >>FSA_outfile, "Finding common stems across edges."
    HowManyTimesToCollapseEdges = 9
    for loop in range(HowManyTimesToCollapseEdges): 
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("Loop number", loop)
        print("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        (commonEdgePairs,  EdgeToEdgeCommonMorphs) = morphology.findCommonStems()
        # We now have a list of pairs of edges, sorted by how many stems they share in common. 
        # In the current implementation, we consider only pairs of edges that have a common mother or daughter....    


        if len( commonEdgePairs ) == 0:
            print("There are no more pairs of edges to consider.")
            break
        edge1, edge2 = commonEdgePairs[0]
        state1 = edge1.fromState
        state2 = edge2.fromState
        state3 = edge1.toState
        state4 = edge2.toState
        print("\n\nWe are considering merging edge ", edge1.index,"(", edge1.fromState.index, "->", edge1.toState.index, ") and  edge", edge2.index, "(", edge2.fromState.index, "->", edge2.toState.index , ")")
         
        print("Printed graph", str(loop), "before_merger")
        graph = morphology.createDoublePySubgraph(state1,state2)     
        graph.layout(prog='dot')
        filename = outfolder + short_filename + str(loop) + '_before_merger' + str(state1.index) + "-" + str(state2.index) + '.png'
        graph.draw(filename) 

        if state1 == state2:
            print("The from-States are identical")
            state_changed_1 = state1
            state_changed_2 = state2
            morphology.mergeTwoStatesCommonMother(state3,state4)
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        elif state3 == state4:
            print("The to-States are identical")
            state_changed_1 = state3
            state_changed_2 = state4     
            morphology.mergeTwoStatesCommonDaughter(state1,state2) 
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        elif morphology.mergeTwoStatesCommonMother(state1,state2):
            print("Now we have merged two sister edges from line 374 **********")
            state_changed_1 = state1
            state_changed_2 = state2
            morphology.EdgePairsToIgnore.append((edge1, edge2))

        
        elif   morphology.mergeTwoStatesCommonDaughter((state3,state4))  : 
            print("Now we have merged two daughter edges from line 377 **********")
            state_changed_1 = state3
            state_changed_2 = state4
            morphology.EdgePairsToIgnore.append((edge1, edge2))
             
        graph = morphology.createDoublePySubgraphcreatePySubgraph(state1)     
        graph.layout(prog='dot')
        filename = outfolder + str(loop) +  '_after_merger_' + str(state_changed_1.index) +  "-" + str(state_changed_2.index) + '.png'
        print("Printed graph", str(loop), "after_merger")
        graph.draw(outfile_FSA_graphics_name) 
     

    #------------------------------------------------------------------------------#
    #------------------------------------------------------------------------------#
    #        User inquiries about morphology
    #------------------------------------------------------------------------------#
    #------------------------------------------------------------------------------#

    #morphology_copy = morphology.MakeCopy()

    #class parseChunk:
    #    def __init__(self, morph, rString, edge= None):
    #        self.morph         = morph
    #        self.edge         = edge
    #        self.remainingString     = rString
    #        if (edge):
    #            self.fromState = self.edge.fromState
    #            self.toState   = self.edge.toState
    #        else:
    #            self.fromState = None
    #            self.toState = None
    #    def Copy (self, otherChunk):
    #        self.morph         = otherChunk.morph
    #        self.edge         = otherChunk.edge
    #        self.remainingString     = otherChunk.remainingString

    #initialParseChain = list()
    #CompletedParses = list()
    #IncompleteParses = list()
    #word = "" 
    #while True:
    #    word = raw_input('Inquiry about a word: ')
    #    if word == "exit":
    #        break
    #    if word == "State":
    #        while True:
    #            stateno = raw_input("State number:")
    #            if stateno == "" or stateno == "exit":
    #                break
    #            stateno = int(stateno)    
    #            for state in morphology.States:
    #                if state.index == stateno:
    #                    break    
    #            state = morphology.States[stateno]
    #            for edge in state.getOutgoingEdges():
    #                print "Edge number", edge.index 
    #                i = 0
    #                for morph in edge.labels:
    #                    print "%12s" % morph,
    #                    i+=1
    #                    if i%6 == 0: print 
    #            print "\n\n"        
    #            continue
    #    if word == "Edge":
    #        while True:
    #            edgeno = raw_input("Edge number:")
    #            if edgeno == "" or edgeno == "exit":
    #                break
    #            edgeno = int(edgeno)
    #            for edge in morphology.Edges:
    #                if edge.index == edgeno:
    #                    break
    #            print "From state", morphology.Edges[edgeno].fromState.index, "To state", morphology.Edges[edgeno].toState.index
    #            for edge in morphology.Edges:
    #                if edge.index == int(edgeno):
    #                    morphlist = list(edge.labels)
    #            for i in range(len( morphlist )):
    #                print "%12s" % morphlist[i],
    #                if i%6 == 0:
    #                    print    
    #            print "\n\n"
    #            continue
    #    if word == "graph":
    #        while True:
    #            stateno = raw_input("Graph state number:")
    #            
    #    del CompletedParses[:]
    #    del IncompleteParses[:]
    #    del initialParseChain[:]
    #    startingParseChunk = parseChunk("", word)
    #    startingParseChunk.toState = morphology.startState

    #    initialParseChain.append(startingParseChunk)
    #    IncompleteParses.append(initialParseChain)
    #    while len(IncompleteParses) > 0 :
    #        CompletedParses, IncompleteParses = morphology.lparse(CompletedParses, IncompleteParses)
    #    if len(CompletedParses) == 0: print "no analysis found." 
    #     
    #    for parseChain in CompletedParses:
    #        for thisParseChunk in  parseChain:            
    #            if (thisParseChunk.edge):                 
    #                print "\t",thisParseChunk.morph,  
    #        print 
    #    print

    #    for parseChain in CompletedParses:
    #        print "\tStates: ",
    #        for thisParseChunk in  parseChain:            
    #            if (thisParseChunk.edge):                 
    #                print "\t",thisParseChunk.fromState.index, 
    #        print "\t",thisParseChunk.toState.index      
    #    print 

    #    for parseChain in CompletedParses:
    #        print "\tEdges: ",
    #        for thisParseChunk in  parseChain:            
    #            if (thisParseChunk.edge):                 
    #                print "\t",thisParseChunk.edge.index,
    #        print
    #    print "\n\n"



    #---------------------------------------------------------------------------------------------------------------------------#
    # We create a list of words, each word with its signature transform (so DOGS is turned into NULL.s_s, for example)

    if True:
        printWordsToSigTransforms(SigToStems, WordToSig, StemCounts, SigTransforms_outfile, g_encoding, FindSuffixesFlag)
     

    #---------------------------------------------------------------------------------------------------------------------------#  
    #---------------------------------------------------------------------------------#    
    #    Close output files
    #---------------------------------------------------------------------------------# 
      
    FSA_outfile.close()
    Signatures_outfile.close() 
    SigTransforms_outfile.close() 


    #---------------------------------------------------------------------------------#    
    #    Logging information
    #---------------------------------------------------------------------------------# 

    localtime = time.asctime( time.localtime(time.time()) )
    print("Local current time :", localtime)

    numberofwords = len(wordlist)
    logfilename = outfolder + "logfile.txt"
    logfile = open (logfilename,"a")

    print(outfile_Signatures_name.ljust(60),
          '%30s wordcount: %8d data source:' %(localtime, numberofwords ),
          infilename.ljust(50), file=logfile)

if __name__ == "__main__":
    main(sys.argv)
