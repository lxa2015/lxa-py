__author__ = 'Anton Melnikov'

from argparse import ArgumentParser
from itertools import combinations
from pprint import pprint

from lxa5 import create_wordlist

from Levenshtein import opcodes, editops

def are_similar(word1: str, word2: str) -> tuple:
    acceptable_ops = {'replace'}
    max_num_ops = 1

    all_ops = opcodes(word1, word2)

    # make sure that the first and the last characters are identities
    if all_ops[0][0] == 'equal' and all_ops[-1][0] == 'equal':
        edit_ops = editops(word1, word2)

        # check that there is only one operation, and that we allow that op
        if len(edit_ops) <= max_num_ops and edit_ops[0][0] in acceptable_ops:
            return True, all_ops

    return False, None

def find_pairs(corpus: list):
    word_pairs = combinations(corpus, 2)

    # compare each pair of words
    for word1, word2 in word_pairs:

        result = are_similar(word1, word2)
        similar, all_ops = result
        if similar:

            # a list for character comparisons
            comp_chars = []

            # present the differences by comparing the opcodes
            # (see http://www.coli.uni-saarland.de/courses/LT1/2011/slides/Python-Levenshtein.html)
            for op_kind, i1, i2, j1, j2 in all_ops:
                if op_kind == 'equal':
                    comp_chars.append(word1[i1:i2])
                elif op_kind == 'replace':
                    comp_chars.append((word1[i1:i2], word2[j1:j2]))

            yield word1, word2, comp_chars

def print_diff_pairs(diff_pairs):
    for word1, word2, diffs in diff_pairs:
        str_diffs = []
        for element in diffs:
            if isinstance(element, tuple):
                str_diffs.append('/'.join(element))
            else:
                str_diffs.append(element)
        print(word1, word2, str_diffs)

def run(language, corpus, min_stem_length):
    corpus = create_wordlist(language, corpus, min_stem_length)[0]
    diff_pairs = find_pairs(corpus)
    print_diff_pairs(diff_pairs)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('language', help='language to analyze')
    arg_parser.add_argument('corpus', help='corpus file to analyze')
    arg_parser.add_argument('-msl', '--min_stem_length',
                            type=int, default=4)
    args = arg_parser.parse_args()
    run(args.language, args.corpus, args.min_stem_length)

