#!/usr/bin/env python

import argparse
import re
import string
import json
from collections import defaultdict
from itertools import combinations, chain
from typing import Iterator, Tuple, List, Sequence, Dict, Set, Callable


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


PositionScores = Dict[int, Dict[str, int]]


def construct_position_freqs(word_list: List[str], decimal_points=5) -> PositionScores:
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


def score_words(position_scores: dict = position_scores) -> Callable[[Tuple[str, ...]], float]:
    """Scores words based on total positional score across the word list."""
    def _score_words(*words: str) -> float:
        score = 0
        scored_in_position = defaultdict(lambda: defaultdict(lambda: False))

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
                if scored_in_position[i][c]:
                    continue
                scored_in_position[i][c] = True
                word_score += pos_score
            return word_score

        return round(sum(score_word(w) for w in words), 3)

    return _score_words


def score_for_novelty(position_scores: dict = position_scores) -> Callable[[Tuple[str, ...]], float]:
    """Scores words based on novelty of each character.

    In other words, we want as many different characters as possible,
    with as high a score in each position as possible.
    """
    def _score_for_novelty(*words: str) -> float:
        score = 0.0
        characters_scored = set()

        def score_word(word: str) -> float:
            wscore = 0.0
            sorted_pos_scores = sorted([(position_scores[i].get(c, 0.0), i, c) for i, c in enumerate(word)], reverse=True)
            for pos_score, i, c in sorted_pos_scores:
                if c in characters_scored:
                    continue
                characters_scored.add(c)
                wscore += pos_score
            return wscore

        return round(sum(score_word(word) for word in words), 3)

    return _score_for_novelty


def high_score_tuples(word_list: list = five_letter_word_list, n: int = 2) -> List[Tuple[int, str, str]]:
    scored = list()
    for words in combinations(word_list, n):
        score = score_for_novelty()(*words)
        scored.append((score, *words))
    return sorted(scored)


def best_next_score(word_list: Sequence[str], *starting_words, scorer = score_words()) -> List[Tuple[int, str]]:
    """Determines a best next word score without regard to solving.

    Mostly useful for playing around with different combinations of
    two and three word starts, to find something you actually like.
    """
    best_words = list()
    for w_next in word_list:
        best_words.append((scorer(*starting_words, w_next), w_next))
    return sorted(best_words)


def _remove_solved(position_scores: PositionScores) -> PositionScores:
    return {pos: (val if len(val) > 1 else dict()) for pos, val in position_scores.items()}


def _replace_solved_with_average_totals(position_scores: PositionScores) -> PositionScores:
    avg_unsolved_total = defaultdict(int)
    solved_letters = {list(letters.keys())[0] for _, letters in position_scores.items() if len(letters) == 1}
    for pos, scores in position_scores.items():
        if len(scores) > 1:
            for letter, score in scores.items():
                if letter not in solved_letters:
                    avg_unsolved_total[letter] += score / len(position_scores)
    return {pos: (scores if len(scores) > 1 else dict(avg_unsolved_total)) for pos, scores in position_scores.items()}


def solver_regexes(green: dict, yellow: dict, gray: set, n: int = 5) -> Tuple[str, ...]:
    yellow_chars = set(chain(*yellow.values()))
    all_known = len(green) + len(yellow_chars) == n
    # if the number of green chars plus the number of yellow chars is N, then we
    # don't need to accept anything other than those chars.
    def pos(i):
        if i in green:
            return green[i]
        char_regex = '['
        for c in (string.ascii_lowercase if not all_known else yellow_chars):
            if c in yellow.get(i, list()):
                continue
            if c in gray and c not in yellow_chars:
                # if a character appeared gray, that might be because
                # it was in a guess with two of those same character,
                # and only one appears in the word.
                continue
            char_regex += c
        char_regex += ']'
        return char_regex
    return (''.join(pos(i) for i in range(n)),) + tuple(c for c in (yellow_chars if not all_known else []))


def find_with_regexes(regexes: tuple, wl: list = five_letter_word_list):
    for w in wl:
        if all(regex.search(w) for regex in regexes):
            yield w


def given(*guesses, n: int = 5) -> Tuple[Dict[int, str], Dict[int, Set[str]], Set[str]]:
    """Format:

    lowercase letters for incorrect guesses.

    uppercase letters for correct (green) guesses.

    yellow (letter is present, but not the correct position) guesses
    are letters encased in parentheses.

    Example:

    If the correct answer is BROWN, B(OR)oN would be the guess representation for 'boron'.
    """
    green = dict()
    yellow = dict()
    gray = set()
    for guess in guesses:
        is_yellow = False
        i = 0
        for c in guess:
            if c == '(':
                assert not is_yellow, guess
                is_yellow = True
            elif c == ')':
                assert is_yellow, guess
                is_yellow = False
            else:
                if is_yellow:
                    if i not in yellow:
                        yellow[i] = set()
                    yellow[i].add(c.lower())
                elif c in string.ascii_uppercase: # yellow
                    assert c in string.ascii_letters
                    assert green.get(i) in (c.lower(), None)
                    green[i] = c.lower()
                else:
                    gray.add(c)
                i += 1
    return green, yellow, gray


def options(regex_strs: Sequence[str]) -> list:
    regexes = tuple(re.compile(regex_str) for regex_str in regex_strs)
    return list(find_with_regexes(regexes))


def _to_word(guess: str) -> str:
    return guess.replace('(', '').replace(')', '').lower()


