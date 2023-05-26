import re
import typing as ty
from collections import defaultdict
from functools import cache
from typing import List

from .constrain import given2, regexes2
from .dbm_cache import elim_cache
from .parse import guess_to_word
from .scoring import Scorer
from .words import five_letter_word_list


@cache
def compile(regex_str: str):
    return re.compile(regex_str)


@cache
def options(regex_strs: ty.Tuple[str, ...], wl: ty.Tuple[str, ...] = five_letter_word_list) -> List[str]:
    opts = list()
    regexes = tuple(compile(regex_str) for regex_str in regex_strs)
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
    char_counts: dict[str, int] = defaultdict(int)
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


def options_after_guess(
    alpha: frozenset[str],
    word_list: ty.Tuple[str, ...],
    guesses: ty.Sequence[str],
) -> ty.Callable[[str, str], ty.List[str]]:
    def options_after_guess_(solution: str, guess: str) -> List[str]:
        constraint = given2(*(*guesses, answer(solution, guess)), alpha=alpha, empty_n=len(guess))
        return options(regexes2(constraint), wl=word_list)

    return options_after_guess_


class DataForOptionsAfterGuess(ty.NamedTuple):
    alpha: frozenset[str]
    word_list: ty.Tuple[str, ...]
    guesses: ty.Sequence[str]


def elimination_scorer(
    remaining_possibilities: ty.Collection[str],
    data_for_options_after_guess: DataForOptionsAfterGuess,
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
    dfo = (
        data_for_options_after_guess.alpha,
        data_for_options_after_guess.word_list,
        tuple(sorted(data_for_options_after_guess.guesses)),
        # the constraints on your word are not affected by the order of guesses,
        # so we can sort them to make the cache key slightly more consistent
    )
    the_options_would_be = options_after_guess(*data_for_options_after_guess)

    if len(remaining_possibilities) > 15:
        deco = elim_cache(tuple(remaining_possibilities), dfo)
    else:
        deco = lambda f: f  # noqa

    @deco
    def scorer(*words: str) -> float:
        new_word_to_score = words[-1]
        total_eliminated = 0
        for assumed_solution in remaining_possibilities:
            if assumed_solution == new_word_to_score:
                num_left = 0
            else:
                num_left = len(the_options_would_be(assumed_solution, new_word_to_score))
            total_eliminated += len(remaining_possibilities) - num_left
        return round(total_eliminated / len(remaining_possibilities), 3)

    return scorer
