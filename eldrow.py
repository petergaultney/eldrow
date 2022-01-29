#!/usr/bin/env python

import argparse
import re
import string
import json
import random
import typing as ty
from collections import defaultdict
from copy import deepcopy
from itertools import combinations, chain
from typing import Iterator, Tuple, List, Sequence, Dict, Set, Callable


with open('5_letter_words.txt') as f:
    five_letter_word_list = f.read().splitlines()

with open('sols.txt') as f:
    sols = f.read().splitlines()

with open('dumb_words.txt') as f:
    dumb_words = f.read().splitlines()

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

# some shorthand
wl = five_letter_word_list
pos = position_scores
ALPHA = set(string.ascii_lowercase)


__very_unusual_letters = 'vzjxq'


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


def regexes2(positions, counts):
    def pos(i):
        return '[' + ''.join(positions[i]) + ']'
    return (''.join((pos(i) for i in positions)), *tuple(counts))


PositionEliminations = ty.Dict[int, ty.Set[str]]
CharacterCount = ty.Dict[str, int]
Constraint = ty.Tuple[PositionEliminations, CharacterCount]


def parse(guess: str) -> ty.Iterator[ty.Tuple[str, str]]:
    is_yellow = False
    for c in guess:
        if c == '(':
            assert not is_yellow, guess
            is_yellow = True
        elif c == ')':
            assert is_yellow, guess
            is_yellow = False
        else:
            if is_yellow:
                yield 'yellow', c.lower()
            elif c in string.ascii_uppercase:
                yield 'green', c.lower()
            else:
                yield 'gray', c


def constraint(guess: str, alpha: ty.Set[str] = ALPHA) -> Constraint:
    n = len(_to_word(guess))
    position_eliminations = {i: set() for i in range(n)}
    char_counts = defaultdict(int)

    def eliminate(c, from_=set(range(n))):
        for i in from_:
            # never eliminate the last character for a position
            if len(position_eliminations[i]) < len(alpha) - 1:
                position_eliminations[i].add(c)

    def require(rc, i):
        position_eliminations[i] = alpha - {rc}

    already_yellow = set()
    for i, (color, c) in enumerate(parse(guess)):
        if color == 'yellow':
            eliminate(c, {i})
            char_counts[c] += 1
            already_yellow.add(c)
        elif color == 'green':
            require(c, i)
            char_counts[c] += 1
        else:
            # grays are complex.
            # They mean "there are no more of this character in the word".
            # In the absence of other information about the character,
            # this means the character cannot appear anywhere in the word, i.e. the count is zero.
            # However, if the character has already appeared in the word, this
            # only means that the character must not appear more times.
            # If any of the previous occurrence(s) were yellow,
            # then we can only eliminate this specific position.
            # If all other occurrences are green, then we can eliminate
            # the character from consideration from all locations except where it is required.
            assert color == 'gray', (guess, i, c, color)
            if c in already_yellow:
                eliminate(c, {i})
            else:
                eliminate(c)
    return position_eliminations, dict(char_counts)


def _merge_constraints(ca: Constraint, cb: Constraint) -> Constraint:
    """Constraints must be for strings of equal length"""
    elims_a, cc_a = ca
    elims_b, cc_b = cb
    return {
        i: elims_a[i] | elims_b[i]
        for i in range(len(elims_a))
    }, {
        c: max(cc_a.get(c, 0), cc_b.get(c, 0)) for c in list((*cc_a.keys(), *cc_b.keys()))
    }


def merge_constraints(*constraints: Constraint) -> Constraint:
    merged = None
    for constraint in constraints:
        merged = constraint if merged is None else _merge_constraints(merged, constraint)
    assert merged, "Cannot merge zero constraints"
    return merged


def matrix_eliminate(alpha: ty.Set[str], constraint: Constraint) -> Constraint:
    # at this point, it's possible to use position-by-position process
    # of elimination.  in other words, if a character is known to be
    # required N times but is eliminated in all but N locations, then
    # all other characters are eliminated from those N locations.
    #
    # Not only must this be run for every character, it must also
    # be re-run with all non-finalized characters every time it results in a change.
    def run(constraint: Constraint) -> Constraint:
        pos_elims, char_counts = constraint
        for char, count in char_counts.items():
            remaining_positions_allowed = set(pos_elims)
            for pos, eliminations in pos_elims.items():
                if char in eliminations:
                    remaining_positions_allowed -= {pos}
            if len(remaining_positions_allowed) == count:
                pos_elims = deepcopy(pos_elims)
                for pos in remaining_positions_allowed:
                    pos_elims[pos] = alpha - {char}
                return pos_elims, char_counts
        return pos_elims, char_counts
    while True:
        new_constraint = run(constraint)
        if new_constraint == constraint:
            return constraint
        constraint = new_constraint


