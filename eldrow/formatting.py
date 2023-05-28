from . import colors
from .game import Game, WordElim


def _p(game: Game, multiline: bool = False):
    if multiline:
        return "\n        ".join(["", *colors.colorize(*game.guesses)])
    return "  ".join(colors.colorize(*game.guesses))


def _format_welim(welim: WordElim) -> tuple[str, ...]:
    def fmt3(f):
        return f"{f: 3.3f}"

    return (
        fmt3(welim.elim_score),
        fmt3(welim.novelty_score),
        "🟨" if welim.is_possible_solution else "⬛",
        welim.scored_word,
    )
