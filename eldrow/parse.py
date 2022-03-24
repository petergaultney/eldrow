import typing as ty
import string


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
    is_yellow = False
    for c in guess:
        if c == "(":
            assert not is_yellow, guess
            is_yellow = True
        elif c == ")":
            assert is_yellow, guess
            is_yellow = False
        else:
            if is_yellow:
                yield "yellow", c.lower()
            elif c in string.ascii_uppercase:
                yield "green", c.lower()
            else:
                yield "gray", c


def paren_yellow_parse(guess: str) -> ty.Tuple[Pos, ...]:
    return tuple(_paren_yellow_parse(guess))
