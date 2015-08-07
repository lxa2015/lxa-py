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

import numpy as np
import scipy.spatial.distance as sd
import scipy.sparse as sp
import scipy.sparse.linalg as sl
import networkx as nx

from lxa5lib import sorted_alphabetized

def Normalize(NumberOfWordsForAnalysis, CountOfSharedContexts):
    arr = np.ones((NumberOfWordsForAnalysis))
    for w in range(NumberOfWordsForAnalysis):
        arr[w] = np.sum(CountOfSharedContexts[w]) - CountOfSharedContexts[w, w]
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

def GetMyWords(infileWordsname, corpus, minWordFreq=1):
    mywords = dict()

    with infileWordsname.open() as wordfile:
        for line in wordfile:
            line = line.replace('\n', '').replace('\r', '')
            if (not line) or line.startswith('#') or hasGooglePOSTag(line, corpus):
                continue
            *subpieces, lastpiece = line.split()
            if not subpieces:
                continue

            wordFreq = int(lastpiece)
            if wordFreq < minWordFreq:
                break

            mywords[' '.join(subpieces)] = wordFreq

    return OrderedDict(sorted(mywords.items(),
                                            key=lambda x:x[1], reverse=True))


def GetMyGraph(WordToNeighbors_by_str, useWeights=None):
    G = nx.Graph()
    for word in WordToNeighbors_by_str.keys():
        neighbors = WordToNeighbors_by_str[word] # a list
        for neighbor in neighbors:
            G.add_edge(word, neighbor)
    return G


def GetContextArray(nwords, worddict,
                    infileBigramsname, infileTrigramsname):

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
    rows = []
    cols = []
    vals = [] 

    WordToContexts = defaultdict(Counter)
    ContextToWords = defaultdict(Counter)

    def addword(word, context, occurrence_count):
        w = worddict[word] # w is a word index
        c = contextdict[context] # c is a context index
        rows.append(w)
        cols.append(c)
        vals.append(1)

        WordToContexts[w][c] += occurrence_count
        ContextToWords[c][w] += occurrence_count

    with infileTrigramsname.open() as trigramfile:
        for line in trigramfile:
            line = line.strip()
            if (not line) or line.startswith('#'):
                continue
            c = line.split()

            word1 = c[0]
            word2 = c[1]
            word3 = c[2]
            occurrence_count = int(c[3])

            context1 = tuple(['_', word2, word3])
            context2 = tuple([word1, '_', word3])
            context3 = tuple([word1, word2, '_'])

            if worddict.get(word1) is not None:
                addword(word1, context1, occurrence_count)
            if worddict.get(word2) is not None:
                addword(word2, context2, occurrence_count)
            if worddict.get(word3) is not None:
                addword(word3, context3, occurrence_count)

    with infileBigramsname.open() as bigramfile:
        for line in bigramfile:
            line = line.strip()
            if (not line) or line.startswith('#'):
                continue
            c = line.split()

            word1 = c[0]
            word2 = c[1]
            occurrence_count = int(c[2])

            context1 = tuple(['_', word2])
            context2 = tuple([word1, '_'])

            if worddict.get(word1) is not None:
                addword(word1, context1, occurrence_count)
            if worddict.get(word2) is not None:
                addword(word2, context2, occurrence_count)

    return ( sp.csr_matrix((vals,(rows,cols)), shape=(nwords, ns.ncontexts+1) ),
             contextdict, WordToContexts, ContextToWords )


def counting_context_features(context_array):
    return np.dot(context_array, context_array.T) 


def compute_incidence_graph(NumberOfWordsForAnalysis, Diameter, CountOfSharedContexts):
    incidencegraph= np.asarray(CountOfSharedContexts, dtype=np.int32)

    for w in range(NumberOfWordsForAnalysis):
        incidencegraph[w, w] = Diameter[w]
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
    return sd.squareform(sd.pdist(coordinates, "euclidean"))


def compute_closest_neighbors(wordsdistance, NumberOfNeighbors):
    sortedNeighbors = wordsdistance.argsort() # indices of sorted rows, low to high
    # truncate columns at NumberOfNeighbors+1 
    closestNeighbors = sortedNeighbors[:,:NumberOfNeighbors+1] 
    return closestNeighbors


