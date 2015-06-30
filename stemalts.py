__author__ = 'Anton Melnikov'

from argparse import ArgumentParser
from collections import Counter, namedtuple, defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from itertools import combinations, islice, chain
from math import factorial
from os import cpu_count
from pathlib import Path
from types import GeneratorType
from pprint import pprint, pformat

from lxa5_module import read_word_freq_file

from Levenshtein import opcodes

WordPair = namedtuple('WordPair', ['word1', 'word2',
                                   'comparison',
                                   'skeleton', 'alternation'])
WordPattern = namedtuple('WordPattern', ['word_pair',
                                         'alternation_freq',
                                         'skeleton_freq'])

class AlternationPairs:
    def __init__(self):
        self.__pairs = {}

        self.skeletons = defaultdict(set)
        self.alternations = defaultdict(set)

        self._skeleton_counter = Counter()
        self._alternation_counter = Counter()

    def __repr__(self):
        return 'AlternationPairs({})'.format(pformat(self.__pairs))

    def __len__(self):
        return len(self.__pairs)

    def __iter__(self):
        return iter(self.__pairs.values())

    def __contains__(self, item: WordPair):
        item_hash = hash(item)
        return item_hash in self.__pairs


    def add(self, item: WordPair):
        # store the index to this pair, which is the current size of the list of pairs
        # only add the item if it's not already contained by the list
        if item not in self:
            skeleton = item.skeleton
            alternation = item.alternation
            item_hash = hash(item)

            self.__pairs[item_hash] = item

            self.alternations[alternation].add(item_hash)
            self._alternation_counter[alternation] += 1

            self.skeletons[skeleton].add(item_hash)
            self._skeleton_counter[skeleton] += 1

    def get_pairs(self, skeleton=None, alternation=None) -> GeneratorType:
        if skeleton and alternation:
            # get the intersection hashes
            hashes = self.skeletons[skeleton].intersection(
                self.alternations[alternation])
        elif skeleton:
            hashes = self.skeletons[skeleton]
        elif alternation:
            hashes = self.alternations[alternation]
        else:
            return

        # get all the items with those hashes
        for item_hash in hashes:
            yield self.__pairs[item_hash]

    def get_one(self, skeleton=None, alternation=None) -> WordPair:
        pairs = self.get_pairs(skeleton=skeleton, alternation=alternation)
        return pairs.__next__()

    def itersorted(self, key='alternation_freq', reverse=True):

        if key == 'alternation_freq':
            for alternation, count in self._alternation_counter.most_common():
                for pair in self.get_pairs(alternation=alternation):
                    yield pair
        elif key == 'skeleton_freq':
            for skeleton, count in self._skeleton_counter.most_common():
                for pair in self.get_pairs(skeleton=skeleton):
                    yield pair
        else:
            return

    def remove(self, item: WordPair):
        """
        This method should not be used directly.
        """
        item_hash = hash(item)
        del self.__pairs[item_hash]

        self.alternations[item.alternation].remove(item_hash)
        self.skeletons[item.skeleton].remove(item_hash)

        self._alternation_counter[item.alternation] -= 1
        self._skeleton_counter[item.skeleton] -= 1


    def filter_pairs(self, min_alternation_frequency, min_skeleton_frequency):
        keep_going = True

        # keep filtering while there are pairs to remove
        while keep_going:
            keep_going = False
            to_remove = []

            # remove all skeletons that don't occur in many pairs

            for alternation, count in self._alternation_counter.items():
                if count < min_alternation_frequency:
                    to_remove.append(self.get_pairs(alternation=alternation))

            for skeleton, count in self._skeleton_counter.items():
                if count < min_skeleton_frequency:
                    to_remove.append(self.get_pairs(skeleton=skeleton))

            to_remove = set(chain.from_iterable(to_remove))
            n = 0
            for n, pair in enumerate(to_remove, start=1):
                self.remove(pair)
            if n:
                keep_going = True

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
        i1, i2 = all_ops[1][1], all_ops[1][2]
        chunk_length = i2 - i1
        if chunk_length <= max_diff_length:
            return True, all_ops

    return False, None


def make_pair(word1: str, word2: str, max_diff_length=2) -> WordPair:
    result = are_similar(word1, word2, max_diff_length)
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
                             tuple(comp_chars),
                             tuple(skeleton),
                             tuple(alternations))

        return word_pair


def make_pairs(sequence, max_alternation_length=2) -> list:
    """
    Used by the parallel version
    :param pair_tuple:
    :return:
    """
    pairs = []
    for word1, word2 in sequence:
        pair = make_pair(word1, word2, max_alternation_length)
        if pair:
            pairs.append(pair)
    return pairs


def make_chunks(sequence, num_chunks, num_elements):
    begin = 0
    chunk_size = round(num_elements / num_chunks)
    end = chunk_size
    for n in range(num_elements):
        if n > 0 and n % chunk_size == 0:
            yield islice(sequence, begin, end)
            begin = end
            end += chunk_size


