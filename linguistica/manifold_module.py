#!/usr/bin/env python3

#-----------------------------------------------------------------------#
#
#    This program takes n-gram files and a word list    
#    and creates a file with lists of most similar words.
#    John Goldsmith and Wang Xiuli 2012.
#    Jackson Lee and Simon Jacobs 2014
#
#-----------------------------------------------------------------------#

from collections import (OrderedDict, defaultdict, Counter)
from itertools import combinations
from pathlib import Path

import json
import numpy as np
import scipy.spatial
import scipy.sparse
import networkx as nx

from .lxa5lib import sorted_alphabetized, SEP_NGRAM

def Normalize(NumberOfWordsForAnalysis, CountOfSharedContexts):
    arr = np.ones((NumberOfWordsForAnalysis), dtype=np.int64)
    for word_no in range(NumberOfWordsForAnalysis):
        arr[word_no] = np.sum(CountOfSharedContexts[word_no]) - \
                       CountOfSharedContexts[word_no, word_no]
    return arr

def hasGooglePOSTag(line, corpus):
    if corpus == 'google':
        for tag in ['_NUM', '_ADP', '_ADJ', '_VERB', '_NOUN',
                    '_PRON', '_ADV', '_CONJ', '_DET']:
            if tag in line:
                return True
        else:
            return False
    else:
        return False

def GetMyWords(infileWordsname):
    word_to_freq = json.load(infileWordsname.open())
    return [word for word, freq in
            sorted(word_to_freq.items(), key=lambda x: x[1], reverse=True)]


def GetMyGraph(WordToNeighbors_by_str, useWeights=None):
    G = nx.Graph()
    for word in WordToNeighbors_by_str.keys():
        neighbors = WordToNeighbors_by_str[word] # a list
        for neighbor in neighbors:
            G.add_edge(word, neighbor)
    return G


def GetContextArray(nwords, worddict,
                    infileBigramsname, infileTrigramsname, mincontexts):

    # read bigrams and trigrams from their respective JSON data files
    bigram_to_freq = json.load(infileBigramsname.open())
    trigram_to_freq = json.load(infileTrigramsname.open())

    # convert the bigram and trigram dicts into list and sort them
    # throw away bi/trigrams whose frequency is below mincontexts
    bigram_to_freq_sorted = [(bigram, freq) for bigram, freq in 
        sorted_alphabetized(bigram_to_freq.items(), key=lambda x : x[1],
        reverse=True) if freq >= mincontexts]
    trigram_to_freq_sorted = [(trigram, freq) for trigram, freq in 
        sorted_alphabetized(trigram_to_freq.items(), key=lambda x : x[1],
        reverse=True) if freq >= mincontexts]

    # this is necessary so we can reference variables from inner functions
    class Namespace:
        pass
    ns = Namespace()
    # more notes: We use "ncontexts" to keep track of how many unique contexts
    # there are. Conveniently, ncontexts also serves to provide a unique context
    # index whenever the program encounters a new context. The dummy class
    # Namespace is to make it possible that we can refer to and update ncontexts
    # within inner functions (both "contexts_incr" and "addword")
    # inside this "GetContextArray" function.

    ns.ncontexts = 0
    def contexts_incr():
        tmp = ns.ncontexts
        ns.ncontexts += 1
        return tmp

    contextdict = defaultdict(contexts_incr)
    # key: context (tuple, e.g. ("of", "_", "cat") as a trigram context for "the"
    # value: context index (int)
    # This dict is analogous to worddict, where each key is a word (str)
    # and each value is a word index (int).

    # entries for sparse matrix
    rows = [] # row numbers are word indices
    cols = [] # column numbers are context indices
    vals = [] 

    # use the standard dict data type here, don't use Counter, defaultdict, etc
    # because we will serialize these two dicts as JSON later
    WordToContexts = dict()
    ContextToWords = dict()

    def addword(word, context, occurrence_count):
        word_no = worddict[word] # w is a word index
        context_no = contextdict[context] # c is a context index
        rows.append(word_no)
        cols.append(context_no)
        vals.append(1) # if we use 1, we assume "type" counts.
                       # What if we use occurrence_count (--> "token" counts)?

        # update WordToContexts and ContextToWords
        if word not in WordToContexts:
            WordToContexts[word] = dict()
        if context not in WordToContexts[word]:
            WordToContexts[word][context] = 0

        if context not in ContextToWords:
            ContextToWords[context] = dict()
        if word not in ContextToWords[context]:
            ContextToWords[context][word] = 0

        WordToContexts[word][context] += occurrence_count
        ContextToWords[context][word] += occurrence_count

    sep = SEP_NGRAM

    for trigram, freq in trigram_to_freq_sorted:
        word1, word2, word3 = trigram.split()

        context1 = '_' + sep + word2 + sep + word3
        context2 = word1 + sep + '_' + sep + word3
        context3 = word1 + sep + word2 + sep + '_'

        if worddict.get(word1) is not None:
            addword(word1, context1, freq)
        if worddict.get(word2) is not None:
            addword(word2, context2, freq)
        if worddict.get(word3) is not None:
            addword(word3, context3, freq)

    for bigram, freq in bigram_to_freq_sorted:
        word1, word2 = bigram.split()

        context1 = '_' + sep + word2
        context2 = word1 + sep + '_'

        if worddict.get(word1) is not None:
            addword(word1, context1, freq)
        if worddict.get(word2) is not None:
            addword(word2, context2, freq)

    # csr_matrix in scipy means compressed matrix
    return ( scipy.sparse.csr_matrix((vals,(rows,cols)),
                shape=(nwords, ns.ncontexts+1), dtype=np.int64 ),
             contextdict, WordToContexts, ContextToWords )


