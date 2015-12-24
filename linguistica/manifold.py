#-----------------------------------------------------------------------#
#
#    This program takes n-gram files and a word list    
#    and creates a file with lists of most similar words.
#    John Goldsmith and Wang Xiuli 2012.
#    Jackson Lee and Simon Jacobs 2014
#
#-----------------------------------------------------------------------#


import argparse
from pathlib import Path
from collections import OrderedDict
import sys
import json

import networkx as nx
from networkx.readwrite import json_graph

from .manifold_module import (GetMyWords, GetContextArray,
                             Normalize, compute_incidence_graph,
                             compute_laplacian, GetEigenvectors,
                             compute_words_distance, compute_closest_neighbors,
                             compute_WordToSharedContextsOfNeighbors,
                             output_WordToSharedContextsOfNeighbors,
                             GetMyGraph, output_ImportantContextToWords)
from . import ngram
from . import signature

from .lxa5lib import (changeFilenameSuffix, stdout_list, json_pload,
                      SEP_SIG, SEP_SIGTRANSFORM, json_dump)


def main(language=None, corpus=None, datafolder=None, filename=None,
         maxwordtypes=1000, nNeighbors=9, nEigenvectors=11, 
         mincontexts=3):

    print("\n*****************************************************\n"
          "Running the manifold component of Linguistica now...\n")

    if filename:
        corpusStem = Path(filename).stem
        infolder = Path(Path(filename).parent, 'ngrams')
        outfolder = Path(Path(filename).parent, 'neighbors')
        outcontextsfolder = Path(Path(filename).parent, 'word_contexts')
    else:
        corpusStem = Path(corpus).stem
        infolder = Path(datafolder, language, 'ngrams')
        outfolder = Path(datafolder, language, 'neighbors')
        outcontextsfolder = Path(datafolder, language, 'word_contexts')

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    if not outcontextsfolder.exists():
        outcontextsfolder.mkdir(parents=True)

    # input filenames
    infileWordsname = Path(infolder, corpusStem + '_words.json')
    infileBigramsname = Path(infolder, corpusStem + '_bigrams.json')
    infileTrigramsname = Path(infolder, corpusStem + '_trigrams.json')

    # if the expected input files are absent, run ngram.py to generate them
    if (not infileWordsname.exists()) or \
       (not infileBigramsname.exists()) or \
       (not infileTrigramsname.exists()):
        print("Error in locating ngram data files.\n"
              "The program now creates them.\n")
        ngram.main(language=language, corpus=corpus,
                        datafolder=datafolder, filename=filename)

    # get signature transforms
    if filename:
        infolderlxa = Path(Path(filename).parent, 'lxa')
    else:
        infolderlxa = Path(datafolder, language, 'lxa')
    sigtransform_json_fname = Path(infolderlxa,
                                    corpusStem + "_WordToSigtransforms.json")
    try:
        WordToSigtransforms = json_pload(sigtransform_json_fname.open())
    except FileNotFoundError:
        print("The file \"{}\" is not found.\n"
              "The program now creates it.\n".format(sigtransform_json_fname))
        signature.main(language=language, corpus=corpus, datafolder=datafolder,
                  filename=filename)
        WordToSigtransforms = json_pload(sigtransform_json_fname.open())
    except ValueError:
        # WordToSigtransforms has nothing interesting
        pass

    # WordToSigtransforms just read into the program; to be used soon...

    print('Reading word list...', flush=True)
    mywords = GetMyWords(infileWordsname)

    print("Word file is", infileWordsname, flush=True)
    print("Number of neighbors to find for each word type: ", nNeighbors)
    print('Corpus has', len(mywords), 'word types', flush=True)

    lenMywords = len(mywords)
    if lenMywords > maxwordtypes:
        nWordsForAnalysis = maxwordtypes
    else:
        nWordsForAnalysis = lenMywords
    print('number of words for analysis adjusted to', nWordsForAnalysis)

    analyzedwordlist = mywords[ : nWordsForAnalysis] 
    worddict = {word: analyzedwordlist.index(word) for word in analyzedwordlist}

    corpusName = corpusStem + '_' + str(nWordsForAnalysis) + '_' + str(nNeighbors)

    # output filenames
    outfilenameNeighbors = Path(outfolder, corpusName + "_neighbors.txt")
    outfilenameSharedcontexts = Path(outfolder, corpusName + \
                                "_shared_contexts.txt")
    outfilenameNeighborGraph = Path(outfolder, corpusName + "_neighbors.gexf")
    outfilenameImportantContextToWords = Path(outfolder, corpusName + \
                                              "_ImportantContextToWords.txt")
    outWordToContexts_json = Path(outcontextsfolder, corpusName + \
                                       "_WordToContexts.json")
    outContextToWords_json = Path(outcontextsfolder, corpusName + \
                                       "_ContextToWords.json")

    # now ready to do the actual work...

    print("Reading bigrams/trigrams and computing context array...", flush=True)

    context_array, contextdict, \
    WordToContexts, ContextToWords = GetContextArray(nWordsForAnalysis,
        worddict, infileBigramsname, infileTrigramsname, mincontexts)

    # output WordToContexts, ContextToWords
    json_dump(WordToContexts, outWordToContexts_json.open("w"),
        separators=(',', ':'), indent=2)
    json_dump(ContextToWords, outContextToWords_json.open("w"),
        separators=(',', ':'), indent=2)

    print("Computing shared context master matrix...", flush=True)
    CountOfSharedContexts = context_array.dot(context_array.T).todense()
    del context_array

    print("Computing diameter...", flush=True)
    Diameter = Normalize(nWordsForAnalysis, CountOfSharedContexts)

    print("Computing incidence graph...", flush=True)
    incidencegraph = compute_incidence_graph(nWordsForAnalysis, Diameter,
                                             CountOfSharedContexts)
    del CountOfSharedContexts

    print("Computing mylaplacian...", flush=True)
    mylaplacian = compute_laplacian(nWordsForAnalysis, Diameter, incidencegraph)
    del Diameter
    del incidencegraph

    print("Computing eigenvectors and eigenvalues...", flush=True)
    myeigenvalues, myeigenvectors = GetEigenvectors(mylaplacian)
    del mylaplacian

    ### BEGIN work in progress ### J Lee, 2015-12-24
    eigenvector_outdict = dict()

    for eigen_no in range(len(myeigenvalues)):

        ## BUG? Why is len(myeigenvalues) NOT equal to nEigenvectors?
        coordinate_word_pairs = list()

        for word_no in range(nWordsForAnalysis):
            coordinate = myeigenvectors[word_no, eigen_no]
            word = analyzedwordlist[word_no]
            coordinate_word_pairs.append((coordinate, word))

        coordinate_word_pairs.sort()
        eigenvector_outdict[eigen_no] = (myeigenvalues[eigen_no],
                                         coordinate_word_pairs)

    with Path(outfolder, corpusName + '_eigenvectors.json').open('w') as f:
        json_dump(eigenvector_outdict, f)

    # Data structure of the output json file:
    #
    # { eigen_number : [ eigenvalue, eigenvector_as_an_array ] }
    #
    # eigen_number starts from 0 to k-1, for k eigenvectors
    # (note: I don't understand why the current code only outputs 6 eigenvectors, while our default parameter has set the number of eigenvectors to be 11... bug to fix soon?)
    #
    # eigenvector_as_an_array is an array of pairs, where each pair is (coordinate, word). The pairs in eigenvector_as_an_array are sorted in ascending order by the coordinates.

    ### END work in progress ### J Lee, 2015-12-24

    print('Computing distances between words...', flush=True)
    # take first N columns of eigenvector matrix
    coordinates = myeigenvectors[:,:nEigenvectors] 
    wordsdistance = compute_words_distance(nWordsForAnalysis, coordinates)
    del coordinates
    del myeigenvalues

    print('Computing nearest neighbors now... ', flush=True)
    closestNeighbors = compute_closest_neighbors(wordsdistance, nNeighbors)

    WordToNeighbors = OrderedDict()

    for wordno in range(nWordsForAnalysis):
        line = closestNeighbors[wordno]
        word_idx, neighbors_idx = line[0], line[1:]
        word = analyzedwordlist[word_idx]
        neighbors = [analyzedwordlist[idx] for idx in neighbors_idx]
        WordToNeighbors[word] = neighbors

    del closestNeighbors

    with outfilenameNeighbors.open('w') as f:
        print("# language: {}\n# corpus: {}\n"
              "# Number of word types analyzed: {}\n"
              "# Number of neighbors: {}\n".format(language, corpus,
                                         nWordsForAnalysis, nNeighbors), file=f)

        for word, neighbors in WordToNeighbors.items():
            print(word, " ".join(neighbors), file=f)

    neighbor_graph = GetMyGraph(WordToNeighbors)

    # output manifold as gexf data file
    nx.write_gexf(neighbor_graph, str(outfilenameNeighborGraph))

    # output manifold as json for d3 visualization
    manifold_json_data = json_graph.node_link_data(neighbor_graph)
    outfilenameManifoldJson = Path(outfolder, corpusName + "_manifold.json")
    json_dump(manifold_json_data, outfilenameManifoldJson.open("w"))

    WordToNeighbors_json = changeFilenameSuffix(outfilenameNeighbors, ".json")
    json_dump(WordToNeighbors, WordToNeighbors_json.open("w"))

    print("Computing shared contexts among neighbors...", flush=True)
    WordToSharedContextsOfNeighbors, \
    ImportantContextToWords = compute_WordToSharedContextsOfNeighbors(
        analyzedwordlist, WordToContexts, WordToNeighbors, ContextToWords,
        mincontexts)

    output_WordToSharedContextsOfNeighbors(outfilenameSharedcontexts,
        WordToSharedContextsOfNeighbors, analyzedwordlist)

    output_ImportantContextToWords(outfilenameImportantContextToWords,
        ImportantContextToWords)

    outputfilelist = [outfilenameNeighbors, outfilenameNeighborGraph,
                      WordToNeighbors_json, outfilenameSharedcontexts,
                      outfilenameImportantContextToWords,
                      outfilenameManifoldJson,
                      outWordToContexts_json, outContextToWords_json]

    # print to stdout the list of output files
    stdout_list("Output files:", *outputfilelist)


