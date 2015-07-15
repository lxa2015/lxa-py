__author__ = 'anton'

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

def find_stems(corpus, min_equal_length=4):
    word_pairs = combinations(corpus, 2)
    stems = RelatedStemCounter()
    all_stems_counted = Counter()

    for word1, word2 in word_pairs:
        if ratio(word1, word2) > 0.5:
            # check if there is an equal chunk
            ops = opcodes(word1, word2)
            equal_ops = [op for op in ops if op[0] == 'equal']
            if len(equal_ops) == 1:
                equal_op = equal_ops[0]
                equal_chunk_length = equal_op[2] - equal_op[1]
                if equal_chunk_length >= min_equal_length:
                    i1, i2 = equal_op[1], equal_op[2]
                    equal_chunk = word1[i1:i2]
                    stems[word1].append(equal_chunk)
                    stems[word2].append(equal_chunk)
                    all_stems_counted[equal_chunk] += 1

    # get rid of 'stems' that appear too frequently
    mean_stem_freq = mean(all_stems_counted.values())
    uncommon_stems = {}
    for word, stem_candidates in stems.related_items(0.8):
        current_stems = []
        for stem_candidate in stem_candidates:
            if all_stems_counted[stem_candidate] < mean_stem_freq:
                current_stems.append(stem_candidate)

        # all of the stems here are common
        if not current_stems:
            if stem_candidates:
                current_stems = list(stem_candidates)
            else:
                current_stems = list(stems[word])
        uncommon_stems[word] = Counter(current_stems)

    # counted_uncommon_stems = Counter(chain.from_iterable(uncommon_stems.values()))

    # pick the most common stem
    optimal_stems = {}
    for word, stem_candidates in uncommon_stems.items():
        try:
            optimal_stem = max(stem_candidates,
                           key=lambda stem: uncommon_stems[word][stem])
        except ValueError:
            # FIXME
            optimal_stem = ''

        optimal_stems[word] = optimal_stem

    return optimal_stems