def given2(*guesses, alpha: ty.Set[str] = ALPHA):
    """Format:

    lowercase letters for incorrect guesses.

    uppercase letters for correct (green) guesses.

    yellow (letter is present, but not the correct position) guesses
    are letters encased in parentheses. Capitalization is ignored.

    Example:

    If the correct answer is BROWN, B(OR)oN would be the guess representation for 'boron'.
    """
    elims, char_counts = merge_constraints(*[constraint(guess) for guess in guesses])
    ## total known characters    == number of characters per string
    if sum(char_counts.values()) == len(elims):
        # then any char not appearing in char_counts must also be eliminated
        for eliminated in elims.values():
            eliminated |= (alpha - set(char_counts))
    elims, char_counts = matrix_eliminate(alpha, (elims, char_counts))
    return {i: ALPHA - e for i, e in elims.items()}, char_counts


def options(regex_strs: Sequence[str], wl: list = five_letter_word_list) -> list:
    def find_with_regexes(regexes: tuple):
        for w in wl:
            if all(regex.search(w) for regex in regexes):
                yield w

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
            # correct! (green)
            assert char_counts[guess_c] > 0
            end_yellow()
            results.append(c.upper())
            char_counts[guess_c] -= 1
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
    CGREEN  = '\33[32m'
    CYELLOW = '\33[33m'
    CRED    = '\33[31m'
    CEND    = '\33[0m'
    colorized = list()
    def colorize_g(guess: str) -> str:
        color_guess = ''
        for color, c in parse(guess):
            if color == 'green':
                color_guess += CGREEN
                color_guess += c.upper()
                color_guess += CEND
            elif color == 'yellow':
                color_guess += CYELLOW
                color_guess += c
                color_guess += CEND
            elif color == 'gray':
                color_guess += CRED
                color_guess += c.lower()
                color_guess += CEND
            else:
                assert False, (guess, c, color)
        return color_guess
    return [colorize_g(guess) for guess in guesses]


from IPython.core.magic import Magics, magics_class, line_magic


@magics_class
class IpythonSolver(Magics):
    def __init__(self, shell, guesses: List[str] = list()):
        # You must call the parent constructor
        super(IpythonSolver, self).__init__(shell)
        self.limit = 30
        self.reset(None)
        self.wl = five_letter_word_list

    @line_magic
    def word_list(self, _):
        if self.wl is five_letter_word_list:
            self.wl = sols
            print('Switched to solutions - cheater...')
        else:
            self.wl = five_letter_word_list
            print('Switched to full word list')
        return self.guesses(_)

    @line_magic
    def wl(self, _):
        self.word_list(_)

    @line_magic
    def possibilities(self, _):
        return given2(*self._guesses)

    def _cur_options(self) -> List[str]:
        return [w for w in options(regexes2(*given2(*self._guesses)), wl=self.wl) if w not in self._ignored]

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
    def play(self, _):
        self.solution(random.choice(sols))

    @line_magic
    def solution(self, line):
        """For testing purposes. If you know the answer and want to manually
        try to 'discover' it using various tools, you can put the
        solution in, and that will make typing easier.
        """
        if line:
            self.reset(None)
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
    def guesses(self, _):
        print(f'# options: {len(self._cur_options())}, input options: {len(self.input_options())}')
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
    def letters(self, _):
        pos_allowed, _ = given2(*self._guesses)
        return ''.join(sorted({c.upper() for allowed in pos_allowed.values() for c in allowed}))

    @line_magic
    def g(self, line):
        return self.guess(line)

    def input_options(self):
        opts = set(self._cur_options())
        return sorted([k for k in self._input_options if k in opts])

    @line_magic
    def o(self, line):
        """Input an option that you have considered."""
        for word in line.split():
            if line not in self._cur_options():
                print(f'{line} not an option')
            self._input_options.add(line)
        self.guesses(None)
        return self.input_options()

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
        self._input_options = set()
        self._ignored = set()


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
