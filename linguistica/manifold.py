#!/usr/bin/env python3

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

from .lxa5lib import (json_pdump, changeFilenameSuffix, stdout_list, json_pload,
                      SEP_SIG, SEP_SIGTRANSFORM)


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
    worddict = {w: analyzedwordlist.index(w) for w in analyzedwordlist}

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
    outworddict_json = Path(outcontextsfolder, corpusName + "_worddict.json")
    outcontextdict_json = Path(outcontextsfolder, corpusName + "_contextdict.json")

    # now ready to do the actual work...

    print("Reading bigrams/trigrams and computing context array...", flush=True)

    context_array, contextdict, \
    WordToContexts, ContextToWords = GetContextArray(nWordsForAnalysis,
        worddict, infileBigramsname, infileTrigramsname, mincontexts)

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

    print("Computing eigenvectors...", flush=True)
    myeigenvalues, myeigenvectors = GetEigenvectors(mylaplacian)
    del mylaplacian
    del myeigenvalues

    print('Computing distances between words...', flush=True)
    # take first N columns of eigenvector matrix
    coordinates = myeigenvectors[:,:nEigenvectors] 
    wordsdistance = compute_words_distance(nWordsForAnalysis, coordinates)
    del coordinates

    print('Computing nearest neighbors now... ', flush=True)
    closestNeighbors = compute_closest_neighbors(wordsdistance, nNeighbors)

    WordToNeighbors_by_str = OrderedDict()
    WordToNeighbors = dict()

    for wordno in range(nWordsForAnalysis):
        line = closestNeighbors[wordno]
        word_idx, neighbors_idx = line[0], line[1:]
        word = analyzedwordlist[word_idx]
        neighbors = [analyzedwordlist[idx] for idx in neighbors_idx]
        WordToNeighbors_by_str[word] = neighbors
        WordToNeighbors[word_idx] = neighbors_idx

    del closestNeighbors

    with outfilenameNeighbors.open('w') as f:
        print("# language: {}\n# corpus: {}\n"
              "# Number of word types analyzed: {}\n"
              "# Number of neighbors: {}\n".format(language, corpus,
                                         nWordsForAnalysis, nNeighbors), file=f)

        for word, neighbors in WordToNeighbors_by_str.items():
            print(word, " ".join(neighbors), file=f)

    neighbor_graph = GetMyGraph(WordToNeighbors_by_str)

    # output manifold as gexf data file
    nx.write_gexf(neighbor_graph, str(outfilenameNeighborGraph))

    # output manifold as json for d3 visualization
    manifold_json_data = json_graph.node_link_data(neighbor_graph)
    outfilenameManifoldJson = Path(outfolder, corpusName + "_manifold.json")
    json.dump(manifold_json_data, outfilenameManifoldJson.open("w"), indent=2)

    WordToNeighbors_json = changeFilenameSuffix(outfilenameNeighbors, ".json")
    json_pdump(WordToNeighbors_by_str, WordToNeighbors_json.open("w"), asis=True)

    print("Computing shared contexts among neighbors...", flush=True)
    WordToSharedContextsOfNeighbors, \
    ImportantContextToWords = compute_WordToSharedContextsOfNeighbors(
                                        nWordsForAnalysis, WordToContexts,
                                        WordToNeighbors, ContextToWords,
                                        nNeighbors, mincontexts)

    output_WordToSharedContextsOfNeighbors(outfilenameSharedcontexts,
                                        WordToSharedContextsOfNeighbors,
                                        worddict, contextdict,
                                        nWordsForAnalysis)

    output_ImportantContextToWords(outfilenameImportantContextToWords,
                                   ImportantContextToWords,
                                   contextdict, worddict)

    outputfilelist = [outfilenameNeighbors, outfilenameNeighborGraph,
                      WordToNeighbors_json, outfilenameSharedcontexts,
                      outfilenameImportantContextToWords,
                      outfilenameManifoldJson, outworddict_json,
                      outcontextdict_json]

    # output WordToContexts, ContextTOWords (these two are in the index form)
    #    also contextdict and worddict (from index to string)
    outputfilelist.append(outWordToContexts_json)
    json_pdump(WordToContexts, outWordToContexts_json.open("w"),
               key=lambda x : len(x[1]), reverse=True)

    outputfilelist.append(outContextToWords_json)
    json_pdump(ContextToWords, outContextToWords_json.open("w"),
               key=lambda x : len(x[1]), reverse=True)

    json_pdump({word_index: word for word, word_index in worddict.items()},
        outworddict_json.open("w"))

    json_pdump({context_index: context for context, context_index in contextdict.items()},
        outcontextdict_json.open("w"))

    # print to stdout the list of output files
    stdout_list("Output files:", *outputfilelist)


