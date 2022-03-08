#!/usr/bin/env python
import string
import typing as ty
from collections import defaultdict
from copy import deepcopy


ALPHA = set(string.ascii_lowercase)


__very_unusual_letters = "vzjxq"


PositionEliminations = ty.Dict[int, ty.Set[str]]
CharacterCount = ty.Dict[str, int]
Constraint = ty.Tuple[PositionEliminations, CharacterCount]


def regexes2(constraint: Constraint) -> ty.Tuple[str, ...]:
    positions, counts = constraint

    def pos(i: int) -> str:
        chars = positions[i]
        if not chars:
            raise ValueError(f"No characters are left for position {i} with constraint {constraint}")
        return "[" + "".join(chars) + "]"

    return ("".join((pos(i) for i in positions)), *tuple(counts))


def parse(guess: str) -> ty.Iterator[ty.Tuple[str, str]]:
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


def constraint(guess: str, alpha: ty.Set[str] = ALPHA) -> Constraint:
    n = len(guess_to_word(guess))
    position_eliminations = {i: set() for i in range(n)}
    char_counts = defaultdict(int)

    def eliminate(c, from_=set(range(n))):
        for i in from_:
            # never eliminate the last character for a position
            if len(position_eliminations[i]) < len(alpha) - 1:
                position_eliminations[i].add(c)

    def require(rc, i):
        position_eliminations[i] = alpha - {rc}

    already_yellow = set()
    for i, (color, c) in enumerate(parse(guess)):
        if color == "yellow":
            eliminate(c, {i})
            char_counts[c] += 1
            already_yellow.add(c)
        elif color == "green":
            require(c, i)
            char_counts[c] += 1
        else:
            # grays are complex.
            # They mean "there are no more of this character in the word".
            # In the absence of other information about the character,
            # this means the character cannot appear anywhere in the word, i.e. the count is zero.
            # However, if the character has already appeared in the word, this
            # only means that the character must not appear more times.
            # If any of the previous occurrence(s) were yellow,
            # then we can only eliminate this specific position.
            # If all other occurrences are green, then we can eliminate
            # the character from consideration from all locations except where it is required.
            assert color == "gray", (guess, i, c, color)
            if c in already_yellow:
                eliminate(c, {i})
            else:
                eliminate(c)
    return position_eliminations, dict(char_counts)


def _merge_constraints(ca: Constraint, cb: Constraint) -> Constraint:
    """Constraints must be for strings of equal length"""
    elims_a, cc_a = ca
    elims_b, cc_b = cb
    return {i: elims_a[i] | elims_b[i] for i in range(len(elims_a))}, {
        c: max(cc_a.get(c, 0), cc_b.get(c, 0)) for c in list((*cc_a.keys(), *cc_b.keys()))
    }


def merge_constraints(*constraints: Constraint) -> Constraint:
    merged = None
    for constraint in constraints:
        merged = constraint if merged is None else _merge_constraints(merged, constraint)
    assert merged, "Cannot merge zero constraints"
    return merged


def matrix_eliminate(alpha: ty.Set[str], constraint: Constraint) -> Constraint:
    # at this point, it's possible to use position-by-position process
    # of elimination.  in other words, if a character is known to be
    # required N times but is eliminated in all but N locations, then
    # all other characters are eliminated from those N locations.
    #
    # Not only must this be run for every character, it must also
    # be re-run with all non-finalized characters every time it results in a change.
    def run(constraint: Constraint) -> Constraint:
        pos_elims, char_counts = constraint
        for char, count in char_counts.items():
            remaining_positions_allowed = set(pos_elims)
            for pos, eliminations in pos_elims.items():
                if char in eliminations:
                    remaining_positions_allowed -= {pos}
            if len(remaining_positions_allowed) == count:
                pos_elims = deepcopy(pos_elims)
                for pos in remaining_positions_allowed:
                    pos_elims[pos] = alpha - {char}
                return pos_elims, char_counts
        return pos_elims, char_counts

    while True:
        new_constraint = run(constraint)
        if new_constraint == constraint:
            return constraint
        constraint = new_constraint


def given2(*guesses, alpha: ty.Set[str] = ALPHA, empty_n: int = 5) -> Constraint:
    """Format:

    lowercase letters for incorrect guesses.

    uppercase letters for correct (green) guesses.

    yellow (letter is present, but not the correct position) guesses
    are letters encased in parentheses. Capitalization is ignored.

    Example:

    If the correct answer is BROWN, B(OR)oN would be the guess representation for 'boron'.
    """
    if not guesses:
        return {i: alpha - set() for i in range(empty_n)}, dict()
    elims, char_counts = merge_constraints(*[constraint(guess) for guess in guesses])
    #  total known characters    == number of characters per string
    if sum(char_counts.values()) == len(elims):
        # then any char not appearing in char_counts must also be eliminated
        for eliminated in elims.values():
            eliminated |= alpha - set(char_counts)
    elims, char_counts = matrix_eliminate(alpha, (elims, char_counts))
    return {i: alpha - e for i, e in elims.items()}, char_counts


def guess_to_word(guess: str) -> str:
    return guess.replace("(", "").replace(")", "").lower()