def counting_context_features(context_array):
    return np.dot(context_array, context_array.T) 


def compute_incidence_graph(NumberOfWordsForAnalysis, Diameter, CountOfSharedContexts):
    incidencegraph= np.asarray(CountOfSharedContexts, dtype=np.int64)

    for word_no in range(NumberOfWordsForAnalysis):
        incidencegraph[word_no, word_no] = Diameter[word_no]
    return incidencegraph



def compute_laplacian(NumberOfWordsForAnalysis, Diameter, incidencegraph): 
    D = np.sqrt(np.outer(Diameter, Diameter))
    # we want to NOT have div-by-zero errors,
    # but if D[i,j] = 0 then incidencegraph[i,j] = 0 too.
    D[D==0] = 1

    # broadcasts the multiplication, so A[i,j] = B[i,j] * C[i, j]
    mylaplacian = (1/D) * incidencegraph 
    return mylaplacian

def compute_coordinates(NumberOfWordsForAnalysis, NumberOfEigenvectors, myeigenvectors):
    Coordinates = dict()
    for wordno in range(NumberOfWordsForAnalysis):
        Coordinates[wordno]= list() 
        for eigenno in range(NumberOfEigenvectors):
            Coordinates[wordno].append( myeigenvectors[ wordno, eigenno ] )
    return Coordinates



def compute_words_distance(nwords, coordinates):
    # the scipy pdist function is to compute pairwise distances
    return scipy.spatial.distance.squareform(scipy.spatial.distance.pdist(coordinates, "euclidean"))


def compute_closest_neighbors(wordsdistance, NumberOfNeighbors):
    sortedNeighbors = wordsdistance.argsort() # indices of sorted rows, low to high
    # truncate columns at NumberOfNeighbors+1 
    closestNeighbors = sortedNeighbors[:,:NumberOfNeighbors+1] 
    return closestNeighbors


def GetEigenvectors(laplacian):
    # csr_matrix in scipy means compressed matrix
    laplacian_sparse = scipy.sparse.csr_matrix(laplacian)

    # linalg is the linear algebra module in scipy
    # eigs takes a matrix and returns (array of eigenvalues, array of eigenvectors)
    return scipy.sparse.linalg.eigs(laplacian_sparse)


def compute_WordToSharedContextsOfNeighbors(analyzedwordlist, WordToContexts,
        WordToNeighbors, ContextToWords, mincontexts):

    WordToSharedContextsOfNeighbors = dict()

    for word in analyzedwordlist:
        WordToSharedContextsOfNeighbors[word] = dict()

        neighbors = WordToNeighbors[word] # list of neighbor indices

        for context in WordToContexts[word].keys():
            WordToSharedContextsOfNeighbors[word][context] = list()

            for neighbor in neighbors:
                if neighbor in ContextToWords[context]:
                    WordToSharedContextsOfNeighbors[word][context].append(neighbor)

            if len(WordToSharedContextsOfNeighbors[word][context]) < mincontexts:
                del WordToSharedContextsOfNeighbors[word][context]

    ImportantContextToWords = dict()
    for word in analyzedwordlist:
        for context in WordToSharedContextsOfNeighbors[word].keys():
            CountOfThisWordInThisContext = ContextToWords[context][word]
            if CountOfThisWordInThisContext >= mincontexts:
                if context not in ImportantContextToWords:
                    ImportantContextToWords[context] = dict()
                ImportantContextToWords[context][word] = CountOfThisWordInThisContext

    return (WordToSharedContextsOfNeighbors, ImportantContextToWords)


def output_WordToSharedContextsOfNeighbors(outfilenameSharedcontexts,
        WordToSharedContextsOfNeighbors, analyzedwordlist):

    with outfilenameSharedcontexts.open("w") as f:
        for i, word in enumerate(analyzedwordlist, 1):
            ContextToNeighbors = WordToSharedContextsOfNeighbors[word] # a dict
            if not ContextToNeighbors:
                continue

            # To ensure that the output is always the same, we need three
            # rounds of sorting here:
            #   1) sort alphabetically by the context str
            #   2) reverse sort for sizes of neighbor lists
            #   3) sort alphabetically for neighbor lists with the same size

            ContextToNeighbors = sorted(ContextToNeighbors.items())
            # ContextToNeighbors is now a list of tuples, not a dict anymore

            ContextToNeighbors = sorted_alphabetized(ContextToNeighbors,
                key=lambda x: len(x[1]), reverse=True, subkey=lambda x:x[1])

            print("{} {} ({})".format(i, word, len(ContextToNeighbors)), file=f)

            for context, neighbors in ContextToNeighbors:
                context = context.replace("\t", " ")
                neighbors = " ".join(neighbors)
                print("          {:20} | {}".format(context, neighbors), file=f)

            print(file=f)


