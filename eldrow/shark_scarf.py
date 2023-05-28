import typing as ty
from collections import defaultdict
from itertools import combinations

from .constrain import ALPHA
from .game import WordElim, best_elim, hashable, new_game
from .words import sols

_COMBS = dict()


def _yield_threes(word: str, base: str = "_") -> ty.Iterator[str]:
    if len(word) not in _COMBS:
        _COMBS[len(word)] = list(combinations(list(range(len(word))), 3))

    for comb in _COMBS[len(word)]:
        three_comb = ""
        for i in range(len(word)):
            if i in comb:
                three_comb += word[i]
            else:
                three_comb += base
        yield three_comb


def lines(*fs):
    for f in fs:
        with open(f) as fp:
            for l in fp.read().splitlines():
                yield l


def find_threes(*words, min_length: int = 10):
    d = defaultdict(set)
    for word in words:
        for three_comb in _yield_threes(word):
            d[three_comb].add(word)

    skip_keys = set()
    for key, val in d.items():
        if len(val) < min_length:
            skip_keys.add(key)

    return {k: v for k, v in d.items() if k not in skip_keys}


def counted(threes):
    by_count: dict[int, dict] = defaultdict(dict)
    for k, v in threes.items():
        by_count[len(v)][k] = v
    return {k: by_count[k] for k in sorted(by_count.keys())}


class Path(ty.NamedTuple):
    word: str
    guess: str
    best_word_elim: WordElim


def shark_scarf_paths(pattern: str, shark_scarf: ty.Collection[str]) -> ty.Iterator[Path]:
    """Show the best next option available given that your first guess
    is a word within the shark scarf but the other two letters are
    incorrect.
    """

    def w_to_g(w):
        g = ""
        for i in range(len(w)):
            if pattern[i] == "_":
                g += w[i]
            else:
                g += w[i].upper()
        assert len(g) == len(w)
        return g

    for w in shark_scarf:
        game = new_game(ALPHA, sols)
        g = w_to_g(w)
        game.guesses.append(g)
        yield Path(w, g, best_elim(hashable(game), game.wl)[-1])


class PathStats(ty.NamedTuple):
    avg: float
    median: float
    best: ty.Tuple[float, ty.Tuple[str, ...]]
    worst: ty.Tuple[float, ty.Tuple[str, ...]]


def best_worst_avg(paths: ty.Sequence[Path]) -> PathStats:
    avg = round(sum([p.best_word_elim.elim_score for p in paths]) / len(paths), 2)
    worst = 0.0
    worst_l = list()
    best = 100000.0
    best_l = list()
    all_scores: ty.List[float] = list()

    for p in paths:
        all_scores.append(p.best_word_elim.elim_score)
        if p.best_word_elim.elim_score > worst:
            worst_l = [p.guess]
            worst = p.best_word_elim.elim_score
        elif p.best_word_elim.elim_score == worst:
            worst_l.append(p.guess)

        if p.best_word_elim.elim_score < best:
            best_l = [p.guess]
            best = p.best_word_elim.elim_score
        elif p.best_word_elim.elim_score == best:
            best_l.append(p.guess)

    all_scores = sorted(all_scores)

    def median() -> float:
        midpoint = len(all_scores) // 2
        if len(all_scores) % 2 == 1:
            return all_scores[midpoint]
        return (all_scores[midpoint] + all_scores[midpoint - 1]) / 2

    return PathStats(
        avg,
        round(median(), 2),
        (best, tuple(best_l)),
        (worst, tuple(worst_l)),
    )


def do_it():
    import traceback

    for size, threes in reversed(counted(find_threes(*sols)).items()):
        for pat, words in threes.items():
            try:
                res = best_worst_avg(list(shark_scarf_paths(pat, words)))
                print(pat, size, res)
                yield pat, res
            except Exception:
                traceback.print_exc()
                print("the broken one is ", pat, size)
