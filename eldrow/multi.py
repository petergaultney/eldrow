import os
import typing as ty
from collections import defaultdict
from functools import partial, reduce
from multiprocessing import Pool

from .elimination import DataForOptionsAfterGuess, elimination_scorer
from .game import Game, HashableGame, get_options, hashable, novel_or_option, novelty
from .words import five_letter_word_list

_DEFAULT_WORDLIST_LIMIT = int(os.getenv("ELDROW_WORDLIST_LIMIT", 12973))


class CrossElim(ty.NamedTuple):
    elim_ratio: float
    solved: bool
    option: bool


def elim_game(candidates: tuple[str, ...], game: HashableGame) -> ty.Dict[str, CrossElim]:
    opts_tuple = get_options(game)
    nc = len(candidates)
    elim_scorer = elimination_scorer(
        opts_tuple, DataForOptionsAfterGuess(game.alpha, opts_tuple, game.guesses)
    )
    cross_game_elimination_multipliers = dict()
    options_set = set(opts_tuple)
    for i, word in enumerate(candidates):
        elim_count = elim_scorer(word)
        game_elim_ratio = (elim_count + 1) / len(opts_tuple)
        cross_game_elimination_multipliers[word] = CrossElim(
            (game_elim_ratio if len(opts_tuple) != 1 else 1.0),
            elim_count >= len(opts_tuple) - 1,
            word in options_set,
        )
        left = nc - i
        if left % 1000 == 0:
            print(f"{left} words left against {len(opts_tuple)} options")
    print(f"finished with {len(opts_tuple)} options")
    return cross_game_elimination_multipliers


class GameCrossElim(ty.NamedTuple):
    elim_ratio: float
    solved: set[str]
    option: set[str]


def _p_elim_game(
    candidates: tuple[str, ...], key_game: ty.Tuple[str, Game]
) -> ty.Dict[str, GameCrossElim]:
    key, game = key_game
    return {
        word: GameCrossElim(
            ce.elim_ratio,
            {key} if ce.solved else set(),
            {key} if ce.option else set(),
        )
        for word, ce in elim_game(candidates, hashable(game)).items()
    }


def _all_options(*games: Game) -> ty.Set[str]:
    wordlist = set()
    for game in games:
        wordlist |= set(get_options(game))
    return wordlist


def _all_novel(limit: int, *games: Game) -> ty.Set[str]:
    wordlist = set()
    for game in games:
        game_options = set(get_options(game))
        wordlist |= novel_or_option(game, game_options, limit)
    return wordlist


def _best_novelty_words_across_games(
    games: ty.Collection[Game | HashableGame],
    limit: int,
    wordlist: ty.Collection[str],
) -> ty.List[str]:
    cross_game_novelty_scores: ty.Dict[str, float] = defaultdict(float)
    for game in games:
        w_n = novelty(game, *wordlist)
        for word, n in w_n:
            cross_game_novelty_scores[word] += n

    return [w for w, s in sorted(cross_game_novelty_scores.items(), key=lambda t: t[1], reverse=True)][
        :limit
    ]


def all_or_opts_wordlist_creators(games: ty.Collection[Game]) -> dict[str, ty.Callable[..., list[str]]]:
    def best_sols(limit: int = _DEFAULT_WORDLIST_LIMIT):
        return _best_novelty_words_across_games(games, limit, _all_novel(limit, *games))

    def best_opts(limit: int = _DEFAULT_WORDLIST_LIMIT):
        return _best_novelty_words_across_games(games, limit, _all_options(*games))

    def best_all(limit: int = 0):
        if not limit:
            return five_letter_word_list
        return _best_novelty_words_across_games(games, limit, five_letter_word_list)

    return dict(default=best_all, sols=best_sols, opts=best_opts)


def _merge_game_cross_elims(
    a: ty.Dict[str, GameCrossElim], b: ty.Dict[str, GameCrossElim]
) -> ty.Dict[str, GameCrossElim]:
    assert set(a) == set(b)

    def merge(ac: GameCrossElim, bc: GameCrossElim) -> GameCrossElim:
        return GameCrossElim(ac.elim_ratio * bc.elim_ratio, ac.solved | bc.solved, ac.option | bc.option)

    return {word: merge(a[word], b[word]) for word in a}


def elim_across_games(
    games: ty.Dict[ty.Any, Game], wordlist: ty.Collection[str]
) -> ty.List[ty.Tuple[str, GameCrossElim]]:
    wordlist_t = tuple(wordlist)
    with Pool(len(games)) as pool:
        cross_game_elimination_multipliers = reduce(
            _merge_game_cross_elims, pool.map(partial(_p_elim_game, wordlist_t), games.items())
        )

    game_wordlist = set(list(games.values())[0].wl)
    words_onto_cross_elims = cross_game_elimination_multipliers.items()
    sorted_by_in_wl = sorted(
        words_onto_cross_elims, key=lambda w_ce: 1 if w_ce[0] in game_wordlist else 0
    )
    sorted_by_options = sorted(sorted_by_in_wl, key=lambda kv: len(kv[1].option))
    sorted_by_solving = sorted(sorted_by_options, key=lambda kv: len(kv[1].solved))
    return sorted(
        sorted_by_solving, key=lambda kv: (len(kv[1].solved), kv[1].elim_ratio, len(kv[1].option))
    )
