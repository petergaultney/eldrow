#!/usr/bin/env python

import argparse
import re
import string
import json
from collections import defaultdict
from itertools import combinations
from typing import Iterator, Tuple, List, Sequence, Dict


with open('5_letter_words.txt') as f:
    five_letter_word_list = f.read().splitlines()

with open('dumb_words.txt') as f:
    dumb_words = f.read().splitlines()

with open('counts.json') as f:
    counts = json.loads(f.read())

total_counts = counts['total_counts']


def _sort_dict_by_values(d):
    return {k: v for k, v in sorted(d.items(), key=lambda item: item[1])}


def _xf_dict_vals(xf, d):
    return {k: xf(v) for k, v in d.items()}


def _xf_dd_vals(xf, dd):
    def xf_d_vals(d):
        return {k: xf(v) for k, v in d.items()}
    return {dk: xf_d_vals(dv) for dk, dv in dd.items()}


PositionCounts = Dict[int, Dict[str, int]]


def construct_position_freqs(word_list: List[str], decimal_points=5) -> PositionCounts:
    counts = defaultdict(lambda: defaultdict(int))
    for word in word_list:
        for i, char in enumerate(word):
            counts[i][char] += 1

    def count_to_freq(count: int) -> float:
        return round(count / len(word_list), decimal_points)

    return {
        k: _xf_dict_vals(count_to_freq, _sort_dict_by_values(v))
        for k, v in counts.items()
    }


position_scores = construct_position_freqs(five_letter_word_list)

with open('best_pairs.json') as f:
    # this represents significant computation (on the order of several minutes)
    best_pairs = json.loads(f.read())


# some shorthand
wl = five_letter_word_list
tc = total_counts
pos = position_scores


very_unusual_letters = 'vzjxq'

def score_words(*words: str, position_scores: dict = position_scores) -> float:
    """Scores words based on total positional score across the word list.

    Only scores a character the first time it appears.
    """
    score = 0
    times_scored = defaultdict(int)

    def score_word(w):
        word_score = 0
        for i, c in enumerate(w):
            if i not in position_scores:
                break
            pos = position_scores[i]
            if c not in pos:
                # letter literally not an option in this location.
                # it gets no score here, and will be fully scored
                # elsewhere.
                continue
            pos_score = pos[c]
            times_scored[c] += 1
            word_score += pos_score / times_scored[c]
        return word_score

    for w in words:
        score += score_word(w)
    return round(score, 3)


def yield_high_tuples(word_list: list = five_letter_word_list, n: int = 2) -> Iterator[Tuple[int, str, str]]:
    for words in combinations(word_list, n):
        score = score_words(*words)
        yield (score, *words)


def best_next_score(word_list: Sequence[str], *starting_words, position_scores=position_scores) -> List[Tuple[int, str]]:
    """Determines a best next word score without regard to solving.

    Mostly useful for playing around with different combinations of
    two and three word starts, to find something you actually like.
    """
    best_words = list()
    for w_next in word_list:
        score = score_words(*starting_words, w_next, position_scores=position_scores)
        best_words.append((score, w_next))
    return sorted(best_words)


def solver_regexes(green: dict, yellow: dict, gray: set, n: int = 5) -> Tuple[str, ...]:
    def pos(i):
        if i in green:
            return green[i]
        char_regex = '['
        for c in string.ascii_lowercase:
            if c in gray:
                continue
            not_here = yellow.get(i, list())
            if c in not_here:
                continue
            char_regex += c
        char_regex += ']'
        return char_regex
    yellow_chars = set()
    for chars in yellow.values():
        yellow_chars |= chars
    return (''.join(pos(i) for i in range(n)),) + tuple(c for c in yellow_chars)


def find_with_regexes(regexes: tuple, wl: list = five_letter_word_list):
    for w in wl:
        if all(regex.search(w) for regex in regexes):
            yield w


def given(*guesses, n: int = 5) -> Tuple[dict, dict, str]:
    """Format:

    lowercase letters for incorrect guesses.

    uppercase letters for yellow guesses.

    space followed by letter for correct (green) guesses.
    """
    green = dict()
    yellow = dict()
    gray = ''
    for guess in guesses:
        bare_guess = guess.replace(' ', '')
        assert len(bare_guess) == n
        is_green = False
        i = 0
        for c in guess:
            if is_green:
                assert c != ' '
                assert green.get(i) in (c.lower(), None)
                green[i] = c.lower()
                is_green = False
            elif c in string.ascii_uppercase: # yellow
                if i not in yellow:
                    yellow[i] = set()
                yellow[i].add(c.lower())
            else:
                gray += c
            if c == ' ':
                is_green = True
            else:
                i += 1
    return green, yellow, gray


def options(regex_strs: Sequence[str]) -> list:
    regexes = tuple(re.compile(regex_str) for regex_str in regex_strs)
    return list(find_with_regexes(regexes))


def _simple_words(*guesses) -> List[str]:
    return [guess.replace(' ', '').lower() for guess in guesses]


from IPython.core.magic import Magics, magics_class, line_magic


@magics_class
class IpythonSolver(Magics):
    def __init__(self, shell, guesses: List[str] = list()):
        # You must call the parent constructor
        super(IpythonSolver, self).__init__(shell)
        self._guesses = guesses or list()
        self.ideas = list()
        self.limit = 30

    def _cur_options(self):
        return options(solver_regexes(*given(*self._guesses)))

    @line_magic
    def limit(self, line):
        self.limit = int(line)

    @line_magic
    def guesses(self, line):
        return self._guesses

    @line_magic
    def words(self, _):
        return _simple_words(*self._guesses)

    @line_magic
    def score(self, words):
        return score_words(*words.split(), position_scores=construct_position_freqs(self._cur_options()))

    @line_magic
    def guess(self, line):
        self._guesses.append(line)
        return self._guesses

    @line_magic
    def g(self, line):
        if line:
            return self.guess(line)
        return self._guesses

    @line_magic
    def ideas(self, _):
        return [f'{idea} ({i + 1})' for i, idea in enumerate(self.ideas)]

    @line_magic
    def idea(self, line):
        idea_num = int(line)
        if idea_num > 0 and idea_num <= len(self.ideas):
            self.guess(self.ideas[idea_num - 1])

    @line_magic
    def options(self, _):
        return self._cur_options()

    @line_magic
    def best_options(self, limit):
        """Scores all remaining options against the position scores for remaining words"""
        remaining_words = self._cur_options()
        limit = int(limit) if limit else self.limit
        return best_next_score(
            remaining_words,
            *_simple_words(*self._guesses),
            position_scores=construct_position_freqs(remaining_words),
        )[-limit:]

    @line_magic
    def best_info(self, limit):
        """Uses full word list to maximize information score, rather than limiting to words it 'could' be"""
        opts = self._cur_options()
        limit = int(limit) if limit else self.limit
        return best_next_score(
            five_letter_word_list,
            *_simple_words(*self._guesses),
            position_scores=construct_position_freqs(opts)
        )[-limit:]

    @line_magic
    def pop(self, _):
        idea = self._guesses.pop()
        if idea not in self.ideas:
            self.ideas.append(idea)
        print(self._guesses)

    @line_magic
    def scores(self, _):
        return construct_position_freqs(self._cur_options())

    @line_magic
    def reset(self, _):
        self._guesses = list()
        self.ideas = list()


def load_ipython_extension(ipython):  # magic name
    ipython.register_magics(IpythonSolver)


def main():
    pass


if __name__ == '__main__':
    main()
