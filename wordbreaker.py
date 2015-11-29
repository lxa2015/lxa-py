#!/usr/bin/env python3

# Word segmentation
# John Goldsmith 2014-

# code refactoring/optimization in progress, Jackson Lee, 7/6/2015

# audrey  08/2015
# TODO: In ReadBrokenCorpus(), separate additional punctuation marks from preceding word. e.g. comma


import os
import math
import argparse
import sys
import json
import jsonpickle
from pathlib import Path
import copy

import time
import datetime

from latexTable_py3 import MakeLatexTable
from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix, stdout_list,
                     load_config_for_command_line_help)




def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="This program segments unbroken text into words.\n\n{}"
                    .format(configtext),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--config", help="configuration filename",
                        type=str, default=configfilename)

    parser.add_argument("--ibase", help="iterative processing for this run will start at iteration # (ibase+1); use '0' for fresh start.",
                        type=int, default=None)
    parser.add_argument("--itarget", help="last iteration to perform in this run;\n thus # cycles = itarget - ibase",
                        type=int, default=None)
    parser.add_argument("--statefile", help="jsonpickle file needed to restore previous state in order to resume processing; not needed if ibase==0",
                type=str, default=None)
    parser.add_argument("--candidates", help="number of candidates per iteration",
                        type=int, default=25)
    parser.add_argument("--corpuslinestoread", help="number of lines to read in from corpus (defaults to 'sys.maxsize' to read entire corpus)",
                        type=int, default=sys.maxsize)
    parser.add_argument("--verbose", help="verbose output",
                        type=bool, default=False)

    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)

    return parser


class LexiconEntry:
    def __init__(self, key = "", count = 0):
        self.m_Key = key
        self.m_Count = count
        self.m_Frequency= 0.0
        self.m_ParentWords = list()
        self.m_ChildWords = list()
        self.m_Suffix = False
        self.m_Stem = False
        self.m_CountRegister = list()


    def UpdateRegister(self, current_iteration):
        if len(self.m_CountRegister) > 0:
            last_count = self.m_CountRegister[-1][1]
            if self.m_Count != last_count or self.m_ChildWords != []:
                self.m_CountRegister.append((current_iteration, self.m_Count, self.m_ChildWords))
        else:
            self.m_CountRegister.append((current_iteration, self.m_Count, self.m_ChildWords))
        #self.m_Count = 0


    def Display(self, outfile):
        print(self.m_Key, "   ", "{:.7f}".format(self.m_Frequency), "   ", "{:.7f}".format(-1* math.log(self.m_Frequency, 2)), file = outfile)
        if len(self.m_ParentWords) > 0:
            expression = "/".join( self.m_ParentWords )
            #print("expression is ", expression)
            print("%s" % ("{:<}".format(expression)), file=outfile)

        for (iteration_number, count, childwords) in self.m_CountRegister:
                if childwords == []:
                    #print("{0:6}".format(iteration_number), " ",  "{0:10}".format(count), file=outfile)
                    print("%6i %10s" % (iteration_number, "{:,}".format(count)), file=outfile)
                else:
                    #print("{0:6}".format(iteration_number), " ",  "{0:10}".format(count), ":<".format(childwords), file=outfile)
                    print("%6i %10s    %-100s" % (iteration_number, "{:,}".format(count),  childwords), file=outfile)

# ---------------------------------------------------------#
class Lexicon:
    def __init__(self):
        self.m_LetterPlog = dict()
        self.m_EntryDict = dict()
        self.m_TrueDictionary = dict()
        self.m_DictionaryCost = 0   #in bits!
        self.m_Corpus     = list()
        self.m_SizeOfLongestEntry = 0
        self.m_CorpusCost = 0.0
        self.m_ParsedCorpus = list()
        self.m_NumberOfHypothesizedRunningWords = 0
        self.m_NumberOfTrueRunningWords = 0
        self.m_BreakPointList = list()
        self.m_DeletionList = list()  # these are the words that were nominated and then not used in any line-parses *at all*.
        self.m_DeletionDict = dict()  # They never stop getting nominated.
        self.m_Break_based_RecallPrecisionHistory = list()
        self.m_Token_based_RecallPrecisionHistory = list()
        self.m_Type_based_RecallPrecisionHistory = list()
        self.m_DictionaryCostHistory = list()
        self.m_CorpusCostHistory = list()

    # ---------------------------------------------------------#  
    #def AddEntry(self,key,count):
    #    this_entry = LexiconEntry(key,count)
    #    self.m_EntryDict[key] = this_entry
    #    if len(key) > self.m_SizeOfLongestEntry:
    #        self.m_SizeOfLongestEntry = len(key)
    # ---------------------------------------------------------#
    def AddEntry(self,key,new_entry):    #was AddEntry(self,key,count)
        #this_entry = LexiconEntry(key,count)
        self.m_EntryDict[key] = copy.deepcopy(new_entry)
        if len(key) > self.m_SizeOfLongestEntry:
            self.m_SizeOfLongestEntry = len(key)
        return self.m_EntryDict[key]
    # ---------------------------------------------------------#

    # Found bug here July 5 2015: important, don't let it remove a singleton letter! John
    # don't del key-value pairs within still iterating through the pairs among the dict; fix by John Goldsmith July 6 2015
    def FilterZeroCountEntries(self, outfile):
        TempDeletionList = list()
        for key, entry in self.m_EntryDict.items():
            if len(key) == 1 and entry.m_Count==0:
                entry.m_Count = 1
                continue
            if len(key)>1 and entry.m_Count == 0:   # DO WE REALLY WANT TO DISALLOW ITS USE FOR THE FUTURE?
                # Transfer this entry from the EntryDict to the DeletionDict (Keep a list but don't delete yet!)
                TempDeletionList.append(key)
                self.m_DeletionDict[key] = entry

        for key in TempDeletionList:
            del self.m_EntryDict[key]
            print("---> Deleted ", key)
            print("---> Deleted ", key, file=outfile)

    # ---------------------------------------------------------#
    def UpdateLexEntryRegisters(self, iteration_number):
        for key, entry in self.m_EntryDict.items():
            entry.UpdateRegister(iteration_number)
    # ---------------------------------------------------------#


    #-------------------------------------------------------#
    #  Populate data structures for corpus and dictionary.  #
    #  Record truth for measuring performance.              #
    #  Compute initial values for metrics.                  #
    #-------------------------------------------------------#
    def ReadBrokenCorpus(self, infilepathname, outfile, howmuchcorpus):
        print("Name of data file: ", infilepathname)
        if not os.path.isfile(infilepathname):  # Note: already checked at startup by get_language_corpus_datafolder()
            print("Warning:", infilepathname, "does not exist.")
            print("Check file paths and names.")
            sys.exit()
        infile = open(infilepathname)

        rawcorpus_list = infile.readlines() # bad code if the corpus is very large -- but then we won't use python.
        if howmuchcorpus != "all":
            rawcorpus_list = rawcorpus_list[0:int(howmuchcorpus)]    # 0 <= index < corpuslinestoread
        print("Number of lines read =", len(rawcorpus_list))

        for line in rawcorpus_list:
            this_line = ""
            breakpoint_list_forline = list()

            # Clean up data as desired
            #line = line.lower()
            line = line.replace('.', ' .').replace('?', ' ?')

            line_list = line.split()                           # split line into words
            if len(line_list) <=  1:
                continue
            for word in line_list:                             # by word in line
                self.m_NumberOfTrueRunningWords += 1               # build up TrueDictionary
                if word not in self.m_TrueDictionary:              # build up unbroken line
                    self.m_TrueDictionary[word] = 1                # build up breakpoint list
                else:
                    self.m_TrueDictionary[word] += 1
                this_line += word
                breakpoint_list_forline.append(len(this_line))


            #for letter in line:
            for letter in this_line:                           # by character in unbroken line
                if letter not in self.m_EntryDict:                 # build up dictionary
                    this_entry = LexiconEntry()
                    this_entry.m_Key = letter
                    this_entry.m_Count = 1   #counts occurrences of letter in the corpus
                    self.AddEntry(letter, this_entry)
                else:
                    self.m_EntryDict[letter].m_Count += 1

            self.m_Corpus.append(this_line)                    # by unbroken line
            self.m_BreakPointList.append(breakpoint_list_forline)  # build up unbroken corpus

        print("# " + str(len(self.m_TrueDictionary)) + " distinct words in the original corpus.", file=outfile)   # Goes into outfile header

		#----------------------------#
		
        # AT THIS POINT WE HAVE
            # the data:        m_Corpus         unbroken text
            # the dictionary:  m_EntryDict      initial version, entries for single characters

        # HERE IS THE INITIAL PARSE
        for line in self.m_Corpus:
            self.m_ParsedCorpus.append(list(line))    #Parsing is easy!

        self.m_NumberOfHypothesizedRunningWords = 0
        for (key, entry) in self.m_EntryDict.items():
            self.m_NumberOfHypothesizedRunningWords += entry.m_Count

        # PLOGS
        self.m_CorpusCost = 0.0
        self.m_DictionaryCost = 0.0
        self.m_SizeOfLongestEntry = 1
        self.ComputeDictFrequencies()

        for key, entry in self.m_EntryDict.items():
            this_plog = -1 * math.log(entry.m_Frequency, 2)      # applies to both (a)letter uses in data, AND (b)word uses in current parse
            self.m_LetterPlog[key] = this_plog                   # record it
            self.m_DictionaryCost += this_plog                   # as in (a)
            self.m_CorpusCost += entry.m_Count * this_plog       # as in (b)

            entry.m_CountRegister.append((0, entry.m_Count, []))  # iteration_number, count, childwords  as in UpdateRegister()


        print("\n Startup")
        self.Report(0, outfile)

        infile.close()


