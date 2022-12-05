with open("5_letter_words.txt") as f:
    five_letter_word_list = tuple(f.read().splitlines())

with open("sols.txt") as f:
    sols = tuple(f.read().splitlines())

with open("other.txt") as f:
    sols = tuple(sorted(set(sols) | set(f.read().splitlines())))

with open("dumb_words.txt") as f:
    dumb_words = tuple(f.read().splitlines())
