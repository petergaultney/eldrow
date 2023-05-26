import string
import typing as ty

POS_TYPE = ty.Literal[
    "green",
    "yellow",
    "gray",
]


Pos = ty.Tuple[POS_TYPE, str]
ParsedGuess = ty.Sequence[Pos]


Parser = ty.Callable[[str], ty.Tuple[Pos, ...]]


def _paren_yellow_parse(guess: str) -> ty.Iterator[Pos]:
    """Standard parser - uses parens to indicate yellow, and caps to indicate green"""
    yellow_count = 0
    for c in guess:
        if c == ".":
            yellow_count += 1
        elif c == "(":
            yellow_count = 100
        elif c == ")":
            yellow_count = 0
        else:
            if yellow_count:
                yellow_count -= 1
                yield "yellow", c.lower()
            elif c in string.ascii_uppercase:
                yield "green", c.lower()
            else:
                yield "gray", c
    assert yellow_count == 0, guess


def paren_yellow_parse(guess: str) -> ty.Tuple[Pos, ...]:
    return tuple(_paren_yellow_parse(guess))


def guess_to_word(guess: str) -> str:
    return guess.replace("(", "").replace(")", "").replace(".", "").lower()
