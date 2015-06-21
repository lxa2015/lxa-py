__author__ = 'Anton Melnikov'

from argparse import ArgumentParser
from collections import Counter, namedtuple
from itertools import combinations, permutations
from pathlib import Path
from pprint import pprint

from lxa5 import create_wordlist

from Levenshtein import opcodes, editops

WordPair = namedtuple('WordPair', ['word1', 'word2',
                                   'comparison',
                                   'skeleton', 'alternation'])

def are_similar(word1: str, word2: str) -> tuple:
    # (see http://www.coli.uni-saarland.de/courses/LT1/2011/slides/Python-Levenshtein.html)
    allowed_op_kinds = ('equal', 'replace', 'equal')

    all_ops = opcodes(word1, word2)
    op_kinds = tuple(op[0] for op in all_ops)
    if op_kinds == allowed_op_kinds:
        return True, all_ops

    return False, None

def find_pairs(corpus: list):
    word_pairs = combinations(corpus, 2)

    # compare each pair of words
    for n, (word1, word2) in enumerate(word_pairs):

        result = are_similar(word1, word2)
        similar, all_ops = result
        if similar:

            # a list for character comparisons
            skeleton = []
            alternations = []
            comp_chars = []

            # present the differences by comparing the opcodes
            for op_kind, i1, i2, j1, j2 in all_ops:
                if op_kind == 'equal':
                    comp_chars.append(word1[i1:i2])
                    skeleton.append(word1[i1:i2])
                elif op_kind == 'replace':
                    alternation = (word1[i1:i2], word2[j1:j2])
                    comp_chars.append(alternation)
                    alternations.append(alternation)

            word_pair = WordPair(word1, word2,
                                 comp_chars,
                                 skeleton, alternations)
            yield word_pair

def find_patterns(diff_pairs, min_alt_count=2, min_skeleton_count=0):
    # search for ever skeleton/alternation pattern
    # which occurs more than once

    diff_pairs = list(diff_pairs)
    skeletons = Counter()
    alternations = Counter()

    patterns = []

    for word1, word2, comparison, skeleton, alts in diff_pairs:
        # we can only work with one alternation for now
        alternation = alts[0]

        # get the skeleton before and after the alternation
        pre_skeleton, post_skeleton = skeleton
        skeletons[(pre_skeleton, post_skeleton)] += 1
        alternations[alternation] += 1

    # iterate over the pairs again to find patterns
    for word1, word2, comparison, skeleton, alts in diff_pairs:
        alternation = alts[0]
        pre_skeleton, post_skeleton = skeleton
        if (alternations[alternation] >= min_alt_count
            and skeletons[(pre_skeleton, post_skeleton)] > min_skeleton_count):
            patterns.append((word1, word2, comparison,
                             alternations[alternation],
                             skeletons[(pre_skeleton, post_skeleton)]))

    return skeletons, alternations, patterns


def run(language, corpus, min_stem_length):
    corpus = create_wordlist(language, corpus, min_stem_length)[0]
    diff_pairs = find_pairs(corpus)
    skeletons, alternations, patterns = find_patterns(diff_pairs)
    print_patterns(patterns, language)


def print_diff_pairs(diff_pairs):
    for word1, word2, diffs in diff_pairs:
        str_diffs = []
        for element in diffs:
            if isinstance(element, tuple):
                str_diffs.append('/'.join(element))
            else:
                str_diffs.append(element)
        print(word1, word2, str_diffs)

def print_patterns(patterns, language):
    # sort by frequency of alternation pattern
    sorted_patterns = sorted(patterns, key=lambda x: x[3],
                             reverse=True)

    results_dir = Path('results')
    if not results_dir.exists():
        results_dir.mkdir()

    with Path(results_dir, 'apophony_{}.txt'.format(language)).open('w') as new_file:
        for word1, word2, sequence, alt_count, skeleton_count in sorted_patterns:
            pre_skeleton, alternation, post_skeleton = sequence
            joined_alt = '/'.join(alternation)
            print('{} {} {}[{}]{} alternation occurrence: {}; skeleton occurrence: {}'
                  .format(word1, word2, pre_skeleton, joined_alt, post_skeleton,
                          alt_count, skeleton_count),
                  file=new_file)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('language', help='language to analyze')
    arg_parser.add_argument('corpus', help='corpus file to analyze')
    arg_parser.add_argument('-msl', '--min_stem_length',
                            type=int, default=4)
    args = arg_parser.parse_args()
    run(args.language, args.corpus, args.min_stem_length)

