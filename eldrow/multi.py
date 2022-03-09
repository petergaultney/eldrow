import typing as ty
from collections import defaultdict

from .elimination import elimination_scorer, make_options
from .game import Game, get_options, novel_or_option, novelty


class CrossElim(ty.NamedTuple):
    elim_ratio: float
    option_count: int
    solve_count: int


def elim_across_games(games: ty.Collection[Game], limit: int) -> ty.List[ty.Tuple[str, CrossElim]]:
    wordlist = set()
    game_options = dict()
    for game in games:
        game_options[id(game)] = set(get_options(game))
        wordlist |= novel_or_option(game, game_options[id(game)], limit)
    cross_game_novelty_scores: ty.Dict[str, float] = defaultdict(float)
    for game in games:
        w_n = novelty(game, *wordlist)
        for word, n in w_n:
            cross_game_novelty_scores[word] += n

    best_novelty_words = [
        w for w, s in sorted(cross_game_novelty_scores.items(), key=lambda t: t[1], reverse=True)
    ][:limit]

    cross_game_elimination_multipliers: ty.Dict[str, CrossElim] = defaultdict(
        lambda: CrossElim(1.0, 0, 0)
    )

    for game in games:
        print(game.guesses)
        opts = game_options[id(game)]
        elim_scorer = elimination_scorer(opts, make_options(game.alpha, opts, game.guesses))
        for word in best_novelty_words:
            opt_inc = 1 if word in opts else 0
            elim_count = elim_scorer(word)
            game_elim_ratio = elim_count / len(opts)
            solve_inc = 1 if elim_count == len(opts) - 1 else 0
            cross_elim = cross_game_elimination_multipliers[word]
            cross_game_elimination_multipliers[word] = CrossElim(
                cross_elim.elim_ratio * game_elim_ratio if not len(opts) == 1 else 1.0,
                cross_elim.option_count + opt_inc,
                cross_elim.solve_count + solve_inc,
            )

    return sorted(cross_game_elimination_multipliers.items(), key=lambda kv: kv[1][0])
