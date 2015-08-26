#!usr/bin/env python3

import sys
import os
import json
import argparse
from pathlib import Path

from linguistica.lxa5lib import (__version__, determine_use_corpus,
                                 proceed_or_not,
                                 CONFIG, CONFIG_FILENAME, PROGRAMS,
                                 PROGRAM_TO_DESCRIPTION, PROGRAM_TO_PARAMETERS)

from linguistica import signature
from linguistica import ngram
from linguistica import trie
from linguistica import phon
from linguistica import manifold

def makeArgParser(config):
    parser = argparse.ArgumentParser(
        description="This is the Linguistica {} program.".format(__version__),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("program", help="Specific program to run: "
        "{}".format(", ".join(sorted(PROGRAMS))),
        type=str, default=None)

    parser.add_argument("--language", help="Language name",
        type=str, default=config["language"])
    parser.add_argument("--corpus", help="Corpus file to use",
        type=str, default=config["corpus"])
    parser.add_argument("--datafolder", help="path of the data folder",
        type=str, default=config["datafolder"])

    parser.add_argument("--max_word_tokens", help="maximum number of word tokens;"
        " if zero, then the program reads all word tokens in the corpus",
        type=int, default=config["max_word_tokens"])

    parser.add_argument("--min_stem_length", help="Minimum stem length; "
        "usually from 2 to 5, where a smaller number means you can find "
        "shorter stems although the program may run a lot slower",
        type=int, default=config["min_stem_length"])
    parser.add_argument("--max_affix_length", help="Maximum affix length; "
        "usually from 1 to 5 -- a larger number means possibly longer affixes",
        type=int, default=config["max_affix_length"])
    parser.add_argument("--min_sig_use", help="Minimum number of signature use; "
        "a small number like 5 is pretty much the smallest to use in order to "
        "filter spurious signatures; may try larger numbers like 10 or 20",
        type=int, default=config["min_sig_use"])

    parser.add_argument("--min_affix_length", help="Minimum affix length",
        type=int, default=config["min_affix_length"])
    parser.add_argument("--min_sf_pf_count", help="Minimum size of "
        "successors/predecessors for output",
        type=int, default=config["min_sf_pf_count"])

    parser.add_argument("--max_word_types", help="Number of word types to handle",
        type=int, default=config["max_word_types"])
    parser.add_argument("--n_neighbors", help="Number of neighbors",
        type=int, default=config["n_neighbors"])
    parser.add_argument("--n_eigenvectors", help="Number of eigenvectors",
        type=int, default=config["n_eigenvectors"])

    parser.add_argument("--min_context_use", help="Minimum number of times that "
        "a word occurs in a context; also minimum number of neighbors for a "
        "word that share a context (for WordToSharedContextsOfNeighbors)",
        type=int, default=config["min_context_use"])

    return parser


def load_config():
    print("\tlocating {} in the current directory... ".format(CONFIG_FILENAME),
        end="", flush=True)

    # read the configuration file (if present), and initialize "config"
    try:
        config = json.load(open(CONFIG_FILENAME))
        print("found", flush=True)
    except FileNotFoundError:
        config = CONFIG
        json.dump(config, open(CONFIG_FILENAME, "w"))
        print("not found\n\tdefault settings are used", flush=True)

    # make sure that the "config" dict has ALL the expected keys
    expected_keys = CONFIG.keys()
    for k in expected_keys:
        if k not in config:
            config[k] = CONFIG[k]

    return config


if __name__ == "__main__":

    # welcome
    print("\n***************************************************************\n"
          "Linguistica {}\n".format(__version__), flush=True)

    # print current directory
    print("Current directory:\n{}\n".format(os.getcwd()), flush=True)

    # load configuration file (if present) from current directory
    print("Loading configuration...", flush=True)
    config = load_config()
    print("\tconfiguration loaded\n", flush=True)

    # load command line arguments
    print("Loading command line arguments... ", end="", flush=True)
    args = makeArgParser(config).parse_args()

    program = args.program
    language = args.language
    corpus = args.corpus
    datafolder = args.datafolder

    max_word_tokens = args.max_word_tokens
    min_stem_length = args.min_stem_length
    max_affix_length = args.max_affix_length
    min_sig_use = args.min_sig_use
    min_affix_length = args.min_affix_length
    min_sf_pf_count = args.min_sf_pf_count
    n_neighbors = args.n_neighbors
    n_eigenvectors = args.n_eigenvectors
    min_context_use = args.min_context_use
    max_word_types = args.max_word_types
    print("done\n", flush=True)

    # make sure that "program" is one of the valid programs
    if not program:
        sys.exit("No specific program is specified.\n"
                 "Run \"python3 lxa5.py -h\" for details.")
    program = program.casefold()
    if program not in PROGRAMS:
        sys.exit("{} is not one of the programs.\n"
                 "Run \"python3 lxa5.py -h\" for details.".format(program))
    if program == "all":
        print("You are running all Linguistica components.", flush=True)
    else:
        print("You are running the {} program.\n"
            "{}\n".format(program, PROGRAM_TO_DESCRIPTION[program]), flush=True)

    # make sure that none of "language", "corpus", and "datafolder" are empty
    write_new_config = False
    if not language or not corpus or not datafolder:
        write_new_config = True
        print("At least one of the {{language, corpus, datafolder}} values is\n"
            "empty. The program will be looking for the file\n"
            "\"<datafolder>{}<language>{}<corpus>\" relative to your current\n"
            "directory. You are now prompted to provide what "
            "is missing.\n".format(os.sep, os.sep), 
            flush=True)
        while not datafolder:
            datafolder = input("Datafolder (relative to current directory): ")
            datafolder = datafolder.strip().casefold()
        while not language:
            language = input("Language: ")
            language = language.strip().casefold()
        while not corpus:
            corpus = input("Corpus filename (including file extension name): ")
            corpus = corpus.strip().casefold()
        print(flush=True)

    # make sure the expected input file (based on "language", "corpus", and
    # "datafolder") exists
    corpus_filename_path = Path(datafolder, language, corpus)
    if not corpus_filename_path.exists():
        sys.exit("The file {}\n relative to the current directory "
            "does not exist.".format(corpus_filename_path))
    print("The specified input data file relative to the current directory:\n"
          "{}\n".format(corpus_filename_path), flush=True)

    # print the relevant parameters
    print("The relevant program parameters are as follows:\n\t{}".format(
          "\n\t".join([parameter + " = " + str(eval(parameter))
              for parameter in PROGRAM_TO_PARAMETERS[program]])), flush=True)
    if "max_word_tokens" in PROGRAM_TO_PARAMETERS[program]:
        print("\t(If max_word_tokens is 0, "
              "all word tokens are handled.)\n", flush=True)
    else:
        print(flush=True)

    # pause and allow user to decide whether to proceed or not
    proceed_or_not()

    # run the specified program

    use_corpus = True # By default, the input data file is a corpus text file,
                      # unless a wordlist is used instead
                      # (for signature, trie, and phon)
    if program in {"signature", "trie", "phon"}:
        use_corpus = determine_use_corpus()

    # if program is "all", run all Linguistica programs in the specified order
    # otherwise just run the particular one as specified
    if program == "all":
        programs = ["ngram", "signature", "trie", "phon", "manifold"]
    else:
        programs = [program]

    for program in programs:
        if program == "ngram":
            ngram.main(language=language, corpus=corpus, datafolder=datafolder,
                 maxwordtokens=max_word_tokens)

        elif program == "signature":
            signature.main(language=language, corpus=corpus, datafolder=datafolder,
                 MinimumStemLength=min_stem_length,
                 MaximumAffixLength=max_affix_length,
                 MinimumNumberofSigUses=min_sig_use,
                 maxwordtokens=max_word_tokens, use_corpus=use_corpus)

        elif program == "trie":
            trie.main(language=language, corpus=corpus, datafolder=datafolder,
                 MinimumStemLength=min_stem_length,
                 MinimumAffixLength=min_affix_length,
                 SF_threshold=min_sf_pf_count,
                 maxwordtokens=max_word_tokens, use_corpus=use_corpus)

        elif program == "phon":
            phon.main(language=language, corpus=corpus, datafolder=datafolder,
                 maxwordtokens=max_word_tokens, use_corpus=use_corpus)

        elif program == "manifold":
            manifold.main(language=language, corpus=corpus, datafolder=datafolder,
                 maxwordtypes=max_word_types, nNeighbors=n_neighbors,
                 nEigenvectors=n_eigenvectors,
                 mincontexts=min_context_use)

    # check if the corpus text file has been run before, and keep track of it
    if use_corpus:
        # if use_corpus is False, then a wordlist (not a corpus text) was
        # used as input data. So in this case we don't change
        # "last_filename" and "filenames_run" which are only for corpora
        # text files
        corpus_filename_abspath = os.path.abspath(str(corpus_filename_path))
        if corpus_filename_abspath not in config["filenames_run"]:
            config["filenames_run"].append(corpus_filename_abspath)
            write_new_config = True
        if corpus_filename_abspath != config["last_filename"]:
            config["last_filename"] = corpus_filename_abspath
            write_new_config = True

    # if at least one of the parameters have been changed by the command line
    # input, then rewrite the configuration file
    if len(sys.argv) > 2 or write_new_config:

        config["language"] = language
        config["corpus"] = corpus
        config["datafolder"] = datafolder

        config["max_word_tokens"] = max_word_tokens
        config["min_stem_length"] = min_stem_length
        config["max_affix_length"] = max_affix_length
        config["min_sig_use"] = min_sig_use
        config["min_affix_length"] = min_affix_length
        config["min_sf_pf_count"] = min_sf_pf_count
        config["n_neighbors"] = n_neighbors
        config["n_eigenvectors"] = n_eigenvectors
        config["min_context_use"] = min_context_use
        config["max_word_types"] = max_word_types

        json.dump(config, open(CONFIG_FILENAME, "w"))
        print("New configuration file written", flush=True)

    # exit message
    print("End of the Linguistica program", flush=True)