def output_ImportantContextToWords(outfilename, ImportantContextToWords):

    ImportantContextToWords_sorted = sorted_alphabetized(
        ImportantContextToWords.items(), key=lambda x: len(x[1]), reverse=True)

    context_list = [context.replace("\t", " ")
                        for context, v in ImportantContextToWords_sorted]
    max_key_length = max([len(x) for x in context_list])

    WordToCount_list = [WordToCount for _, WordToCount in ImportantContextToWords_sorted]

    with outfilename.open("w") as f:
        for context, WordToCount in zip(context_list, WordToCount_list):
            print("{} {}".format(context.ljust(max_key_length), 
                len(WordToCount)), file=f)
        print(file=f)

        for context, WordToCount in zip(context_list, WordToCount_list):
            if not WordToCount:
                continue

            print("\n===============================================\n", file=f)
            print("{} {}".format(context.ljust(max_key_length),
                len(WordToCount)), file=f)
            print(file=f)

            WordToCount_sorted = sorted_alphabetized(WordToCount.items(),
                key=lambda x :x[1], reverse=True)

            # don't use "count" as a variable (it's the name of a function in python)
            max_word_length = max([len(word)
                for word, c in WordToCount_sorted])

            for word, c in WordToCount_sorted:
                print("        {} {}".format(
                    word.ljust(max_word_length), c), file=f)


#------------------------------------------------------------------------------#
#------------------------------------------------------------------------------#
# TODO: bring latex output back


#def LatexAndEigenvectorOutput(LatexFlag, PrintEigenvectorsFlag, infileWordsname, outfileLatex, outfileEigenvectors, NumberOfEigenvectors, myeigenvalues, NumberOfWordsForAnalysis):
#    if LatexFlag:
#            #Latex output
#            print("% ",  infileWordsname, file=outfileLatex)
#            print("\\documentclass{article}", file=outfileLatex) 
#            print("\\usepackage{booktabs}" , file=outfileLatex)
#            print("\\begin{document}" , file=outfileLatex)

#    data = dict() # key is eigennumber, value is list of triples: (index, word, eigen^{th} coordinate) sorted by increasing coordinate
#    print("9. Printing contexts to latex file.")
#    formatstr = '%20s   %15s %10.3f'
#    headerformatstr = '%20s  %15s %10.3f %10s'
#    NumberOfWordsToDisplayForEachEigenvector = 20
#            

#            
#                     
#    if PrintEigenvectorsFlag:

#            for eigenno in range(NumberOfEigenvectors):
#                    print >>outfileEigenvectors
#                    print >>outfileEigenvectors,headerformatstr %("Eigenvector number", eigenno, myeigenvalues[eigenno], "word" )
#                    print >>outfileEigenvectors,"_"*50 

#                    eigenlist=list()        
#                    for wordno in range (NumberOfWordsForAnalysis):         
#                            eigenlist.append( (wordno,myeigenvectors[wordno, eigenno]) )            
#                    eigenlist.sort(key=lambda x:x[1])            

#                    for wordno in range(NumberOfWordsForAnalysis):    
#                            word = analyzedwordlist[eigenlist[wordno][0]]
#                            coord =  eigenlist[wordno][1]        
#                            print >>outfileEigenvectors, formatstr %(eigenno, word, eigenlist[wordno][1])


#     

#    if LatexFlag:
#            for eigenno in range(NumberOfEigenvectors):
#                    eigenlist=list()    
#                    data = list()
#                    for wordno in range (NumberOfWordsForAnalysis):         
#                            eigenlist.append( (wordno,myeigenvectors[wordno, eigenno]) )            
#                    eigenlist.sort(key=lambda x:x[1])            
#                    print >>outfileLatex             
#                    print >>outfileLatex, "Eigenvector number", eigenno, "\n" 
#                    print >>outfileLatex, "\\begin{tabular}{lll}\\toprule"
#                    print >>outfileLatex, " & word & coordinate \\\\ \\midrule "

#                    for i in range(NumberOfWordsForAnalysis):             
#                            word = analyzedwordlist[eigenlist[i][0]]
#                            coord =  eigenlist[i][1]
#                            if i < NumberOfWordsToDisplayForEachEigenvector or i > NumberOfWordsForAnalysis - NumberOfWordsToDisplayForEachEigenvector:
#                                    data.append((i, word , coord ))
#                    for (i, word, coord) in data:
#                            if word == "&":
#                                    word = "\&" 
#                            print >>outfileLatex,  "%5d & %10s &  %10.3f \\\\" % (i, word, coord) 

#                    print >>outfileLatex, "\\bottomrule \n \\end{tabular}", "\n\n"
#                    print >>outfileLatex, "\\newpage" 
#            print >>outfileLatex, "\\end{document}" 


