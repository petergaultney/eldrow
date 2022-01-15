#!/usr/bin/env python

import argparse
import re
import string
import json
from itertools import combinations
from typing import Iterator, Tuple, List, Sequence


with open('5_letter_words.txt') as f:
    five_letter_word_list = f.read().splitlines()

with open('dumb_words.txt') as f:
    dumb_words = f.read().splitlines()

with open('counts.json') as f:
    counts = json.loads(f.read())

total_counts = counts['total_counts']

def int_positions(d):
    return {int(pos): c for pos, c in d.items()}

position_counts = int_positions(counts['position_counts'])
reduced_position_counts = int_positions(counts['reduced_position_counts'])  # only more common letters

with open('best_pairs.json') as f:
    # this represents significant computation (on the order of several minutes)
    best_pairs = json.loads(f.read())


# some shorthand
wl = five_letter_word_list
tc = total_counts
pos = position_counts
rpos = reduced_position_counts


def xf_dd_vals(xf, dd):
    def xf_d_vals(d):
        return {k: xf(v) for k, v in d.items()}
    return {dk: xf_d_vals(dv) for dk, dv in dd.items()}


very_unusual_letters = 'vzjxq'

def score_words(*words: str, position_counts: dict = position_counts) -> int:
    """Scores words based on total positional score across the word list.

    Does not help you solve.
    """
    score = 0
    found = set()
    for w in words:
        for i, c in enumerate(w):
            if c not in found:
                found.add(c)
                score += position_counts[i][c]
    return score


def yield_high_tuples(word_list: list = five_letter_word_list, n: int = 2, floor: int = 16000) -> Iterator[Tuple[int, str, str]]:
    for words in combinations(word_list, n):
        score = score_words(*words)
        if score >= floor:
            yield (score, *words)


def best_next_score(word_list: Sequence[str], *words) -> Tuple[int, List[str]]:
    """Determines a best next word score without regard to solving.

    Mostly useful for playing around with different combinations of
    two and three word starts, to find something you actually like.
    """
    high_score = 0
    best_words = list()
    for w_next in word_list:
        score = score_words(*words, w_next)
        if score > high_score:
            high_score = score
            best_words = [w_next]
        elif score == high_score:
            best_words.append(w_next)
    return high_score, best_words


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
    print(regexes)
    for w in wl:
        if all(regex.search(w) for regex in regexes):
            yield w


def options(regex_strs: Sequence[str]) -> list:
    regexes = tuple(re.compile(regex_str) for regex_str in regex_strs)
    return list(find_with_regexes(regexes))


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

def main():
    pass


if __name__ == '__main__':
    main()