def find_pairs(corpus: list, max_alternation_length=2,
               verbose=False) -> AlternationPairs:
    """
    :param corpus, max_alternation_length=2, verbose=False:
    :return diff_pairs:
    """

    word_pairs = combinations(corpus, 2)
    num_words = len(corpus)
    # n! / r! / (n-r)!
    num_pairs = factorial(num_words) // 2 // factorial(num_words - 2)
    if verbose:
        print('({:,} pairs to analyse)'.format(num_pairs))

    # put the combinations in chunks for parallel processing
    pair_chunks = make_chunks(word_pairs, cpu_count(), num_pairs)

    # 'partialise' the make_pairs function to include the max_alternation_length
    make_pairs_l = partial(make_pairs,
                           max_alternation_length=max_alternation_length)
    # process each chunk of combinations in parallel
    with ProcessPoolExecutor() as executor:
        alt_pairs = executor.map(make_pairs_l, pair_chunks)
    # flatten the pairs
    all_pairs = chain.from_iterable(alt_pairs)

    diff_pairs = AlternationPairs()

    # add pairs and count the frequencies of alternations and skeletons
    for pair in all_pairs:
        word1, word2, comparison, skeleton, alts = pair
        # we can only work with one alternation for now
        alternation = alts[0]

        # get the skeleton before and after the alternation
        one_alt_pair = WordPair(word1, word2, comparison,
                                skeleton, alternation)
        diff_pairs.add(one_alt_pair)

    return diff_pairs


def filter_pairs(diff_pairs: AlternationPairs,
                 min_alt_freq=5, min_skeleton_freq=3):
    # search for ever skeleton/alternation pattern
    # which occurs more than the given amount
    diff_pairs.filter_pairs(min_alt_freq, min_skeleton_freq)


def combine_patterns(pairs: AlternationPairs) -> dict:
    combined_patterns = {}
    for skeleton, _ in pairs._skeleton_counter.most_common():
        skeleton_pairs = pairs.get_pairs(skeleton=skeleton)
        word_pairs = []
        alternations = []

        for pair in skeleton_pairs:
            word_pairs += [pair.word1, pair.word2]
            alternations.append('/'.join(pair.alternation))

        if word_pairs:
            # put them all together
            skeleton = '_'.join(skeleton)
            combined_patterns[skeleton] = (set(alternations), set(word_pairs))

    return combined_patterns


def run(corpus_path, min_stem_length, max_alternation_length,
        min_alternation_freq, min_skeleton_freq,
        verbose=False):
    if verbose:
        print('assembling the corpus...')
    corpus_path = Path(corpus_path)
    word_freqs = read_word_freq_file(corpus_path,
                                     minimum_stem_length=min_stem_length)
    corpus = sorted(w for w in word_freqs if w.isalpha())

    if verbose:
        print('finding pairs in alternations...')

    diff_pairs = find_pairs(corpus,
                             max_alternation_length=max_alternation_length,
                             verbose=verbose)
    if verbose:
        print('finding patterns in pairs...')

    filter_pairs(diff_pairs,
                         min_alt_freq=min_alternation_freq,
                         min_skeleton_freq=min_skeleton_freq)
    if verbose:
        print('combining the patterns by skeletons...')

    combined_patterns = combine_patterns(diff_pairs)

    if verbose:
        print('writing the patterns...')

    corpus_name = corpus_path.stem
    print_patterns(diff_pairs, combined_patterns, corpus_name)

    if verbose:
        print('done')

def print_diff_pairs(diff_pairs):
    for word1, word2, diffs in diff_pairs:
        str_diffs = []
        for element in diffs:
            if isinstance(element, tuple):
                str_diffs.append('/'.join(element))
            else:
                str_diffs.append(element)
        print(word1, word2, str_diffs)


def print_patterns(patterns: AlternationPairs,
                   combined_skeletons: dict,
                   name):
    # sort by frequency of alternation patterns

    results_dir = Path('results')
    if not results_dir.exists():
        results_dir.mkdir()

    new_file_path = Path(results_dir, 'apophony_{}.txt'.format(name))
    with new_file_path.open('w') as new_file:
        for word_pair in patterns.itersorted():
            pre_skeleton, alternation, post_skeleton = word_pair.comparison
            joined_alt = '/'.join(alternation)
            alt_count = patterns._alternation_counter[word_pair.alternation]
            skeleton_count = patterns._skeleton_counter[word_pair.skeleton]

            print('{} {}\t{}[{}]{}\talternation occurrence: {};\tskeleton occurrence: {}'
                  .format(word_pair.word1, word_pair.word2,
                          pre_skeleton, joined_alt, post_skeleton,
                          alt_count, skeleton_count),
                  file=new_file)

        print('*****\ncombined skeletons:', file=new_file)
        pprint(combined_skeletons, stream=new_file, width=70)

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
    arg_parser.add_argument('-mal', '--max-alternation-length',
                            type=int, default=2,
                            help='maximum length of an alternation')
    args = arg_parser.parse_args()
    run(args.corpus, args.min_stem_length, args.max_alternation_length,
        args.min_alternation_freq, args.min_skeleton_freq,
        args.verbose)