# ---------------------------------------------------------#
    def ComputeDictFrequencies(self):
        TotalCount = 0
        for (key, entry) in self.m_EntryDict.items():
            TotalCount += entry.m_Count
        for (key, entry) in self.m_EntryDict.items():
            entry.m_Frequency = entry.m_Count/float(TotalCount)
# ---------------------------------------------------------#
#    # added july 2015 john
#    def ComputeDictionaryLength(self):
#        DictionaryCost = 0
#        for word in self.m_EntryDict:
#            wordlength = 0
#            letters = list(word)
#            for letter in letters:
#                wordlength += self.m_LetterPlog[letter]
#            DictionaryLength += wordlength
#        self.m_DictionaryCost = DictionaryCost
#        self.m_DictionaryCostHistory.append(DictionaryCost)
#
# ---------------------------------------------------------#

    def ParseCorpus(self, current_iteration, outfile):
        self.m_ParsedCorpus = list()
        self.m_CorpusCost = 0.0
        self.m_NumberOfHypothesizedRunningWords = 0

        for word, entry in self.m_EntryDict.items():
            entry.m_Count = 0
        for line in self.m_Corpus:
            parsed_line,bit_cost =     self.ParseWord(line, outfile)
            self.m_ParsedCorpus.append(parsed_line)
            self.m_CorpusCost += bit_cost
            for word in parsed_line:
                self.m_EntryDict[word].m_Count +=1
                self.m_NumberOfHypothesizedRunningWords += 1
# ---------------------------------------------------------#
    def PrintParsedCorpus(self,outfile):
        for line in self.m_ParsedCorpus:
            PrintList(line, outfile)
# ---------------------------------------------------------#
    def ParseWord(self, word, outfile):
        wordlength = len(word)

        Parse=dict()
        Piece = ""
        LastChunk = ""
        BestCompressedLength = dict()
        BestCompressedLength[0] = 0
        CompressedSizeFromInnerScanToOuterScan = 0.0
        LastChunkStartingPoint = 0
        # <------------------ outerscan -----------><------------------> #
        #                  ^---starting point
        # <----prefix?----><----innerscan---------->
        #                  <----Piece-------------->
        if verboseflag: print("\nOuter\tInner", file=outfile)
        if verboseflag: print("scan:\tscan:\tPiece\tFound?", file=outfile)
        for outerscan in range(1,wordlength+1):
            Parse[outerscan] = list()
            MinimumCompressedSize= 0.0
            startingpoint = 0
            if outerscan > self.m_SizeOfLongestEntry:
                startingpoint = outerscan - self.m_SizeOfLongestEntry
            for innerscan in range(startingpoint, outerscan):
                if verboseflag: print("\n %3s\t%3s  " % (outerscan, innerscan), end=" ", file=outfile)
                Piece = word[innerscan: outerscan]
                if verboseflag: print(" %5s"% Piece, end=" ", file=outfile)
                if Piece in self.m_EntryDict:
                    if verboseflag: print("   %5s" % "Yes.", end=" ", file=outfile)
                    CompressedSizeFromInnerScanToOuterScan = -1 * math.log( self.m_EntryDict[Piece].m_Frequency, 2)
                    newvalue =  BestCompressedLength[innerscan]  + CompressedSizeFromInnerScanToOuterScan
                    if verboseflag: print(" %7.3f bits" % (newvalue), end=" ", file=outfile)
                    if  MinimumCompressedSize == 0.0 or MinimumCompressedSize > newvalue:
                        MinimumCompressedSize = newvalue
                        LastChunk = Piece
                        LastChunkStartingPoint = innerscan
                        if verboseflag: print(" %7.3f bits" % (MinimumCompressedSize), end=" ", file=outfile)
                else:
                    if verboseflag: print("   %5s" % "No. ", end=" ", file=outfile)
            BestCompressedLength[outerscan] = MinimumCompressedSize
            if LastChunkStartingPoint > 0:
                Parse[outerscan] = list(Parse[LastChunkStartingPoint])
            else:
                Parse[outerscan] = list()
            if verboseflag: print("\n\t\t\t\t\t\t\t\tchosen:", LastChunk, end=" ", file=outfile)
            Parse[outerscan].append(LastChunk)
        if verboseflag:
            PrintList(Parse[wordlength], outfile)
        bitcost = BestCompressedLength[outerscan]
        return (Parse[wordlength],bitcost)
