#!/usr/bin/env python3

#-----------------------------------------------------------------------#
#
#    This program creates word neighbor graphs for a specified word.
#    John Goldsmith, Jackson Lee, 2015
#
#-----------------------------------------------------------------------#

import argparse
from pathlib import Path
import sys
import time

import networkx as nx

from lxa5lib import (get_language_corpus_datafolder,
                     load_config_for_command_line_help)
import manifold

# colors for generations of nodes in output graph
# RGB_list[0] is the color for the seed word node
# RGB_list[1] is the color for the 1st generation word nodes, and so forth
RGB_list = [{'a': 1, 'r': 255, 'g': 128, 'b': 0}, # orange
            {'a': 1, 'r': 51, 'g': 153, 'b': 255}, # blue
            {'a': 1, 'r': 255, 'g': 255, 'b': 0}, # yellow
            {'a': 1, 'r': 51, 'g': 255, 'b': 51}, # green
            {'a': 1, 'r': 255, 'g': 51, 'b': 51}, # red
           ]

# the number of generations is restricted by len_RGB_list
# (if we want more generations, we'll just have to build in more colors in RGB_list...)
len_RGB_list = len(RGB_list)

def makeArgParser(configfilename="config.json"):

    language, \
    corpus, \
    datafolder, \
    configtext = load_config_for_command_line_help(configfilename)

    parser = argparse.ArgumentParser(
        description="This program creates word neighbor graphs.\n\n{}"
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

    return parser


def lastmodified(epochtime):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epochtime))


