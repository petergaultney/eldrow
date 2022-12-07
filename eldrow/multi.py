import typing as ty
from collections import defaultdict
from functools import reduce, partial
from multiprocessing import Pool

from .elimination import elimination_scorer, make_options
from .game import Game, get_options, novel_or_option, novelty


class CrossElim(ty.NamedTuple):
    elim_ratio: float
    solved: set
    option: set


def _merge_cross_elims(
    a: ty.Dict[str, CrossElim], b: ty.Dict[str, CrossElim]
) -> ty.Dict[str, CrossElim]:
    assert set(a) == set(b)

    def merge(ac: CrossElim, bc: CrossElim) -> CrossElim:
        return CrossElim(ac.elim_ratio * bc.elim_ratio, ac.solved | bc.solved, ac.option | bc.option)

    return {word: merge(a[word], b[word]) for word in a}


def _hash_game(game: Game) -> str:
    return f"{game.n}-{game.alpha}-{len(game.wl)}-{game.guesses}"


def caching_cross_elim_for_guesses_and_word(game: Game) -> CrossElim:
    pass


def elim_game(candidates: ty.Collection[str], key: str, game: Game) -> ty.Dict[str, CrossElim]:
    opts = set(get_options(game))
    elim_scorer = elimination_scorer(opts, make_options(game.alpha, tuple(opts), game.guesses))
    cross_game_elimination_multipliers = dict()
    for word in candidates:
        elim_count = elim_scorer(word)
        game_elim_ratio = (elim_count + 1) / len(opts)
        cross_game_elimination_multipliers[word] = CrossElim(
            (game_elim_ratio if len(opts) != 1 else 1.0),
            {key} if elim_count >= len(opts) - 1 else set(),
            {key} if word in opts else set(),
        )
    return cross_game_elimination_multipliers


def _p_elim_game(
    candidates: ty.Collection[str], key_game: ty.Tuple[str, Game]
) -> ty.Dict[str, CrossElim]:
    return elim_game(candidates, *key_game)

    # import cProfile

    # key, game = key_game
    # res = None

    # def profile():
    #     nonlocal res
    #     res = elim_game(candidates, *key_game)

    # cProfile.runctx("profile()", globals(), locals(), f"prof{key}.prof")
    # return res


def elim_across_games(
    games: ty.Dict[ty.Any, Game],
    limit: int,
    only_options: bool = False,
) -> ty.List[ty.Tuple[str, CrossElim]]:
    wordlist = set()
    for key, game in games.items():
        game_options = set(get_options(game))
        if not only_options:
            wordlist |= novel_or_option(game, game_options, limit)
        else:
            wordlist |= game_options
    cross_game_novelty_scores: ty.Dict[str, float] = defaultdict(float)
    for game in games.values():
        w_n = novelty(game, *wordlist)
        for word, n in w_n:
            cross_game_novelty_scores[word] += n

    best_novelty_words = [
        w for w, s in sorted(cross_game_novelty_scores.items(), key=lambda t: t[1], reverse=True)
    ][:limit]

    with Pool(len(games)) as pool:
        cross_game_elimination_multipliers = reduce(
            _merge_cross_elims, pool.map(partial(_p_elim_game, best_novelty_words), games.items())
        )

    sorted_by_options = sorted(
        cross_game_elimination_multipliers.items(), key=lambda kv: len(kv[1].option)
    )
    sorted_by_solving = sorted(sorted_by_options, key=lambda kv: len(kv[1].solved))
    return sorted(
        sorted_by_solving, key=lambda kv: (len(kv[1].solved), kv[1].elim_ratio, len(kv[1].option))
    )