# ---------------------------------------------------------#
    def GenerateCandidates_standardmethod(self, current_iteration, howmany, outfile):
            # m_ChildWords (for display from the CountRegister at this iteration only) are set in this function
            for word, lexicon_entry in self.m_EntryDict.items():
                    lexicon_entry.m_ChildWords = []

            CandidateDict = dict()      # key is the new word, value is a LexiconEntry object
            NomineeList = list()
            for parsed_line in self.m_ParsedCorpus:
                for wordno in range(len(parsed_line)-1):
                    word0 = parsed_line[wordno]
                    word1 = parsed_line[wordno + 1]
                    candidate = word0 + word1
                    if candidate in self.m_EntryDict:
                        continue
                    if candidate in CandidateDict:
                        CandidateDict[candidate].m_Count += 1
                    else:
                        this_entry = LexiconEntry(candidate)
                        this_entry.m_Count = 1
                        this_entry.m_ParentWords = [word0, word1]
                        CandidateDict[candidate] = this_entry

            SortableCandidateDict = dict()
            for candidate, lex_entry in CandidateDict.items():
                SortableCandidateDict[candidate] = lex_entry.m_Count
            EntireCandidateList = sorted(SortableCandidateDict.items(),key=lambda x:x[1], reverse=True)

            #print("\nIn GenerateCandidates - issue is ties")
            ThisCount = 0
            for candidate, count in EntireCandidateList:
                #print("candidate = ", candidate)
                if candidate in self.m_DeletionDict:
                    continue

                PreviousCount = ThisCount
                ThisCount = CandidateDict[candidate].m_Count
                #print("PreviousCount = ", PreviousCount, "  ThisCount = ", ThisCount)
                NomineeList.append((candidate, CandidateDict[candidate]))
                #print("howmany = ", howmany,  "  length of NomineeList: ", len(NomineeList))
                if len(NomineeList) > howmany:
                    if ThisCount == PreviousCount:
                        howmany += 1
                        #print("Keep the new nominee; increase howmany to: ", howmany)
                    else:
                        NomineeList = NomineeList[0:-1]
                        #print("Drop the new nominee; shortened NomineeList to: ", len(NomineeList))
                        #print()
                        break

            print("Nominees:")
            latex_data= list()
            latex_data.append("piece   count   parent0    parent1   status")
            for nominee, entry in NomineeList:
                # for the new word
                entry.m_CountRegister.append((current_iteration, entry.m_Count, []))  # as in UpdateRegister()
                self.AddEntry(nominee,entry)                                           # This records the initial count--before parsing.
                                                                                          # If the actual count used in the parse differs,
                                                                                          # both records will appear for this iteration in the CountRegister.
                # for the trace
                for word in entry.m_ParentWords:
                    self.m_EntryDict[word].m_ChildWords.append(nominee)  #will go into m_CountRegister to display along with changed counts

                # for display
                expr = ""
                for x in entry.m_ParentWords:
                    expr = expr + "%12s" % (x)
                print("%15s  %10s %-50s" % (nominee, '{:,}'.format(entry.m_Count), expr))
                latex_data.append(nominee +  "\t" + '{:,} {}'.format(entry.m_Count, expr) )

            MakeLatexTable(latex_data,outfile)

            return NomineeList      # NOTE THAT THE RETURN VALUE IS NOT USED 

    # ---------------------------------------------------------#
