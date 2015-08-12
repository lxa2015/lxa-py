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

import networkx as nx

from manifold_module import (GetMyWords, GetContextArray,
                             Normalize, compute_incidence_graph,
                             compute_laplacian, GetEigenvectors,
                             compute_words_distance, compute_closest_neighbors,
                             compute_WordToSharedContextsOfNeighbors,
                             output_WordToSharedContextsOfNeighbors,
                             GetMyGraph, output_ImportantContextToWords)
import ngrams
import lxa5

from lxa5lib import (get_language_corpus_datafolder, json_pdump,
                     changeFilenameSuffix, stdout_list, json_pload,
                     load_config_for_command_line_help,
                     SEP_SIG, SEP_SIGTRANSFORM)


def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="This program computes word neighbors.\n\n{}"
                    .format(configtext),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--config", help="configuration filename",
                        type=str, default=configfilename)

    parser.add_argument("--language", help="Language name",
                        type=str, default=None)
    parser.add_argument("--corpus", help="Corpus file to use",
                        type=str, default=None)
    parser.add_argument("--datafolder", help="path of the data folder",
                        type=str, default=None)

    parser.add_argument("--maxwordtypes", help="Number of word types to handle",
                        type=int, default=1000)
    parser.add_argument("--nNeighbors", help="Number of neighbors",
                        type=int, default=9)
    parser.add_argument("--nEigenvectors", help="Number of eigenvectors",
                        type=int, default=11)

    parser.add_argument("--mincontexts", help="Minimum number of times that "
                        "a word occurs in a context; "
                        "also minimum number of neighbors for a word that share "
                        "a context (for WordToSharedContextsOfNeighbors)",
                        type=int, default=3)
    parser.add_argument("--wordtocontexts", help="create the WordToContexts dict?",
                        type=bool, default=False)
    parser.add_argument("--contexttowords", help="create the ContextToWords dict?",
                        type=bool, default=False)
    parser.add_argument("--usesigtransforms", help="use signature transforms?",
                        type=bool, default=True)

    return parser


def main(language=None, corpus=None, datafolder=None, filename=None,
         maxwordtypes=1000, nNeighbors=9, nEigenvectors=11, 
         create_WordToContexts=False, create_ContextToWords=False,
         mincontexts=3, usesigtransforms=True):

    print("\n*****************************************************\n"
          "Running the manifold.py program now...\n")

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

    infileWordsname = Path(infolder, corpusStem + '_words.txt')
    infileBigramsname = Path(infolder, corpusStem + '_bigrams.txt')
    infileTrigramsname = Path(infolder, corpusStem + '_trigrams.txt')

    if (not infileWordsname.exists()) or \
       (not infileBigramsname.exists()) or \
       (not infileTrigramsname.exists()):
        print("Error in locating n-gram data files.\n"
              "The program now creates them.\n")
        ngrams.main(language=language, corpus=corpus,
                        datafolder=datafolder, filename=filename)

    if usesigtransforms:
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
            lxa5.main(language=language, corpus=corpus, datafolder=datafolder,
                      filename=filename)
            WordToSigtransforms = json_pload(sigtransform_json_fname.open())

    # WordToSigtransforms just read into the program; to be used soon...

    print('Reading word list...', flush=True)
    mywords = GetMyWords(infileWordsname, corpus)

    print("Word file is", infileWordsname, flush=True)
    print("Number of neighbors to find for each word type: ", nNeighbors)
    print('Corpus has', len(mywords), 'word types', flush=True)

    lenMywords = len(mywords)
    if lenMywords > maxwordtypes:
        nWordsForAnalysis = maxwordtypes
    else:
        nWordsForAnalysis = lenMywords
    print('number of words for analysis adjusted to', nWordsForAnalysis)

    analyzedwordlist = list(mywords.keys())[ : nWordsForAnalysis] 
    worddict = {w: analyzedwordlist.index(w) for w in analyzedwordlist}

    corpusName = corpusStem + '_' + str(nWordsForAnalysis) + '_' + str(nNeighbors)

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
    nx.write_gexf(neighbor_graph, str(outfilenameNeighborGraph))

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
                      outfilenameImportantContextToWords]

    if create_WordToContexts:
        outputfilelist.append(outWordToContexts_json)
        json_pdump(WordToContexts, outWordToContexts_json.open("w"),
                   key=lambda x : len(x[1]), reverse=True)

    if create_ContextToWords:
        outputfilelist.append(outContextToWords_json)
        json_pdump(ContextToWords, outContextToWords_json.open("w"),
                   key=lambda x : len(x[1]), reverse=True)

    stdout_list("Output files:", *outputfilelist)


if __name__ == "__main__":

    args = makeArgParser().parse_args()
    
    maxwordtypes = args.maxwordtypes
    nNeighbors = args.nNeighbors
    nEigenvectors = args.nEigenvectors
    create_WordToContexts = args.wordtocontexts
    create_ContextToWords = args.contexttowords
    mincontexts = args.mincontexts
    usesigtransforms = args.usesigtransforms

    description="You are running {}.\n".format(__file__) + \
                "This program computes word neighbors.\n" + \
                "maxwordtypes = {}\n".format(maxwordtypes) + \
                "nNeighbors = {}\n".format(nNeighbors) + \
                "nEigenvectors = {}\n".format(nEigenvectors) + \
                "create_WordToContexts = {}\n".format(create_WordToContexts) + \
                "create_ContextToWords = {}\n".format(create_ContextToWords) + \
                "mincontexts = {}\n".format(mincontexts) + \
                "usesigtransforms = {}".format(usesigtransforms)

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    if mincontexts > nNeighbors:
        print("\nBecause mincontexts > nNeighbors (which is disallowed),\n"
              "mincontexts is now set to equal nNeighbors.\n")
        mincontexts = nNeighbors

    main(language=language, corpus=corpus, datafolder=datafolder,
         maxwordtypes=maxwordtypes, nNeighbors=nNeighbors,
         nEigenvectors=nEigenvectors,
         create_WordToContexts=create_WordToContexts,
         create_ContextToWords=create_ContextToWords,
         mincontexts=mincontexts,
         usesigtransforms=usesigtransforms)

