import itertools
import typing as ty
from dataclasses import dataclass

from .constrain import given2, regexes2
from .elimination import DataForOptionsAfterGuess, answer, elimination_scorer, options
from .parse import guess_to_word
from .scoring import (
    best_next_score,
    construct_position_freqs,
    replace_solved_with_average_totals,
    score_for_novelty,
    score_words,
)


@dataclass
class Game:
    n: int
    wl: ty.Tuple[str, ...]
    alpha: frozenset[str]
    solution: str
    guesses: ty.List[str]
    possibilities: ty.List[str]
    ignored: ty.Set[str]


class HashableGame(ty.NamedTuple):
    n: int
    wl: ty.Tuple[str, ...]
    alpha: frozenset[str]
    guesses: ty.Tuple[str, ...]
    ignored: ty.Tuple[str, ...]


def new_game(alpha: ty.Collection[str], wl: ty.Collection[str]) -> Game:
    wl = tuple(wl)
    return Game(len(wl[0]), tuple(wl), frozenset(alpha), "", list(), list(), set())


def hashable(game: Game) -> HashableGame:
    return HashableGame(game.n, game.wl, game.alpha, tuple(game.guesses), tuple(game.ignored))


def _simple_words(*guesses) -> ty.List[str]:
    return [guess_to_word(guess) for guess in guesses]


def _given(game: HashableGame | Game):
    return given2(*game.guesses, alpha=game.alpha, empty_n=game.n)


def letters(game: Game) -> ty.List[str]:
    pos_allowed, _ = _given(game)
    return sorted({c.upper() for allowed in pos_allowed.values() for c in allowed})


def get_options(game: HashableGame | Game) -> tuple[str, ...]:
    return tuple([w for w in options(regexes2(_given(game)), wl=game.wl) if w not in game.ignored])


def unparse(game: Game, guess: str) -> str:
    assert game.solution
    return answer(game.solution, guess) or guess


def best_options(game: Game) -> list[tuple[int, str]]:
    remaining_words = get_options(game)
    return best_next_score(
        remaining_words,
        *_simple_words(*game.guesses),
        scorer=score_words(construct_position_freqs(remaining_words)),
    )


def _novelty_scorer(game: Game | HashableGame) -> ty.Callable[..., float]:
    return score_for_novelty(
        replace_solved_with_average_totals(construct_position_freqs(get_options(game)))
    )


def novelty(game: Game, *words: str) -> list[tuple[str, float]]:
    novelty_scorer = _novelty_scorer(game)
    return [(w, novelty_scorer(*_simple_words(*game.guesses), w)) for w in words]


def best_novelty(game: Game, *words: str) -> list[tuple[float, str]]:
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


class WordElim(ty.NamedTuple):
    elim_score: float
    novelty_score: float
    is_possible_solution: bool
    scored_word: str


# @elim_cache()
def best_elim(game: HashableGame, wordlist: tuple[str, ...]) -> list[WordElim]:
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
            WordElim(score, novelty_scorer(*simple_guesses, word), word in opts, word)
            for score, word in best_next_score(
                wordlist,
                # *list(map(guess_to_word, game.guesses)),
                scorer=elimination_scorer(
                    opts,
                    DataForOptionsAfterGuess(
                        game.alpha,
                        opts,
                        game.guesses,
                    ),
                ),
            )
        ],
    )
