__author__ = 'Anton Melnikov'

from argparse import ArgumentParser
from lxa5 import create_wordlist

from pprint import pprint

import Levenshtein

def run(language, corpus, min_stem_length):
    corpus = create_wordlist(language, corpus, min_stem_length)[0]
    pprint(corpus)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('language', help='language to analyze')
    arg_parser.add_argument('corpus', help='corpus file to analyze')
    arg_parser.add_argument('-msl', '--min_stem_length',
                            type=int, default=4)
    args = arg_parser.parse_args()
    run(args.language, args.corpus, args.min_stem_length)

