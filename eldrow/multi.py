import typing as ty
from dataclasses import dataclass

from .constrain import given2, regexes2, guess_to_word
from .elimination import answer, options, elimination_scorer, make_options


@dataclass
class Game:
    n: int
    wl: ty.List[str]
    alpha: ty.Set[str]
    solution: str
    guesses: ty.List[str]
    possibilities: ty.List[str]
    ignored: ty.Set[str]


def _given(game: Game):
    return given2(*game.guesses, alpha=game.alpha, empty_n=game.n)


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
