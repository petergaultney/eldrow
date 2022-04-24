import typing as ty
from typing import Sequence, Collection, List, Callable
from collections import defaultdict
import re

from .words import five_letter_word_list
from .scoring import Scorer
from .constrain import guess_to_word, given2, regexes2


def options(regex_strs: Sequence[str], wl: Collection[str] = five_letter_word_list) -> List[str]:
    opts = list()
    regexes = tuple(re.compile(regex_str) for regex_str in regex_strs)
    for w in wl:
        allowed = True
        for regex in regexes:
            if not regex.search(w):
                allowed = False
                break
        if allowed:
            opts.append(w)
    return opts


def answer(solution: str, guess: str) -> str:
    if len(solution) != len(guess):
        return guess
    guess = guess_to_word(guess)
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
            results.append(")")
            is_yellow = False

    def start_yellow():
        nonlocal is_yellow
        if not is_yellow:
            results.append("(")
            is_yellow = True

    for guess_c, c in zip(guess, solution):
        if guess_c == c:
            # correct! (green)
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
    return "".join(results)


# bug with following inputs:
# cr(a)te cAr(a)t
# best_elim 1 1200


def elimination_scorer(
    remaining_words: ty.Collection[str],
    options_after_guess: Callable[[str, str], ty.List[str]],
) -> Scorer:
    """The idea is to optimize discovering information _about_ the word
    rather than solving for the word itself. Therefore, knowledge of
    whether a character is present (yellow) is valuable in a way that
    it is not in a pure per-word scorer.

    At the same time, guessing a character that is already known in
    its same location is actively wasteful - you will eliminate no
    words by guessing that.

    Maybe this should be called the elimination scorer, and it should
    focus on picking letters that will reduce the total score in the
    position_scores dict.
    """

    def scorer(*words: str) -> float:
        word = words[-1]
        total_eliminated = 0
        for pretend_solution in remaining_words:
            num_left = len(options_after_guess(pretend_solution, word))
            total_eliminated += len(remaining_words) - num_left
        return round(total_eliminated / len(remaining_words), 3)

    return scorer


def make_options(
    alpha: ty.Set[str],
    word_list: ty.Collection[str],
    guesses: ty.Sequence[str],
):
    def options_after_guess(solution: str, guess: str) -> List[str]:
        constraint = given2(*(*guesses, answer(solution, guess)), alpha=alpha, empty_n=len(guess))
        return options(regexes2(constraint), wl=word_list)

    return options_after_guess