#   def GenerateCandidates_suffixmethod(self):      # Similar to GenerateCandidates() [renamed as GenerateCandidates_standardmethod]
#
#       # Take in the suffixes from Linguistica
#       suffix_infile_name  = "Corpus" + str(current_iteration - 1) + "_1_Mini1_Suffixes.txt"
#       suffix_outfile_name = "Corpus" + str(current_iteration - 1) + ".Suffixes_extracted.txt"
#       suffixList = this_lexicon.ExtractListFromLing413File(suffix_infile_name, suffix_outfile_name, 0)
#       suffixList.sort()
#       #this_lexicon.AddSuffixMark(suffixList)   # PUT THIS IN WHEN VERSION HAS m_Suffix
#       print "Suffix List from", suffix_infile_name
#       for suffix in suffixList:
#           print suffix
#
#
#       # Create a dictionary of potential words
#       SuffixedCandidateDict = dict()              # similar to CandidateDict
#       for parsed_line in self.m_ParsedCorpus:
#           for wordno in range(len(parsed_line)-1):
#                   word0 = parsed_line[wordno]
#                   word1 = parsed_line[wordno + 1]
#                   # if self.m_EntryDict[word1].m_Suffix == True:     # PUT THIS IN WHEN VERSION HAS m_Suffix
#                   if suffixList.count(word1) > 0:    # Use this line when running LinkPrevious
#                   #if suffixList.count(word0) > 0:    # Use this line when running LinkFollowing
#                   suffixed_candidate = word0 + word1
#                   if suffixed_candidate in self.m_EntryDict:
#                       continue
#                   if suffixed_candidate in SuffixedCandidateDict:
#                       SuffixedCandidateDict[suffixed_candidate].m_ParseCount += 1
#                   else: # add it
#                       suffixed_entry = LexiconEntry(suffixed_candidate)
#                       suffixed_entry.m_ParseCount = 1
#                       suffixed_entry.m_Subwords = [word0, word1]
#                       SuffixedCandidateDict[suffixed_candidate] = suffixed_entry
#
#
#       # Behind the scenes, try a parse with these additional words
#       # to distinguish false suffixes and exclude unlikely formations
#       temp_lexicon = copy.deepcopy(self)
#       for candidate, entry in SuffixedCandidateDict.iteritems():
#           temp_lexicon.AddEntry(candidate, entry)
#
#       temp_lexicon.ComputeDictFrequencies()
#       temp_lexicon.ParseCorpus (current_iteration, outfile)   # (no actual print to outfile occurs)
#
#
#       # Compare counts from before and after the parse  (increase is good!)
#       DeltaByWord = dict()
#       for key, entry in SuffixedCandidateDict.iteritems():
#           BeforeParseCount = entry.m_ParseCount
#               AfterParseCount = temp_lexicon.m_EntryDict[key].m_ParseCount
#               DeltaByWord[key]  = AfterParseCount - BeforeParseCount
#
#       WordListOrderedByDelta = sorted(DeltaByWord.iteritems(),key=operator.itemgetter(1), reverse=True)
#
#       if True:            # OUTPUT COUNTS TO A FILE - CAN BE STUDIED IN EXCEL
#           i = datetime.datetime.now()
#           timelabel = "%s_%s_%s.%s%s" % (i.year, i.month, i.day, i.hour, i.minute)
#           counts_outfilename = "WordDeltaCounts_" + str(current_iteration)+"." + timelabel + ".txt"
#           counts_outfile = open(counts_outfilename, "w")
#           print >> counts_outfile, "     SuffixedCandidate      Before       After     Subword0    Subword1        Delta"
#           for key, delta in WordListOrderedByDelta:
#               expr = ""
#               for x in SuffixedCandidateDict[key].m_Subwords:
#                       expr = expr + "%12s" % (x)
#               print >> counts_outfile, "%22s  %10s  %10s %-30s  %5s" % \
#               (key, \
#               '{:,}'.format(SuffixedCandidateDict[key].m_ParseCount),        # BeforeParseCount \
#               '{:,}'.format(temp_lexicon.m_EntryDict[key].m_ParseCount),     # AfterParseCount  \
#               expr, '{:,}'.format(delta))
#           counts_outfile.close()
#
#
#       # COLLECT AND OUTPUT DELTA INFO BY SUFFIX
#       MiddleBandLimit = 1   # SET THIS
#       if MiddleBandLimit == 0:
#           NegMidBandLimit = -1
#       else:
#           NegMidBandLimit = -1 * MiddleBandLimit
#
#       # COLLECT
#       # The quantities below are accumulated per suffix based on delta values of the words formed on that suffix.
#       CountPosDeltas  = dict()    # how many words formed on given suffix have a positive delta
#       CountNegDeltas  = dict()
#       CountZeroDeltas = dict()
#
#       SumPosDeltas = dict()       # sum of their delta values
#       SumNegDeltas = dict()
#
#       for suffix in suffixList:
#           CountPosDeltas[suffix]  = 0
#           CountNegDeltas[suffix]  = 0
#           CountZeroDeltas[suffix] = 0
#
#           SumPosDeltas[suffix] = 0
#           SumNegDeltas[suffix] = 0
#
#       for key, delta in WordListOrderedByDelta:
#           suffix = SuffixedCandidateDict[key].m_Subwords[1]
#
#           if delta >= MiddleBandLimit:
#               CountPosDeltas[suffix] += 1
#               SumPosDeltas[suffix] += delta
#           elif delta <= NegMidBandLimit:
#               CountNegDeltas[suffix] += 1
#               SumNegDeltas[suffix] += delta
#           else:
#               CountZeroDeltas[suffix] +=1
#
#       # OUTPUT
#       # LOOKING FOR USEFUL PATTERNS; MOST LIKELY THIS IS NOT THE FINAL FORM
#       suffixstats_outfilename = "SuffixDeltaStats_"  + str(MiddleBandLimit) + "_" + str(current_iteration) + "." + timelabel + ".txt"
#       suffixstats_outfile = open(suffixstats_outfilename, "w")
#       print >> suffixstats_outfile, "  Suffix    #Pos    #Neg   #Zero    #All  SumPos  SumNeg  DeltaTotal    PNRatio     ROI"
#
#       CountAllDeltas = dict()
#       DeltaTotal = dict()
#       PosNegRatio = dict()
#       ROI = dict()
#       for suffix in suffixList:
#           CountAllDeltas[suffix] = CountPosDeltas[suffix] + CountNegDeltas[suffix] + CountZeroDeltas[suffix]
#           DeltaTotal[suffix] = SumPosDeltas[suffix] + SumNegDeltas[suffix]
#
#           if CountAllDeltas[suffix] != 0:
#               ROI[suffix] = float(DeltaTotal[suffix]) / CountAllDeltas[suffix]
#           else:
#               ROI[suffix] = 0
#
#           if SumNegDeltas[suffix] != 0:
#               PosNegRatio[suffix] = float(SumPosDeltas[suffix]) / abs(SumNegDeltas[suffix])
#           else:
#               PosNegRatio[suffix] = SumPosDeltas[suffix]
#           # may also decide to output an average over something or things tbd
#
#           print >> suffixstats_outfile, "%8s  %6s  %6s  %6s  %6s  %6s  %6s  %9s  %9s  %8s"  %  \
#               (suffix, \
#               '{:,}'.format(CountPosDeltas[suffix]),        \
#               '{:,}'.format(CountNegDeltas[suffix]),        \
#               '{:,}'.format(CountZeroDeltas[suffix]),       \
#               '{:,}'.format(CountAllDeltas[suffix]),        \
#               '{:,}'.format(SumPosDeltas[suffix]),          \
#               '{:,}'.format(SumNegDeltas[suffix]),          \
#               '{:,}'.format(DeltaTotal[suffix]),            \
#               '{:,.2f}'.format(PosNegRatio[suffix]),        \
#               '{:,.2f}'.format(ROI[suffix]))
#
#       suffixstats_outfile.close()
#
#
#
#       # SET UP A USEFUL DATA STRUCTURE
#       FromSuffixToWords = dict()    # key - suffix
#       for suffix in suffixList:     # value - list of (word, delta) pairs for that suffix, listed by delta in descending order
#           FromSuffixToWords[suffix] = []
#
#       for key, delta in WordListOrderedByDelta:
#           this_suffix = SuffixedCandidateDict[key].m_Subwords[1]
#           FromSuffixToWords[this_suffix].append((key, delta))
#
#
#       # FOR EACH SUFFIX, SET A THRESHOLD BASED ON DELTA PROPERTIES FOR WHICH OF ITS
#       # ASSOCIATED WORDS SHOULD GO INTO THE LEXICON
#       Cutoff = dict()  # Key: proposed suffix
#                        # Value: minimum delta for a word in its list to qualify for the lexicon
#
#       # These parameters must be set; so far they look OK for English.
#       DeltaTotalLimit = 1
#       PosNegRatioLimit = 1.9
#       ROILimit = .1
#       DefaultWordDeltaLimit = 1    # This is the standard expectation for words formed on a real suffix.
#
#       for suffix in FromSuffixToWords:
#           if DeltaTotal[suffix] < DeltaTotalLimit:    # Clearly a false suffix! Don't admit any word from its list.
#               Cutoff[suffix] = sys.maxsize
#
#           elif PosNegRatio[suffix] < PosNegRatioLimit:    # May or may not be a real suffix, but likely that many items
#               Cutoff[suffix] = sys.maxsize        # in its list are not real stem+suffix formations.
#
#           elif ROI[suffix] < ROILimit:            # similar to preceding case
#               Cutoff[suffix] = sys.maxsize
#
#           elif (CountPosDeltas[suffix] < CountNegDeltas[suffix] and \
#               CountNegDeltas[suffix] < CountZeroDeltas[suffix]):     # Probably a real suffix, but this property indicates
#               Cutoff[suffix] = DefaultWordDeltaLimit + 1             # that more bad formations occur.
#
#           else:
#               Cutoff[suffix] = DefaultWordDeltaLimit  # A real, well-behaved suffix!
#
#       if True:
#           print >> outfile, "Cutoff values for suffixed words:"
#           for suffix in suffixList:
#               print >> outfile, "%8s  %8s" % \
#               (suffix, '{:,}'.format(Cutoff[suffix]))
#
#
#       # THIS IS THE GOAL OF ALL THE PRECEDING WORK
#       # Add qualified suffixed candidates to the lexicon
#       NomineeList = list()
#       latex_data= list()
#       latex_data.append("piece   count   subword    subword")
#
#       for suffix in FromSuffixToWords:
#           for (word, delta) in FromSuffixToWords[suffix]:
#               if delta >= Cutoff[suffix]:
#                   admitted_entry = self.AddEntry(word, temp_lexicon.m_EntryDict[word])   # Use expected count for this initial, pre-parse entry
#                   NomineeList.append((word, admitted_entry))
#
#                   # for the trace
#                   admitted_entry.m_CountRegister.append((current_iteration, admitted_entry.m_ParseCount, 0, []))  # as in UpdateRegister()
#                   for subword in admitted_entry.m_Subwords:
#                       self.m_EntryDict[subword].m_ReprCount += 1
#                               self.m_EntryDict[subword].m_Extwords.append(word)
#                               self.m_EntryDict[subword].m_NewExtwords.append(word)  #will go into this word's m_CountRegister to display along with changed counts
#
#                   # for display
#                       expr = ""
#                       for subword in admitted_entry.m_Subwords:
#                           expr = expr + "%12s" % (subword)
#                   print "%22s %8s %8s   %-50s" % (word,  '{:,}'.format(delta), '{:,}'.format(admitted_entry.m_ParseCount), expr)
#                   latex_data.append(word +  "\t" + '{:,} {}'.format(admitted_entry.m_ParseCount, expr) )
#                   # DESIRABLE TO DISPLAY DELTA -- NEED HELP MAKING IT WORK!
#
#               else:
#                   break    # deltas are descending, so go on to the next suffix
#
#       MakeLatexTable(latex_data,outfile)
#
#       return NomineeList      # NOTE THAT THE RETURN VALUE IS NOT USED  # July 18, 2015 - Now used to update DictionaryCost
#
#
# ---------------------------------------------------------#
    def Expectation(self):
        self.m_NumberOfHypothesizedRunningWords = 0
        for this_line in self.m_Corpus:
            wordlength = len(this_line)
            ForwardProb = dict()
            BackwardProb = dict()
            Forward(this_line,ForwardProb)
            Backward(this_line,BackwardProb)
            this_word_prob = BackwardProb[0]

            if WordProb > 0:
                for nPos in range(wordlength):
                    for End in range(nPos, wordlength-1):
                        if End- nPos + 1 > self.m_SizeOfLongestEntry:
                            continue
                        if nPos == 0 and End == wordlength - 1:
                            continue
                        Piece = this_line[nPos, End+1]
                        if Piece in self.m_EntryDict:
                            this_entry = self.m_EntryDict[Piece]
                            CurrentIncrement = ((ForwardProb[nPos] * BackwardProb[End+1])* this_entry.m_Frequency ) / WordProb
                            this_entry.m_Count += CurrentIncrement
                            self.m_NumberOfHypothesizedRunningWords += CurrentIncrement



