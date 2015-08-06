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
RGB_list = [{'a': 1, 'r': 255, 'g': 128, 'b': 0}, # orange
            {'a': 1, 'r': 51, 'g': 153, 'b': 255}, # blue
            {'a': 1, 'r': 255, 'g': 255, 'b': 0}, # yellow
            {'a': 1, 'r': 51, 'g': 255, 'b': 51}, # green
            {'a': 1, 'r': 255, 'g': 51, 'b': 51}, # red
           ]


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
                            "(You may add another word.)\n" + \
                            "\n".join(["{} {}".format(w,g)
                                       for w, g in word_generations_list])
        else:
            current_words = ""

        userinput = input("-----------------------------\n"
                          "What word(s) do you want to explore? "
                          "Input options:\n"
                          "1. \"<word> <k>\"\n"
                          "          <word> = the word\n"
                          "          <k> = how many generations (> 0) from that word.\n"
                          "2. \"go\" -- Create the neighbor graph for the current words.\n"
                          "3. \"exit\" -- Exit.{}\n\n>>> ".format(current_words))

        userinput = userinput.strip().casefold()

        try:
            # check if input is an actual word plus number of generations
            word, k = userinput.split()
            if word not in wordlist:
                print("")
                raise ValueError

            k = int(k)

            # can take away "k > 4" when we can accommodate more colors!
            if k < 1 or k > 4:
                print("Invalid number of generations -- "
                      "it must be positive and smaller than 5.")
                raise ValueError

            # if both word and k pass the tests above, keep them.
            word_generations_list.append((word, k))

        except (ValueError, IndexError):
            if userinput not in {"go", "exit"}:
                print("Invalid input\n")
                continue
            elif userinput == "go" and not word_generations_list:
                print("No words are chosen.")
                continue

        if userinput == "exit":
            sys.exit("Program terminated by user.")
        elif userinput == "go":
            print("The program now creates the neighbor graph.\n")

            output_G = nx.Graph()

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

            filenamesuffix = "_".join([w+"-"+str(g)
                                       for w,g in word_generations_list]) + ".gexf"
            outgraphfilename = gexf_infilename.stem.replace("neighbors",
                                                            filenamesuffix)
            nx.write_gexf(output_G, str(Path(outfolder, outgraphfilename)))

            print("===================================\n\n"
                  "Neighbor graph generated:\n{}\n".format(outgraphfilename))

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

