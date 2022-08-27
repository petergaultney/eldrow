import typing as ty

from .game import Game, get_options, _given


def explore(options: ty.Sequence[str], idea: str, already_explored: ty.Collection[str] = tuple()) -> ty.List[str]:
    if not idea:
        idea = '.' * len(options[0])

    def _():
        for w in options:
            matches = ""
            for i, c in enumerate(w):
                if idea[i] != "." and idea[i] != c:
                    matches = ""
                    break
                matches += idea[i]
            if matches:
                if w in already_explored:
                    yield w
                else:
                    yield matches

    return list(_())


def pass_complete_idea(game: Game, idea: str) -> str:
    _elims, counts = _given(game)
    for c, count in counts.items():
        if count > 0 and c not in idea:
            return ""
    return idea