# ---------------------------------------------------------#
    def Maximization(self):
        for entry in self.m_EntryDict:
            entry.m_Frequency = entry.m_Count / self.m_NumberOfHypothesizedRunningWords

# ---------------------------------------------------------#
    def Forward (self, this_line,ForwardProb):
        ForwardProb[0]=1.0
        for Pos in range(1,Length+1):
            ForwardProb[Pos] = 0.0
            if (Pos - i > self.m_SizeOfLongestEntry):
                break
            Piece = this_line[i,Pos+1]
            if Piece in self.m_EntryDict:
                this_Entry = self.m_EntryDict[Piece]
                vlProduct = ForwardProb[i] * this_Entry.m_Frequency
                ForwardProb[Pos] = ForwardProb[Pos] + vlProduct
        return ForwardProb

# ---------------------------------------------------------#
    def Backward(self, this_line,BackwardProb):

        Last = len(this_line) -1
        BackwardProb[Last+1] = 1.0
        for Pos in range( Last, Pos >= 0,-1):
            BackwardProb[Pos] = 0
            for i in range(Pos, i <= Last,-1):
                if i-Pos +1 > m_SizeOfLongestEntry:
                    Piece = this_line[Pos, i+1]
                    if Piece in self.m_EntryDict[Piece]:
                        this_Entry = self.m_EntryDict[Piece]
                        if this_Entry.m_Frequency == 0.0:
                            continue
                        vlProduct = BackwardProb[i+1] * this_Entry.m_Frequency
                        BackwardProb[Pos] += vlProduct
        return BackwardProb


# ---------------------------------------------------------#
    def PrintLexicon(self, outfile):
        print("\n\nLEXICON with trace information", file=outfile)
        for key in sorted(self.m_EntryDict.keys()):
            self.m_EntryDict[key].Display(outfile)

        print("\n\nDELETIONS", file=outfile)
        for key in self.m_DeletionDict:
            self.m_DeletionDict[key].Display(outfile)

# ---------------------------------------------------------#
    def RecallPrecision(self, iteration_number, outfile):

        # the following calculations are precision and recall *for breaks* (not for morphemes)
        total_true_positive_for_break = 0

        for linenumber in range(len(self.m_BreakPointList)):
            truth = self.m_BreakPointList[linenumber]
            if len(truth) < 2:     #NOTE There are 10 such lines in brown-english.txt
                print("Skipping this line:", self.m_Corpus[linenumber], file=outfile)
                continue
            hypothesis = list()
            hypothesis_line_length = 0
            for piece in self.m_ParsedCorpus[linenumber]:    # NOTE audrey 2015_08_23
                hypothesis_line_length += len(piece)         #  This could be constructed in ParseCorpus() and stored in Lexicon.
                hypothesis.append(hypothesis_line_length)    #  Analogous to m_BreakPointList  (and m_NumberOfTrueRunningWords).
            #number_of_hypothesized_words = len(hypothesis)  #  (We already store m_NumberOfHypothesizedRunningWords.)

            true_positive_for_break = len(set(hypothesis).intersection(set(truth)))
            #if linenumber == 86:
                #print("For linenumber ", linenumber, " len(truth) =", len(truth), "BUT true_positive_for_break =", true_positive_for_break)
                #print("truth is ", truth)
                #print("hypothesis is ", hypothesis)
            total_true_positive_for_break += true_positive_for_break

        total_break_precision = float(total_true_positive_for_break) /  self.m_NumberOfHypothesizedRunningWords
        total_break_recall    = float(total_true_positive_for_break) /  self.m_NumberOfTrueRunningWords
        self.m_Break_based_RecallPrecisionHistory.append((iteration_number,  total_break_precision,total_break_recall))

        formatstring = "%16s %12s %6.4f %9s %6.4f"
        print()
        print(formatstring %( "Break based word", "precision", total_break_precision, "recall", total_break_recall))
        print(formatstring %( "Break based word", "precision", total_break_precision, "recall", total_break_recall), file=outfile)


        # Token_based precision for word discovery:

        if (True):
            true_positives = 0
            for (word, this_words_entry) in self.m_EntryDict.items():
                if word in self.m_TrueDictionary:
                    true_count = self.m_TrueDictionary[word]
                    these_true_positives = min(true_count, this_words_entry.m_Count)
                else:
                    these_true_positives = 0
                true_positives += these_true_positives

            word_recall = float(true_positives) / self.m_NumberOfTrueRunningWords
            word_precision = float(true_positives) / self.m_NumberOfHypothesizedRunningWords
            self.m_Token_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))

            print(formatstring %( "Token_based word", "precision", word_precision, "recall", word_recall), file=outfile)
            print(formatstring %( "Token_based word", "precision", word_precision, "recall", word_recall))


        # Type_based precision for word discovery:

        if (True):
            true_positives = 0
            for (word, this_words_entry) in self.m_EntryDict.items():
                if word in self.m_TrueDictionary:
                    true_positives +=1

            word_recall = float(true_positives) / len(self.m_TrueDictionary)
            word_precision = float(true_positives) / len(self.m_EntryDict)
            self.m_Type_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))

            #print >>outfile, "\n\n***\n"
            #print "Type_based Word Precision  %6.4f; Word Recall  %6.4f" %(word_precision ,word_recall)
            print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall), file=outfile)
            print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall))