def _simple_words(*guesses) -> List[str]:
    return [_to_word(guess) for guess in guesses]


def answer(solution: str, guess: str) -> str:
    if len(solution) != len(guess):
        return guess

    guess = _to_word(guess)
    char_counts = defaultdict(int)
    for c in solution:
        char_counts[c] += 1

    for guess_c, c in zip(guess, solution):
        if guess_c == c:
            char_counts[c] -= 1

    results = list()
    is_yellow = False

    def end_yellow():
        nonlocal is_yellow
        if is_yellow:
            results.append(')')
            is_yellow = False

    def start_yellow():
        nonlocal is_yellow
        if not is_yellow:
            results.append('(')
            is_yellow = True

    for guess_c, c in zip(guess, solution):
        if guess_c == c:
            end_yellow()
            results.append(c.upper())
        elif char_counts.get(guess_c):
            start_yellow()
            results.append(guess_c.upper())
            char_counts[guess_c] -= 1
        else:
            end_yellow()
            results.append(guess_c.lower())

    end_yellow()
    return ''.join(results)


def colorize(*guesses: str):
    green, yellow, gray = given(*guesses)
    CGREEN  = '\33[32m'
    CYELLOW = '\33[33m'
    CRED    = '\33[31m'
    CEND    = '\33[0m'
    colorized = list()
    for guess in guesses:
        color_guess = ''
        for i, c in enumerate(_to_word(guess)):
            if c == green.get(i):
                color_guess += CGREEN
                color_guess += c.upper()
                color_guess += CEND
            elif c in yellow.get(i, set()):
                color_guess += CYELLOW
                color_guess += c.upper()
                color_guess += CEND
            elif c in gray:
                color_guess += CRED
                color_guess += c.lower()
                color_guess += CEND
            else:
                assert False, (guess, c, i)
        colorized.append(color_guess)
    return colorized


from IPython.core.magic import Magics, magics_class, line_magic


@magics_class
class IpythonSolver(Magics):
    def __init__(self, shell, guesses: List[str] = list()):
        # You must call the parent constructor
        super(IpythonSolver, self).__init__(shell)
        self._guesses = guesses or list()
        self.ideas = list()
        self.limit = 30
        self._solution = ''
        self._ignored = set()

    def _cur_options(self) -> List[str]:
        return [w for w in options(solver_regexes(*given(*self._guesses))) if w not in self._ignored]

    def format(self, guess):
        assert self._solution
        return answer(self._solution, guess) or guess

    @line_magic
    def ignore(self, words):
        self._ignored |= set(words.split())

    @line_magic
    def limit(self, line):
        if line:
            self.limit = int(line)
        else:
            return self.limit

    @line_magic
    def solution(self, line):
        """For testing purposes. If you know the answer and want to manually
        try to 'discover' it using various tools, you can put the
        solution in, and that will make typing easier.
        """
        if line:
            self._solution = line
        else:
            import getpass
            self._solution = getpass.getpass('Solution? ')

    @line_magic
    def p(self, _):
        for colorized in colorize(*self._guesses):
            print(colorized)

    @line_magic
    def words(self, _):
        return _simple_words(*self._guesses)

    @line_magic
    def score(self, words):
        return score_words(construct_position_freqs(self._cur_options()))(*words.split())

    @line_magic
    def info(self, words):
        return score_for_novelty(
            _replace_solved_with_average_totals(construct_position_freqs(self._cur_options()))
        )(*words.split())

    @line_magic
    def guesses(self, line):
        print(f'# options: {len(self._cur_options())}')
        self.p(None)
        return self._guesses

    @line_magic
    def guess(self, line):
        if line:
            if self._solution:
                line = self.format(line)
            if _to_word(line) not in five_letter_word_list:
                return None
            self._guesses.append(line)
        return self.guesses(None)

    @line_magic
    def g(self, line):
        return self.guess(line)

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
        opts = self._cur_options()
        return opts, len(opts)

    @line_magic
    def best_options(self, limit):
        """Scores all remaining options against the position scores for remaining words"""
        remaining_words = self._cur_options()
        limit = int(limit) if limit else self.limit
        return best_next_score(
            remaining_words,
            *_simple_words(*self._guesses),
            scorer=score_words(construct_position_freqs(remaining_words)),
        )[-limit:]

    @line_magic
    def best_info(self, limit):
        """Uses full word list to maximize information score, rather than limiting to words it 'could' be"""
        opts = self._cur_options()
        limit = int(limit) if limit else self.limit
        return best_next_score(
            five_letter_word_list,
            *_simple_words(*self._guesses),
            scorer=score_for_novelty(_replace_solved_with_average_totals(construct_position_freqs(opts))),
        )[-limit:]

    @line_magic
    def pop(self, count):
        count = int(count) if count else 1
        for _ in range(count):
            idea = self._guesses.pop()
            if idea not in self.ideas:
                self.ideas.append(idea)
        return self.g(None)

    @line_magic
    def scores(self, _):
        return construct_position_freqs(self._cur_options())

    @line_magic
    def reset(self, _):
        self._guesses = list()
        self.ideas = list()
        self._solution = ''


def load_ipython_extension(ipython):  # magic name
    ipython.register_magics(IpythonSolver)

try:
    get_ipython().run_line_magic('load_ext', 'eldrow')
except:
    pass

def main():
    pass


if __name__ == '__main__':
    main()
