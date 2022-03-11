import typing as ty
from collections import defaultdict

from .elimination import elimination_scorer, make_options
from .game import Game, get_options, novel_or_option, novelty
from .colors import colorize


class CrossElim(ty.NamedTuple):
    elim_ratio: float
    solved: set
    option: set


def elim_across_games(
    games: ty.Dict[ty.Any, Game], limit: int, add_to_wordlist: ty.Collection[str] = tuple()
) -> ty.List[ty.Tuple[str, CrossElim]]:
    wordlist = set()
    game_options = dict()
    for key, game in games.items():
        game_options[key] = set(get_options(game))
        wordlist |= novel_or_option(game, game_options[key], limit)
    wordlist |= set(add_to_wordlist)
    cross_game_novelty_scores: ty.Dict[str, float] = defaultdict(float)
    for game in games.values():
        w_n = novelty(game, *wordlist)
        for word, n in w_n:
            cross_game_novelty_scores[word] += n

    best_novelty_words = [
        w for w, s in sorted(cross_game_novelty_scores.items(), key=lambda t: t[1], reverse=True)
    ][:limit]

    cross_game_elimination_multipliers: ty.Dict[str, CrossElim] = defaultdict(
        lambda: CrossElim(1.0, set(), set())
    )

    for key, game in games.items():
        print(key, " ".join(colorize(*game.guesses)))
        opts = game_options[key]
        elim_scorer = elimination_scorer(opts, make_options(game.alpha, opts, game.guesses))
        for word in best_novelty_words:
            opt_inc = {key} if word in opts else set()
            elim_count = elim_scorer(word)
            game_elim_ratio = elim_count / len(opts)
            solved = {key} if elim_count == len(opts) - 1 else set()
            cross_elim = cross_game_elimination_multipliers[word]
            cross_game_elimination_multipliers[word] = CrossElim(
                cross_elim.elim_ratio * (game_elim_ratio if not len(opts) == 1 else 1.0),
                cross_elim.solved | solved,
                cross_elim.option | opt_inc,
            )

    sorted_by_options = sorted(
        cross_game_elimination_multipliers.items(), key=lambda kv: len(kv[1].option)
    )
    sorted_by_solving = sorted(sorted_by_options, key=lambda kv: len(kv[1].solved))
    return sorted(sorted_by_solving, key=lambda kv: kv[1].elim_ratio)
