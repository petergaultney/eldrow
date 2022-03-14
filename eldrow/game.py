import typing as ty
import itertools
from dataclasses import dataclass

from .constrain import given2, regexes2, guess_to_word
from .elimination import answer, options, elimination_scorer, make_options
from .scoring import (
    best_next_score,
    score_words,
    score_for_novelty,
    replace_solved_with_average_totals,
    construct_position_freqs,
)


@dataclass
class Game:
    n: int
    wl: ty.List[str]
    alpha: ty.Set[str]
    solution: str
    guesses: ty.List[str]
    possibilities: ty.List[str]
    ignored: ty.Set[str]


def new_game(alpha, wl) -> Game:
    return Game(len(wl[0]), wl, alpha, "", list(), list(), set())


def _simple_words(*guesses) -> ty.List[str]:
    return [guess_to_word(guess) for guess in guesses]


def _given(game: Game):
    return given2(*game.guesses, alpha=game.alpha, empty_n=game.n)


def letters(game: Game) -> ty.List[str]:
    pos_allowed, _ = _given(game)
    return sorted({c.upper() for allowed in pos_allowed.values() for c in allowed})


def get_options(game: Game) -> ty.List[str]:
    return [w for w in options(regexes2(_given(game)), wl=game.wl) if w not in game.ignored]


def format(game: Game, guess: str) -> str:
    assert game.solution
    return answer(game.solution, guess) or guess


def guess(game: Game, *guesses: str) -> Game:
    for guess in guesses:
        if guess:
            if game.solution:
                guess = format(game, guess)
            if guess_to_word(guess) not in game.wl:
                return game
            if guess not in game.guesses:
                game.guesses.append(guess)
    return game


def best_options(game: Game):
    remaining_words = get_options(game)
    return best_next_score(
        remaining_words,
        *_simple_words(*game.guesses),
        scorer=score_words(construct_position_freqs(remaining_words)),
    )


def _novelty_scorer(game: Game) -> ty.Callable[..., float]:
    return score_for_novelty(
        replace_solved_with_average_totals(construct_position_freqs(get_options(game)))
    )


def novelty(game: Game, *words: str) -> ty.List[ty.Tuple[str, float]]:
    novelty_scorer = _novelty_scorer(game)
    return [(w, novelty_scorer(*_simple_words(*game.guesses), w)) for w in words]


def best_novelty(game: Game, *words: str) -> ty.List[ty.Tuple[float, str]]:
    novelty_scorer = _novelty_scorer(game)
    wordlist = [w for w in (words or game.wl) if w not in game.ignored]
    return [
        (info_score, word)
        for info_score, word in best_next_score(
            wordlist,
            *_simple_words(*game.guesses),
            scorer=novelty_scorer,
        )
    ]


def novel_or_option(game: Game, options: ty.Collection[str], limit: int) -> ty.Set[str]:
    return set([res[1] for res in best_novelty(game)[-limit:]]) | set(itertools.islice(options, limit))


def best_elim(
    game: Game, wordlist: ty.Collection[str] = tuple(), limit: int = 30
) -> ty.List[ty.Tuple[float, float, bool, str]]:
    limit = limit or 30
    opts = get_options(game)
    novelty_scorer = _novelty_scorer(game)
    simple_guesses = _simple_words(*game.guesses)

    by_is_option = lambda x: x[2]
    by_novelty_score = lambda x: x[1]
    by_elim_score = lambda x: x[0]

    def sort_many(sorts, xs):
        for sort in sorts:
            xs = sorted(xs, key=sort)
        return xs

    return sort_many(
        [by_novelty_score, by_is_option, by_elim_score],
        [
            (score, novelty_scorer(*simple_guesses, word), word in opts, word)
            for score, word in best_next_score(
                wordlist or novel_or_option(game, opts, limit),
                *list(map(guess_to_word, game.guesses)),
                scorer=elimination_scorer(
                    opts,
                    make_options(
                        game.alpha,
                        opts,
                        game.guesses,
                    ),
                ),
            )
        ],
    )