def main(language, corpus, datafolder):

    infolder = Path(datafolder, language, 'neighbors')
    outfolder = Path(datafolder, language, 'neighbors')

    # get the list of .gexf word neighbor data filenames
    gexf_infilenames = list(Path(infolder).glob("*neighbors.gexf"))
    if not infolder.exists() or not gexf_infilenames:
        print("No .gexf neighbor data files are detected.\n"
              "The program manifold.py will now be run to compute\n"
              "word neighbors using this corpus text file:\n"
              "{}".format(Path(datafolder, language, corpus)), flush=True)
        manifold.main(language, corpus, datafolder)
        gexf_infilenames = list(Path(infolder).glob("*_neighbors.gexf"))

    # determine which .gexf data file to use
    if len(gexf_infilenames) == 1:
        gexf_infilename = Path(infolder, gexf_infilenames[0])
    else:
        print("\nThe program is looking for a .gexf data file\n"
              "in the following folder "
              "relative to the current directory:\n\n{}\n".format(infolder))

        # sort filenames by the last modified time, in descending order
        gexf_infilenames = sorted(gexf_infilenames,
                                  key=lambda x : x.stat().st_mtime,
                                  reverse=True)

        max_length_filename = max([len(x.name) for x in gexf_infilenames])

        while True:
            gexf_choice = input("\nChoose from the following .gexf neighbor files\n"
                              "by entering the number:\n"
                              "(Files modified most recently are ranked top.)\n\n"
                              "{}\n\n>>> ".format("\n".join([str(i) + ". " + \
                                  x.name.ljust(max_length_filename+1) + \
                                  lastmodified(x.stat().st_mtime)
                                  for i, x in enumerate(gexf_infilenames, 1)])))

            try:
                gexf_infilename = gexf_infilenames[int(gexf_choice)-1]
            except (ValueError, IndexError):
                print("Invalid input")
                continue
            else:
                break

    print("===================================\n\n"
          "The program will be using the following "
          ".gexf data file:\n\n{}\n".format(gexf_infilename))

    G = nx.read_gexf(str(gexf_infilename))
    wordlist = G.nodes()

    # ask for which word(s) to deal with and output the neighbor graph
    word_generations_list = list()

    while True:
        if word_generations_list:
            current_words = "\n\nCurrent words and their generations: " + \
                            "(You may add or delete words.)\n" + \
                            "\n".join(["{} {}".format(w,g)
                                       for w, g in word_generations_list])
        else:
            current_words = ""

        userinput = input("-----------------------------\n"
                          "What word(s) do you want to explore? "
                          "Input options:\n"
                          "1. \"add <word> <k>\" -- Add this word for output.\n"
                          "          <word> = the word\n"
                          "          <k> = how many generations (0 < k < {}) "
                          "from that word.\n"
                          "2. \"del <word>\" -- Delete this word.\n"
                          "3. \"run\" -- Create the neighbor graph for the words added.\n"
                          "4. \"exit\" -- Exit."
                          "{}\n\n>>> ".format(len_RGB_list, current_words))

        userinput = userinput.strip().casefold()

        # check if user input is valid with a legal command word
        command, *rest = userinput.split()

        if command not in {"add", "del", "run", "exit"}:
            print("Invalid command word: {}".format(command))
            continue

        # perform the appropriate actions according to the command word
        if command == "exit":
            sys.exit("Program terminated by user.")

        elif command == "run":

            # make sure there are words in word_generations_list
            if not word_generations_list:
                print("No words are selected.")
                continue

            print("The program now creates the neighbor graph.\n")

            # initialize the output graph
            output_G = nx.Graph()

            # add nodes and edges to output graph; color nodes by generations
            for word, generations in word_generations_list:
                current_words = {word} # a set
                current_generation = 0

                while current_generation < generations:
                    next_batch = set()

                    for _word in current_words:

                        if _word not in output_G:
                            output_G.add_node(_word)
                            output_G.node[_word]['viz'] = dict()
                            output_G.node[_word]['viz']['color'] = RGB_list[current_generation]

                        neighbors = set(nx.all_neighbors(G, _word))

                        for neighbor in neighbors:

                            if neighbor not in output_G:
                                output_G.add_node(neighbor)
                                output_G.node[neighbor]['viz'] = dict()
                                output_G.node[neighbor]['viz']['color'] = RGB_list[current_generation+1]

                            output_G.add_edge(_word, neighbor)

                        next_batch.update(neighbors)

                    current_words = next_batch
                    current_generation += 1

            # force all seed words to have the color for seed words
            for word, generations in word_generations_list:
                output_G.node[word]['viz']['color'] = RGB_list[0]

            # output the graph as .gexf
            filenamesuffix = "_".join([w+"-"+str(g)
                                       for w,g in word_generations_list]) + ".gexf"
            outgraphfilename = gexf_infilename.stem.replace("neighbors",
                                                            filenamesuffix)
            outgraph_path = Path(outfolder, outgraphfilename)
            nx.write_gexf(output_G, str(outgraph_path))

            print("===================================\n\n"
                  "Neighbor graph generated:\n{}\n".format(outgraph_path))

            print("Note:\n"
                  "1. All seed words are forced to bear the color for seed words,\n"
                  "   so that we can visually see the distances between seed words.\n"
                  "2. The ordering by which seed words were entered influences\n"
                  "   the coloring of nodes, because currently the code does not\n"
                  "   allow overrding the color of a node already in the output\n"
                  "   graph. Try the same words with different orders.\n")

            break

        elif command == "add":

            word, *k = rest

            # check if word and k (= number of generations) are valid
            if word not in wordlist:
                print("The word is not in the neighbor graph.")
                continue

            try:
                k = int(k[0])
                if k < 1 or k >= len_RGB_list:
                    raise ValueError
            except (ValueError, IndexError):
                print("Invalid number of generations -- "
                      "it must be a positive interger "
                      "smaller than {}.".format(len_RGB_list))
                continue

            # check if word is already in word_generations_list
            current_words = {w for w, k in word_generations_list} # a set
            if word in current_words:
                print("The word is already added.")
                continue

            # if all tests above are passed, add (word, k) to word_generations_list
            word_generations_list.append((word, k))

        elif command == "del":

            # check if there's a word in the user input
            try:
                word = rest[0]
            except IndexError:
                print("No word is given.")
                continue

            # check if word is absent from word_generations_list
            current_words = {w for w, k in word_generations_list} # a set
            if word not in current_words:
                print("The word has not been added.")
                continue

            # if all tests above are passed, delete (word, k) in word_generations_list

            for _word, k in word_generations_list[:]:
            # the [:] syntax creates a copy as loop iterator,
            # which allows us to delete items from word_generations_list inside the loop
                if _word == word:
                    word_generations_list.remove((word, k))
                    break


if __name__ == "__main__":

    args = makeArgParser().parse_args()

    description="You are running {}.\n".format(__file__) + \
                "This program creates word neighbor graphs\n" + \
                "for some given word(s).\n"

    language, corpus, datafolder = get_language_corpus_datafolder(args.language,
                                      args.corpus, args.datafolder, args.config,
                                      description=description,
                                      scriptname=__file__)

    main(language, corpus, datafolder)