def GetEigenvectors(laplacian):
    laplacian_sparse = sp.csr_matrix(laplacian)
    return sl.eigs(laplacian_sparse)


def compute_WordToSharedContextsOfNeighbors(nWordsForAnalysis, WordToContexts,
                                        WordToNeighbors, ContextToWords,
                                        nNeighbors, mincontexts):

    WordToSharedContextsOfNeighbors = dict()

    for word in range(nWordsForAnalysis):
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
    for word in range(nWordsForAnalysis):
        for context in WordToSharedContextsOfNeighbors[word].keys():
            NumberOfTimesThisWordOccursInThisContext = ContextToWords[context][word]
            if NumberOfTimesThisWordOccursInThisContext >= mincontexts:
                if context not in ImportantContextToWords:
                    ImportantContextToWords[context] = dict()

                ImportantContextToWords[context][word] = NumberOfTimesThisWordOccursInThisContext

    return (WordToSharedContextsOfNeighbors, ImportantContextToWords)


def output_WordToSharedContextsOfNeighbors(outfilenameSharedcontexts,
                                        WordToSharedContextsOfNeighbors,
                                        worddict, contextdict,
                                        nWordsForAnalysis):

    _worddict = {v:k for k,v in worddict.items()} # from index to word
    _contextdict = {v:k for k,v in contextdict.items()} # from index to context

    with outfilenameSharedcontexts.open("w") as f:
        for word_idx in range(nWordsForAnalysis):

            ContextToNeighbors = WordToSharedContextsOfNeighbors[word_idx] # a dict

            if not ContextToNeighbors:
                continue

            ContextToNeighbors = sorted(ContextToNeighbors.items())
            ContextToNeighbors = sorted_alphabetized(ContextToNeighbors,
                                        key=lambda x: len(x[1]), reverse=True,
                                        alphaby=lambda x:x[1])
            # minor TODO: sort by key alphabetically
            #             *after* these sorting steps are done?

            # ContextToNeighbors is now a list of tuples, not a dict anymore

            word = _worddict[word_idx]

            print("{} {} ({})".format(word_idx+1, word,
                                      len(ContextToNeighbors)), file=f)

            for context_idx, neighbor_indices in ContextToNeighbors:
                context = " ".join(_contextdict[context_idx])
                neighbors = " ".join([_worddict[i] for i in neighbor_indices])

                print("          {:20} | {}".format(context, neighbors), file=f)

            print(file=f)


def output_ImportantContextToWords(outfilename, ImportantContextToWords,
                                   contextdict, worddict):

    _contextdict = {v:k for k,v in contextdict.items()} # from index to context tuple
    _worddict = {v:k for k,v in worddict.items()} # from index to word
    ImportantContextToWords_sorted = sorted_alphabetized(
                                        ImportantContextToWords.items(),
                                        key=lambda x: len(x[1]), reverse=True)

    context_str_list = [" ".join(_contextdict[context_index])
                        for context_index, v in ImportantContextToWords_sorted]
    max_key_length = max([len(x) for x in context_str_list])

    WordToCount_list = [WordToCount for _, WordToCount in ImportantContextToWords_sorted]

    with outfilename.open("w") as f:
        for context_str, WordToCount in zip(context_str_list, WordToCount_list):
            print("{} {}".format(context_str.ljust(max_key_length),
                                 len(WordToCount)), file=f)
        print(file=f)

        for context_str, WordToCount in zip(context_str_list, WordToCount_list):
            if not WordToCount:
                continue

            print("\n===============================================\n", file=f)
            print("{} {}".format(context_str.ljust(max_key_length),
                                 len(WordToCount)), file=f)
            print(file=f)

            # small bug to fix: sorted_alphabetized can't output all items (!)
            #       for unknown reasons. The good old "sorted" function is
            #       used for now -- J Lee, 2015/8/5
            WordToCount_sorted = sorted(WordToCount.items(),
                                    key=lambda x :x[1], reverse=True)

            max_word_length = max([len(_worddict[w]) for w, c in WordToCount_sorted])

            for w, c in WordToCount_sorted:
                print("        {} {}".format(
                                _worddict[w].ljust(max_word_length), c), file=f)


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