# ---------------------------------------------------------#
    def RecallPrecision_do_not_use(self, iteration_number, outfile):      # break-based calculation is simplified in version above

        print("Now at top of RecallPrecision function")
        print("linenumber = ", iteration_number)            #just to get a few specific lines - has nothing to do with iteration itself
        print("Here is self.m_BreakPointList[linenumber]    ", self.m_BreakPointList[iteration_number])
        print("Its length is ", len(self.m_BreakPointList[iteration_number]))
        truth = list(self.m_BreakPointList[iteration_number])
        print("Here is truth   ", truth)
        print("Length of truth is ", len(truth))
        print("\n\n")

        total_true_positive_for_break = 0
        total_number_of_hypothesized_words = 0
        total_number_of_true_words = 0
        for linenumber in range(len(self.m_BreakPointList)):
            truth = list(self.m_BreakPointList[linenumber])
            if len(truth) < 2:
                print("Skipping this line:", self.m_Corpus[linenumber], file=outfile)
                continue
            #number_of_true_words = len(truth) -1   #No--For the beginning line, for example, there are 23 words, counting '.' as a separate word. And len(truth) = 23.
            number_of_true_words = len(truth)
            hypothesis = list()
            hypothesis_line_length = 0
            accurate_word_discovery = 0
            true_positive_for_break = 0
            word_too_big = 0
            word_too_small = 0
            real_word_lag = 0
            hypothesis_word_lag = 0

            for piece in self.m_ParsedCorpus[linenumber]:    # NOTE audrey 2015_08_23
                hypothesis_line_length += len(piece)         #  This could be constructed in ParseCorpus() and stored in Lexicon.
                hypothesis.append(hypothesis_line_length)    #  We already store m_NumberOfHypothesizedRunningWords.
            number_of_hypothesized_words = len(hypothesis)   #  Analogous to m_BreakPointList  and  m_NumberOfTrueRunningWords.
            if linenumber == iteration_number:
                print("hypothesis = ", hypothesis)

            # state 0: at the last test, the two parses were in agreement
            # state 1: at the last test, truth was # and hypothesis was not
            # state 2: at the last test, hypothesis was # and truth was not
            pointer = 0
            state = 0
            while (len(truth) > 0 and len(hypothesis) > 0):

                next_truth = truth[0]
                next_hypothesis  = hypothesis[0]
                if state == 0:
                    real_word_lag = 0
                    hypothesis_word_lag = 0

                    if next_truth == next_hypothesis:
                        pointer = truth.pop(0)
                        hypothesis.pop(0)
                        true_positive_for_break += 1
                        accurate_word_discovery += 1
                        state = 0
                    elif next_truth < next_hypothesis:
                        pointer = truth.pop(0)
                        real_word_lag += 1
                        state = 1
                    else: #next_hypothesis < next_truth:
                        pointer = hypothesis.pop(0)
                        hypothesis_word_lag = 1
                        state = 2
                elif state == 1:
                    if next_truth == next_hypothesis:
                        pointer = truth.pop(0)
                        hypothesis.pop(0)
                        true_positive_for_break += 1
                        word_too_big += 1
                        state = 0
                    elif next_truth < next_hypothesis:
                        pointer = truth.pop(0)
                        real_word_lag += 1
                        state = 1 #redundantly
                    else:
                        pointer = hypothesis.pop(0)
                        hypothesis_word_lag += 1
                        state = 2
                else: #state = 2
                    if next_truth == next_hypothesis:
                        pointer = truth.pop(0)
                        hypothesis.pop(0)
                        true_positive_for_break += 1
                        word_too_small +=1
                        state = 0
                    elif next_truth < next_hypothesis:
                        pointer = truth.pop(0)
                        real_word_lag += 1
                        state = 1
                    else:
                        pointer = hypothesis.pop(0)
                        hypothesis_word_lag += 1
                        state =2




            #precision = float(true_positive_for_break) /  number_of_hypothesized_words
            #recall    = float(true_positive_for_break) /  number_of_true_words

            total_true_positive_for_break += true_positive_for_break
            if linenumber == iteration_number:
                print("true_positive_for_break = ", true_positive_for_break)
            total_number_of_hypothesized_words += number_of_hypothesized_words
            total_number_of_true_words += number_of_true_words


        print("Info_RecallPrecision")
        print("iteration_number = ", iteration_number)
        print("total_number_of_true_words = ", total_number_of_true_words)
        print("self.m_NumberOfTrueRunningWords = ", self.m_NumberOfTrueRunningWords)
        print("total_number_of_hypothesized_words = ", total_number_of_hypothesized_words)
        print("self.m_NumberOfHypothesizedRunningWords = ", self.m_NumberOfHypothesizedRunningWords)



        # the following calculations are precision and recall *for breaks* (not for morphemes)

        formatstring = "%16s %12s %6.4f %9s %6.4f"
        total_break_precision = float(total_true_positive_for_break) /  total_number_of_hypothesized_words
        total_break_recall    = float(total_true_positive_for_break) /  total_number_of_true_words

        ### WHY HERE ????
        #self.m_CorpusCostHistory.append( self.m_CorpusCost)   MOVED TO Report()  August 21, 2015

        self.m_Break_based_RecallPrecisionHistory.append((iteration_number,  total_break_precision,total_break_recall))
        print(formatstring %( "Break based word", "precision", total_break_precision, "recall", total_break_recall))
        print(formatstring %( "Break based word", "precision", total_break_precision, "recall", total_break_recall), file=outfile)



        # Token_based precision for word discovery:

        if (True):
            true_positives = 0
            for (word, this_words_entry) in self.m_EntryDict.items():
                if word in self.m_TrueDictionary:
                    true_count = self.m_TrueDictionary[word]
                    these_true_positives = min(true_count, this_words_entry.m_Count)
                else:
                    these_true_positives = 0
                true_positives += these_true_positives
            word_recall = float(true_positives) / self.m_NumberOfTrueRunningWords
            word_precision = float(true_positives) / self.m_NumberOfHypothesizedRunningWords
            self.m_Token_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))

            print(formatstring %( "Token_based Word Precision", word_precision, "recall", word_recall), file=outfile)
            print(formatstring %( "Token_based Word Precision", word_precision, "recall", word_recall))


        # Type_based precision for word discovery:
        if (True):
            true_positives = 0
            for (word, this_words_entry) in self.m_EntryDict.items():
                if word in self.m_TrueDictionary:
                    true_positives +=1
            word_recall = float(true_positives) / len(self.m_TrueDictionary)
            word_precision = float(true_positives) / len(self.m_EntryDict)
            self.m_Type_based_RecallPrecisionHistory.append((iteration_number,  word_precision,word_recall))

            #print >>outfile, "\n\n***\n"
