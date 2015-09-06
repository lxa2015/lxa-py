from collections import Counter
from pathlib import Path

from .lxa5lib import (stdout_list, sorted_alphabetized, SEP_NGRAM,
                     changeFilenameSuffix, json_dump)

#------------------------------------------------------------------------------#
#
#    This program creates a trigram file, bigram file, and a word list.
#
#    Input is a corpus text.
#
#    John Goldsmith and Wang Xiuli 2012
#    Jackson Lee 2014-
#
#------------------------------------------------------------------------------#


def output_ngram(ngram_to_count_sorted, outfilename, intro_string,
        sep, print_stdout):
    print(print_stdout, flush=True)
    with outfilename.open('w') as f:
        print(intro_string, file=f)
        print("# type count: {}".format(len(ngram_to_count_sorted)), file=f)
        for (ngram, freq) in ngram_to_count_sorted:
            print(ngram + sep +  str(freq), file=f)


def main(language=None, corpus=None, datafolder=None, filename=None,
         maxwordtokens=0):

    print("\n*****************************************************\n"
          "Running the ngram component of Linguistica now...\n", flush=True)

    if filename:
        infilename = Path(filename)
        outfolder = Path(infilename.parent, "ngrams")
        outfolderDx1 = Path(infilename.parent, "dx1")
        corpus = infilename.name
    else:
        infilename = Path(datafolder, language, corpus)
        outfolder = Path(datafolder, language, "ngrams")
        outfolderDx1 = Path(datafolder, language, "dx1")

    if not outfolder.exists():
        outfolder.mkdir(parents=True)

    if not outfolderDx1.exists():
        outfolderDx1.mkdir(parents=True)

    if maxwordtokens:
        corpusName = Path(corpus).stem + "_{}-tokens".format(maxwordtokens)
    else:
        corpusName = Path(corpus).stem

    outfilenameWords = Path(outfolder, corpusName + "_words.txt")
    outfilenameBigrams = Path(outfolder, corpusName + "_bigrams.txt")
    outfilenameTrigrams = Path(outfolder, corpusName + "_trigrams.txt")
    outfilenameDx1 = Path(outfolderDx1, corpusName + ".dx1")

    wordDict = Counter()
    trigramDict = Counter()
    bigramDict = Counter()
    sep = SEP_NGRAM
    corpusCurrentSize = 0 # running word token count

    print('Reading the corpus file now...', flush=True)

    with infilename.open() as f:
        for line in f.readlines():
            if maxwordtokens and corpusCurrentSize > maxwordtokens:
                break

            if not line:
                continue

            # TODO: modify/combine these with "scrubbing"
            #   cf. Alchemist and Lxa4
            line = line.replace(".", " . ")
            line = line.replace(",", " , ")
            line = line.replace(";", " ; ")
            line = line.replace("!", " ! ")
            line = line.replace("?", " ? ")
            line = line.replace(":", " : ")
            line = line.replace(")", " ) ")
            line = line.replace("(", " ( ")

            line = line.strip().casefold()

            if not line:
                continue

            words = line.split()
            lenWords = len(words)

            corpusCurrentSize += lenWords

            if lenWords == 1:
                wordDict[words[0]] += 1
                continue
            elif lenWords == 2:
                wordDict[words[0]] += 1
                wordDict[words[1]] += 1
                bigramDict[words[0] + sep + words[1]] += 1
                continue

            # when lenWords >= 3...
            for i in range(lenWords-2):

                word1 = words[i]
                word2 = words[i+1]
                word3 = words[i+2]

                wordDict[word3] += 1

                if i == 0:
                    wordDict[word1] += 1
                    wordDict[word2] += 1
                    bigram = word1 + sep + word2
                    bigramDict[bigram] += 1

                bigram = word2 + sep + word3
                trigram = word1 + sep + word2 + sep + word3

                trigramDict[trigram] += 1
                bigramDict[bigram] += 1

    print("\nCompleted counting words, bigrams, and trigrams.", flush=True)
    print("Token count: {}".format(corpusCurrentSize), flush=True)

    intro_string = "# data source: {}\n# token count: {}".format(
        str(infilename), corpusCurrentSize)

    print("Sorting the ngrams...", flush=True)
    wordsSorted = sorted_alphabetized(wordDict.items(),
                                      key=lambda x: x[1], reverse=True)

    bigramsSorted = sorted_alphabetized(bigramDict.items(),
                                        key=lambda x: x[1], reverse=True)

    trigramsSorted = sorted_alphabetized(trigramDict.items(),
                                         key=lambda x: x[1], reverse=True)

    # print txt outputs
    output_ngram(wordsSorted, outfilenameWords, intro_string, sep,
        "Outputting unigrams...")

    output_ngram(bigramsSorted, outfilenameBigrams, intro_string, sep,
        "Outputting bigrams...")

    output_ngram(trigramsSorted, outfilenameTrigrams, intro_string, sep,
        "Outputting trigrams...")

    # print dx1 output
    print("Outputting the dx1 file...", flush=True)
    with outfilenameDx1.open('w') as f:
        for (word, freq) in wordsSorted:
            print(word, freq, ' '.join(word), file=f)

    # print json outputs
    print("Outputting the JSON files...", flush=True)
    with changeFilenameSuffix(outfilenameWords, ".json").open('w') as f:
        json_dump(wordDict, f)

    with changeFilenameSuffix(outfilenameBigrams, ".json").open('w') as f:
        json_dump(bigramDict, f)

    with changeFilenameSuffix(outfilenameTrigrams, ".json").open('w') as f:
        json_dump(trigramDict, f)

    stdout_list("Output files:", outfilenameWords,
                outfilenameBigrams, outfilenameTrigrams, outfilenameDx1,
                changeFilenameSuffix(outfilenameWords, ".json"),
                changeFilenameSuffix(outfilenameBigrams, ".json"),
                changeFilenameSuffix(outfilenameTrigrams, ".json"))

