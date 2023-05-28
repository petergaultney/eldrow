#!/usr/bin/env python
import typing as ty
from itertools import product

from eldrow.colors import CGREEN, CORANGE, CRED, CYELLOW, c
from eldrow.constrain import ALPHA
from eldrow.formatting import _format_welim
from eldrow.game import HashableGame, best_elim, get_options
from eldrow.multi import _best_novelty_words_across_games
from eldrow.words import five_letter_word_list, sols


def yield_guesses(word: str) -> ty.Iterator[tuple[str, ...]]:
    for markers in product("_yg", repeat=len(word)):
        w = ""
        for marker, letter in zip(markers, word):
            if marker == "_":
                w += letter.lower()
            elif marker == "y":
                w += "." + letter.lower()
            else:
                w += letter.upper()
        yield (w,)


def foo(guesses_iter: ty.Iterable[tuple[str, ...]]):
    def mk_game(*guesses: str) -> HashableGame:
        return HashableGame(5, sols, ALPHA, guesses, tuple())

    for guesses in guesses_iter:
        print(guesses)
        game = mk_game(*guesses)
        opts = get_options(game)
        if len(opts) < 3:
            # nothing to be found
            continue

        true_best = None
        for n in (16000, 8000, 6000, 4000, 2000, 1000, 500, 250, 125):
            candidates = _best_novelty_words_across_games([game], n, five_letter_word_list)

            best = list(reversed(best_elim(game, candidates)))

            COMP = 10
            if not true_best:
                true_best = best
                continue
            for i in range(1, COMP):
                if best[:i] != true_best[:i]:
                    diff = best[i]
                    tot_diff = true_best[0].elim_score - diff.elim_score
                    pct_diff = (tot_diff / true_best[0].elim_score) * 100
                    ps = f"difference of {tot_diff:.2f} or {pct_diff:.1f}%."
                    pstr = c(CGREEN, ps)
                    if pct_diff > 2:
                        pstr = c(CYELLOW, ps)
                    if pct_diff > 4:
                        pstr = c(CORANGE, ps)
                    if pct_diff > 8:
                        pstr = c(CRED, ps)
                    if pct_diff > 1:
                        print(
                            f"with {guesses} and {len(opts)}, using {n} words, took until top {i}"
                            f" to find a {pstr}"
                        )
                        print(" ".join(_format_welim(true_best[i])))
                    break
            if best[0] != true_best[0]:
                print(c(CRED, f"Best option different at {n}, {pstr}, n opts: {len(opts)}"))
                break


if __name__ == "__main__":
    foo(yield_guesses("crate"))
