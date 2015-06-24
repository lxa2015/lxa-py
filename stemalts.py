__author__ = 'Anton Melnikov'

from argparse import ArgumentParser
from collections import Counter, namedtuple, defaultdict
from itertools import combinations, chain
from pathlib import Path
from pprint import pprint
from statistics import mean

from lxa5_module import read_word_freq_file

from Levenshtein import opcodes, editops, ratio

WordPair = namedtuple('WordPair', ['word1', 'word2',
                                   'comparison',
                                   'skeleton', 'alternation'])
WordPattern = namedtuple('WordPattern', ['word_pair',
                                         'alternation_freq',
                                         'skeleton_freq'])
RelatedStems = namedtuple('RelatedStems', 'related_words stems')


class RelatedStemCounter(defaultdict):

    def __init__(self):
        super().__init__(list)

    def get_related(self, word, min_similarity_ratio=0.65) -> RelatedStems:
        related_words = set()
        all_related_stems = []

        for other_word in self:
            current_stems = []

            if (word != other_word
                and ratio(word, other_word) >= min_similarity_ratio):
                for stem_candidate in self[other_word]:
                    if stem_candidate in word:
                        current_stems.append(stem_candidate)
                        related_words.add(other_word)
            all_related_stems += current_stems

        related_stems = RelatedStems(related_words, all_related_stems)
        return related_stems

    def get_related_once(self, word, min_similarity_ratio=0.65,
                        words_covered=None):

        related_stems = self.get_related(word, min_similarity_ratio)
        related_words, all_related_stems = related_stems

        for other_word in related_words:
            if other_word != word:
                related_related = self.get_related(other_word, min_similarity_ratio)
                rr_words, rr_stems = related_related
                for stem in rr_stems:
                    if stem in word:
                        all_related_stems.append(stem)

        return all_related_stems



    def count_related(self, word, min_similarity_ratio=0.65) -> Counter:
        all_related_stems = self.get_related_once(word, min_similarity_ratio)
        return Counter(all_related_stems)

    def related_items(self, min_similarity_ratio=0.65):
        for word in self:
            related_stems = self.get_related_once(word, min_similarity_ratio)
            yield word, related_stems

    def counted_related_items(self, min_similarity_ratio=0.65):
        for word, stems in self.related_items(min_similarity_ratio=0.65):
            yield word, Counter(stems)

def are_similar(word1: str, word2: str, max_diff_length=2,
                allowed_op_kinds=None) -> (bool, tuple):
    if not allowed_op_kinds:
        # (see http://www.coli.uni-saarland.de/courses/LT1/2011/slides/Python-Levenshtein.html)
        allowed_op_kinds = ('equal', 'replace', 'equal')

    all_ops = opcodes(word1, word2)
    op_kinds = tuple(op[0] for op in all_ops)

    # check that the structure of operations is allowed
    if op_kinds == allowed_op_kinds:

        # check that the different chunks are under the maximum allowed length
        i1, i2  = all_ops[1][1], all_ops[1][2]
        chunk_length = i2 - i1
        if chunk_length <= max_diff_length:
            return True, all_ops

    return False, None

def make_pair(word1: str, word2: str) -> WordPair:
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

        return word_pair

def find_pairs(corpus: list):
    word_pairs = combinations(corpus, 2)
    alt_pairs = (make_pair(word1, word2) for word1, word2 in word_pairs)

    # weed out "None"s
    for pair in alt_pairs:
        if pair:
            yield pair

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
    for word_pair in diff_pairs:
        alternation = word_pair.alternation[0]
        pre_skeleton, post_skeleton = word_pair.skeleton
        if (alternations[alternation] >= min_alt_count
            and skeletons[(pre_skeleton, post_skeleton)] > min_skeleton_count):

            # put them in a tuple
            alternation_freq = alternations[alternation]
            skeleton_freq = skeletons[(pre_skeleton, post_skeleton)]
            pattern = WordPattern(word_pair, alternation_freq, skeleton_freq)
            patterns.append(pattern)

    return skeletons, alternations, patterns

def filter_patterns(patterns, min_alt_freq=5, min_skeleton_freq=3):
    for pattern in patterns:
        if (pattern.skeleton_freq >= min_skeleton_freq
            and pattern.alternation_freq >= min_alt_freq):
            yield pattern

def run(corpus_path, min_stem_length, max_words,
        min_alternation_freq, min_skeleton_freq,
        verbose=False):

    if verbose:
        print('assembling the corpus...')
    corpus_path = Path(corpus_path)
    word_freqs = read_word_freq_file(corpus_path,
                             minimum_stem_length=min_stem_length)
    corpus = sorted(w for w in word_freqs if w.isalpha())

    if verbose:
        print('finding alternation pairs...')

    diff_pairs = find_pairs(corpus)

    if verbose:
        print('finding patterns in pairs...')

    skeletons, alternations, patterns = find_patterns(diff_pairs)

    if verbose:
        print('filtering the patterns')

    filtered_patterns = filter_patterns(patterns,
                                        min_alternation_freq,
                                        min_skeleton_freq)

    corpus_name = corpus_path.stem
    print_patterns(filtered_patterns, corpus_name)


def print_diff_pairs(diff_pairs):
    for word1, word2, diffs in diff_pairs:
        str_diffs = []
        for element in diffs:
            if isinstance(element, tuple):
                str_diffs.append('/'.join(element))
            else:
                str_diffs.append(element)
        print(word1, word2, str_diffs)

def print_patterns(patterns, name):
    # sort by frequency of alternation pattern
    sorted_patterns = sorted(patterns, key=lambda x: (x.alternation_freq,
                                                      x.word_pair.alternation),
                             reverse=True)

    results_dir = Path('results')
    if not results_dir.exists():
        results_dir.mkdir()

    new_file_path = Path(results_dir, 'apophony_{}.txt'.format(name))
    with new_file_path.open('w') as new_file:
        for word_pair, alt_count, skeleton_count in sorted_patterns:
            pre_skeleton, alternation, post_skeleton = word_pair.comparison
            joined_alt = '/'.join(alternation)
            print('{} {}\t{}[{}]{}\talternation occurrence: {};\tskeleton occurrence: {}'
                  .format(word_pair.word1, word_pair.word2,
                          pre_skeleton, joined_alt, post_skeleton,
                          alt_count, skeleton_count),
                  file=new_file)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('corpus', help='corpus file to analyze')
    arg_parser.add_argument('-msl', '--min-stem-length',
                            type=int, default=4)
    arg_parser.add_argument('-v', '--verbose',
                            action='store_true', default=False)
    arg_parser.add_argument('--min-alternation-freq',
                            type=int, default=5)
    arg_parser.add_argument('--min-skeleton-freq',
                            type=int, default=3)
    args = arg_parser.parse_args()
    run(args.corpus, args.min_stem_length,
        args.min_alternation_freq, args.min_skeleton_freq,
        args.verbose)