#            print "Type_based Word Precision  %6.4f; Word Recall  %6.4f" %(word_precision ,word_recall)
            print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall), file=outfile)
            print(formatstring %( " Type_based word", "precision", word_precision, "recall", word_recall))

# ---------------------------------------------------------#
    def PrintRecallPrecision(self, itarget, outfile):
        print("\t\t\tBreak\t\tToken-based\t\tType-based", file=outfile)
        print("\t\t\tprecision\trecall\tprecision\trecall\tprecision\trecall", file=outfile)
        for iterno in range(itarget+1):      #was  (range(numberofcycles-1)):
        #for iterno in range(1, numberofcycles+1):  #for the 3 histories, may not be consistent whether start at 0 or 1
            print("printing iterno", iterno)
            (iteration, p1,r1) = self.m_Break_based_RecallPrecisionHistory[iterno]
            (iteration, p2,r2) = self.m_Token_based_RecallPrecisionHistory[iterno]
            (iteration, p3,r3) = self.m_Type_based_RecallPrecisionHistory[iterno]
            cost1 = self.m_DictionaryCostHistory[iterno]  # was int(self.m_DictionaryCostHistory[iterno])
            cost2 = self.m_CorpusCostHistory[iterno]      # was int(self.m_CorpusCostHistory[iterno] )
            #print >>outfile,"%3i\t%8.3f\t%8.3f\t%8.3f\t%8.3f\t%8.3f\t%8.3f" %(iteration, r1,p1,r2,p2,r3,p3)
            print(iteration,"\t",cost1, "\t", cost2, "\t", p1,"\t",r1,"\t",p2,"\t",r2,"\t",p3,"\t",r3, file=outfile)

# ---------------------------------------------------------#
    def ExtendLexicon(self, method, iteration_number, howmany, outfile):
        #TempDeletionList = self.FilterZeroCountEntries(iteration_number)  # DON"T NEED TempDeletionList
        if method == "standard":
            NomineeList = self.GenerateCandidates_standardmethod(iteration_number, howmany, outfile)
        #elif method == "suffix": # if no method specified, no new candidates will be generated
            #NomineeList = self.GenerateCandidates_suffixmethod()

        self.FilterZeroCountEntries(outfile)  # MOVED DOWNWARD.
        self.ComputeDictFrequencies()   # uses Count info from previous parse and GenerateCandidates()

        # COMPUTE DICTIONARY COST - composition-based
        #self.m_LexiconCost = self.m_InitialLexCost
        #for key, entry in self.m_EntryDict.items():
            #self.m_LexiconCost += entry.m_ReprCount *  -1 * math.log(entry.m_Frequency, 2)

        # COMPUTE DICTIONARY COST - letter-based
        #print "Now make sure m_LetterPlog is OK"
        #for key, entry in self.m_LetterPlog.items():
        #   print "key = ", key, "    plog = ", self.m_LetterPlog[key]

        #print "Now in ExtendLexicon: Compute the dictionary cost  letter-based"  # USE THE FUNCTION INSTEAD?
        self.m_DictionaryCost = 0.0
        for word in self.m_EntryDict:
            #print "word = ", word
            letters = list(word)
            for letter in letters:
                self.m_DictionaryCost += self.m_LetterPlog[letter]

        # UPDATE DICTIONARY COST  July 19, 2015: For iters 20, 21, 22, the whole-dictionary calculation is faster
        #for word in TempDeletionList:
        #   letters = list(word)
        #   for letter in letters:
        #       self.m_DictionaryCost -= self.m_LetterPlog[letter]

        #for (word, entry) in NomineeList:
        #   letters = list(word)
        #   for letter in letters:
        #       self.m_DictionaryCost += self.m_LetterPlog[letter]

        #self.m_DictionaryCostHistory.append(self.m_DictionaryCost)   #moved to Report()

# ---------------------------------------------------------#
    def Report(self, iteration_number, outfile):
        # DictionaryCost is calculated in ExtendLexicon(), CorpusCost in ParseCorpus().
        print("Cost: ")
        print("-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost))
        print("-%16s" % 'Dictionary: ',   "{0:18,.4f}".format(self.m_DictionaryCost))
        print("-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_DictionaryCost))

        print("Cost: ", file=outfile)
        print("-%16s" % 'Corpus: ',    "{0:18,.4f}".format(self.m_CorpusCost), file=outfile)
        print("-%16s" % 'Dictionary: ',   "{0:18,.4f}".format(self.m_DictionaryCost), file=outfile)
        print("-%16s" % 'Combined: ',  "{0:18,.4f}".format(self.m_CorpusCost + self.m_DictionaryCost), file=outfile)

        self.m_CorpusCostHistory.append(self.m_CorpusCost)
        self.m_DictionaryCostHistory.append(self.m_DictionaryCost)
        self.RecallPrecision(iteration_number, outfile)
        self.UpdateLexEntryRegisters(iteration_number)


# ---------------------------------------------------------#
def PrintList(my_list, outfile):
    print(file=outfile)
    for item in my_list:
        print(item, end=" ", file=outfile)

# ---------------------------------------------------------#

def LoadSavedStateFromFile(statefile, ibase, itarget):
    if not (itarget > ibase):
        print("\nERROR")
        print("itarget must be an integer greater than ibase.")
        print("Exiting...\n")
        sys.exit()

    if (not os.path.isfile(statefile)):
        print("\nERROR")
        print("The designated statefile, ", statefile, ", does not exist.")
        print("Exiting...\n")
        sys.exit()

    fd = open(statefile, "r")
    lines = fd.readlines()
    fd.close()

    for line in lines:
        if "Last iteration" in line:      #this is 'in' operator
            items = line.split('=')
            iend = int(items[1])
            #print("Found  Last iteration = ", iend)
            if ibase != iend:
                print("\nERROR")
                print("Mismatch between ibase iteration =", ibase, "and last recorded iteration =", iend, "on statefile")
                #print(statefile, "has state information for iteration", str(iend)+",")
                #print("not for ibase iteration", ibase, "as required.")
                print("Exiting...\n")
                sys.exit()
            break

    print("LOADING SAVED STATE...")
    serialstr = lines[-1]
    this_lexicon = jsonpickle.decode(serialstr)
    return this_lexicon



def main(language, corpus, datafolder,
         ibase, itarget, statefile, candidatesperiteration, howmuchcorpus, verboseflag):

    # REQUIRED ARGUMENTS
    if (ibase == None or itarget == None):
        print("\nERROR")
        print("ibase and itarget must be specified, with itarget > ibase >= 0")
        print("Exiting...\n")
        sys.exit()

    if (ibase > 0 and statefile == None):
        print("\nERROR")
        print("To resume processing beyond the ibase iteration, a file specifying the previous state must be provided.")
        print("Use the '--statefile = ' command line option.")
        print("Exiting...\n")
        sys.exit()

    numberofcycles = itarget - ibase    # for convenience


    # SET UP OUTPUT FILES

    i = datetime.datetime.now()
    #timelabel = "%s_%s_%s.%s_%s" % (i.year, i.month, i.day, i.hour, i.minute)
    timelabel = i.strftime("%Y_%m_%d.%H_%M")
    iterlabel = "[%s,%s]" % (ibase+1, itarget)

    longlabel  = "wb-%s-%s" % (timelabel, iterlabel)
    shortlabel = "wb-%s" % (iterlabel)

    outfolder = Path(datafolder, language, "wordbreaking", longlabel)
    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    outfile_pathname                 = str(Path(outfolder, shortlabel + ".txt"))
    outfile_corpus_pathname          = str(Path(outfolder, shortlabel + "_brokencorpus.txt"))
    outfile_lexicon_pathname         = str(Path(outfolder, shortlabel + "_lexicon_.txt"))
    outfile_recallprecision_pathname = str(Path(outfolder, shortlabel + "_recallprecision.tsv"))
    outfile_jsonpickle_pathname      = str(Path(outfolder, longlabel  + "_jsonpickle.txt"))

    outfile                 = open(outfile_pathname, "w")
    outfile_corpus          = open(outfile_corpus_pathname, "w")
    outfile_lexicon         = open(outfile_lexicon_pathname, "w")
    outfile_recallprecision = open(outfile_recallprecision_pathname, "w")
    outfile_jsonpickle      = open(outfile_jsonpickle_pathname, "w")

    # Header for outfile
    print("# corpus = " + str(corpus), file=outfile)
    print("# state loaded from " + str(statefile), file=outfile)
    print("# state saved to " + longlabel  + "_jsonpickle.txt", file=outfile)
    print("# " + str(numberofcycles) + " cycles, ", "(first = " + str(ibase + 1) + ", last = " + str(itarget) + ")", file=outfile)
    print("# " + str(candidatesperiteration) + " candidates on each cycle.", file=outfile)
    print("# lines read from original corpus = ", howmuchcorpus, file=outfile)

    # Header for jsonpickle outfile
    print("# Corpus = " + str(corpus), file=outfile_jsonpickle)
    print("# Date = " + i.strftime("%Y_%m_%d"), file=outfile_jsonpickle)
    print("# Time = " + i.strftime("%H_%M"), file=outfile_jsonpickle)
    print("# First iteration = " + str(ibase+1), file=outfile_jsonpickle)
    print("# Last iteration = " + str(itarget), file=outfile_jsonpickle)
    print("# Notes = working on reacting to load state errors",file=outfile_jsonpickle)
    print(file=outfile_jsonpickle)

    infile_corpus_pathname = str(Path(datafolder, language, corpus))


    # INITIAL PROCESSING

    if False:
        if prev_iteration_number == 0:
            this_lexicon.ReadBrokenCorpus (corpusfilename, corpuslinestoread)
        else:
            print("LOADING SAVED STATE...")
            this_lexicon.LoadState(prev_iteration_number)  # Oops

    if (ibase == 0 and statefile == None):
        this_lexicon = Lexicon()
        this_lexicon.ReadBrokenCorpus (infile_corpus_pathname, outfile, howmuchcorpus)
        #this_lexicon.ParseCorpus (outfile, current_iteration)  # CHANGE NEEDED WHEN LOAD SAVED STATE
        #this_lexicon.ParseCorpus (outfile, 0)  # CHANGE NEEDED WHEN LOAD SAVED STATE

    else:
        this_lexicon = LoadSavedStateFromFile(statefile, ibase, itarget)


    # ITERATIVE PROCESSING

    t_start = time.time()          # 2014_07_20    #2015_07_18   TEMPORARY
    for current_iteration in range(1+ibase, 1+itarget):
        print("\n\n Iteration number " + str(current_iteration) + " (#" + str(current_iteration-ibase) + " of " + str(numberofcycles) + " for this run)")
        print("\n\n Iteration number", current_iteration, file=outfile)
        method = "standard"  #FOR NOW

        this_lexicon.ExtendLexicon(method, current_iteration, candidatesperiteration, outfile)
        this_lexicon.ParseCorpus (current_iteration, outfile)
        this_lexicon.Report(current_iteration, outfile)


    # COMPLETION

    t_end = time.time()
    elapsed = t_end - t_start
    print ("\n\nElapsed wall time in seconds = ", elapsed)
    print ("\n\nElapsed wall time in seconds = ", elapsed, file=outfile)

    this_lexicon.PrintParsedCorpus(outfile_corpus)
    this_lexicon.PrintLexicon(outfile_lexicon)
    this_lexicon.PrintRecallPrecision(itarget, outfile_recallprecision)

    print("\nSAVING CURRENT STATE to '"  +  longlabel  + "_jsonpickle.txt'")
    print("[Processing can be continued from this point in a later run ")
    print("by loading this file through the '--statefile = ' command line option.]")
    print()
    serialstr = jsonpickle.encode(this_lexicon)
    print(serialstr, file=outfile_jsonpickle)

    outfile.close()
    outfile_corpus.close()
    outfile_lexicon.close()
    outfile_recallprecision.close()
    outfile_jsonpickle.close()



if __name__ == "__main__":

    args = makeArgParser().parse_args()

    ibase = args.ibase
    itarget = args.itarget
    statefile = args.statefile
    candidatesperiteration = args.candidates
    corpuslinestoread = args.corpuslinestoread
    verboseflag = args.verbose

    if corpuslinestoread == sys.maxsize:
        howmuchcorpus = "all"
    else:
        howmuchcorpus = str(corpuslinestoread)

    description="You are running {}.\n".format(__file__) + \
                "This program segments unbroken text into words.\n" + \
                "\tibase = {}\n".format(ibase) + \
                "\titarget = {}\n".format(itarget) + \
                "\tstatefile = {}\n".format(statefile) + \
                "\tcandidatesperiteration = {}\n".format(candidatesperiteration) + \
                "\tcorpuslinestoread = {}\n".format(howmuchcorpus) + \
                "\t_verbose = {}".format(verboseflag)

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    main(language, corpus, datafolder,
         ibase, itarget, statefile, candidatesperiteration, howmuchcorpus, verboseflag)

