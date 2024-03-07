from __future__ import annotations

import getpass
import json
import random
import re
from typing import Callable, List

from IPython.core.magic import Magics, line_magic, magics_class

from . import colors
from .auto_limit import auto_limit
from .constrain import ALPHA, guess_to_word
from .explore import explore
from .formatting import _format_welim, _p
from .game import (
    Game,
    best_elim,
    best_options,
    get_options,
    hashable,
    letters,
    new_game,
    novelty,
    unparse,
)
from .memoize import elim_store
from .multi import all_or_opts_wordlist_creators, elim_across_games
from .scoring import construct_position_freqs, score_words
from .words import five_letter_word_list, sols


def kill_words(*words: str) -> None:
    with open("killed.txt", "a") as f:
        for word in words:
            if word:
                f.write(word + "\n")


def _game_color(opts: int, poss: int) -> str:
    if opts == poss:
        if opts == 1:
            return colors.CBLUE
        return colors.CYELLOW
    if opts == 1:
        return colors.CGREEN
    return colors.CEND


def _instruction_line_to_chosen_wordlist(
    line: str, default: Callable[..., list[str]], **named: Callable[..., list[str]]
) -> list[str]:
    bits = line.split()
    if not bits:
        return default()

    cb = default
    if bits[0] in named:
        cb = named[bits[0].lower()]
        bits.pop(0)

    if not bits:
        return cb()

    def _limit(s: str) -> None | int:
        try:
            return int(s)
        except ValueError:
            return None

    limit = _limit(bits[0])
    if limit:
        print(f"Using limit {limit}")
        return cb(limit)
    return cb()


@magics_class
class IpythonCli(Magics):
    def __init__(self, shell, guesses: list[str] = list()):
        # You must call the parent constructor
        super().__init__(shell)
        self.limit = 15
        self.wl = sols
        self.n = len(self.wl[0])
        self.reset(None)

    def _new_game(self, index: int):
        with open("killed.txt") as f:
            to_ignore = set(f.read().splitlines())
        game = new_game(ALPHA, self.wl)
        game.ignored = to_ignore
        self.games[index] = game
        return game

    def _previous_solutions(self) -> List[str]:
        prev_sols = list()
        with open("played.jsonl") as pj:
            for line in pj.read().splitlines():
                prev_sols.append(json.loads(line)[-1].lower())
        return prev_sols

    def _prs(self, line) -> tuple[Game, str]:
        m = re.match(r"^\s*(\d+)(.*)", line or "")
        if m:
            game_number = int(m.group(1))
            if game_number < 17:
                self.game_key = game_number
                if game_number not in self.games:
                    self._new_game(game_number)  # create new game
                return self.games[game_number], m.group(2).strip()
        return self.games[self.game_key], line.strip()

    @line_magic
    def word_list(self, _):
        """Switch the word lists"""
        if self.wl is sols:
            print("Switched to full word list")
            self.wl = five_letter_word_list
        else:
            print("Switched to likely candidates")
            self.wl = sols
        for game in self.games.values():
            game.wl = self.wl
            self._summarize(game)

    @line_magic
    def wl(self, _):
        self.word_list(_)

    @line_magic
    def ignore(self, words):
        for game in self.games:
            game.ignored |= set(words.split())

    @line_magic
    def limit(self, line):
        if line:
            self.limit = int(line)
        return self.limit

    @line_magic
    def play(self, line):
        self.reset(None)
        num = int(line) if line else 1
        for i in range(1, num + 1):
            self._new_game(i)
            self.games[i].solution = random.choice(sols)
        assert len(self.games) == len(
            {g.solution for g in self.games.values()}
        ), "Try again - we picked the same word multiple times"

    @line_magic
    def record(self, _):
        """Call this after finishing a game."""
        assert len(self.games) == 1, "You probably don't want to record multiple games"
        game = self.games[self.game_key]
        if len(guess_to_word(game.guesses[-1])) == self.n and len(get_options(game)) == 1:
            with open("played.jsonl", "a") as f:
                f.write(json.dumps(game.guesses) + "\n")

    @line_magic
    def solution(self, line):
        """For testing purposes. If you know the answer and want to manually
        try to 'discover' it using various tools, you can put the
        solution in, and that will make typing easier.
        """
        game, line = self._prs(line)
        game.solution = line or getpass.getpass("Solution? ")

    @line_magic
    def score(self, words):
        game, words = self._prs(words)
        return score_words(construct_position_freqs(get_options(game)))(*words.split())

    def input_possibilities(self, game: Game):
        opts = set(get_options(game))
        return sorted([k for k in game.possibilities if k in opts])

    @line_magic
    def letters(self, _):
        game, _ = self._prs(_)
        return " ".join(letters(game))

    def _summarize(self, game, multiline: bool = False):
        for game_number, g in self.games.items():
            if game is g:
                break
        opts = len(get_options(game))
        poss = len(self.input_possibilities(game))
        print(
            colors.c(
                _game_color(opts, poss),
                f"# Game {game_number: 2}, options: {opts: 4}, user-selected: {poss}, guesses: ",
            )
            + _p(game, multiline)
        )
        return game.guesses

    def _guess(self, game, line):
        for guess in line.split(" "):
            if guess:
                if game.solution:
                    guess = unparse(game, guess)
                guess_word = guess_to_word(guess)
                if guess_word not in five_letter_word_list:
                    return None
                if guess not in game.guesses:
                    game.guesses.append(guess)
                if len(guess) == self.n and guess.upper() == guess:
                    if guess_word not in game.possibilities:
                        game.possibilities.append(guess_word)
                    print("\nSUCCESS!! Don't forget to %record this result!\n")
        return self._summarize(game)

    @line_magic
    def guess(self, line: str):
        self._guess(*self._prs(line))

    @line_magic
    def n(self, line):
        game, line = self._prs(line)
        game.guesses = list()
        self._guess(game, line)

    def _x(self, idea_line, reveal: bool = False):
        game, ideas_s = self._prs(idea_line)
        ideas = ideas_s.strip().split()
        ideas = ideas or [""]
        options = set(get_options(game))
        successes = list()
        exps = list()
        for idea in ideas:
            exploration = explore(list(options), idea, game.possibilities, reveal=reveal)
            exps.append(exploration)
            if (
                len(exploration) == 1
                and exploration[0] in options
                and exploration[0] not in game.possibilities
            ):
                game.possibilities.append(exploration[0])
                successes.append(exploration[0])

        if successes:
            self._summarize(game)
        return exps[0] if len(exps) == 1 else exps

    @line_magic
    def x(self, idea_line):
        """Explore."""
        return self._x(idea_line)

    @line_magic
    def z(self, idea_line):
        return self._x(idea_line, reveal=True)

    @line_magic
    def o(self, line):
        """Input an option that you have considered."""
        game, line = self._prs(line)

        options = set(get_options(game))
        for word in line.split():
            if word not in options:
                print(f"{word} not an option")
            elif word not in game.possibilities:
                game.possibilities.append(word)
        self._summarize(game)
        return [w for w in game.possibilities if w in options]

    @line_magic
    def g(self, idx):
        game, _ = self._prs(idx)
        self._summarize(game, multiline=True)

    @line_magic
    def kill(self, words):
        self.ignore(words)
        kill_words(*words.split())

    @line_magic
    def options(self, _):
        game, _ = self._prs(_)
        opts = get_options(game)
        return opts, len(opts)

    @line_magic
    def best_options(self, limit):
        """Scores all remaining options against the position scores for remaining words"""
        game, limit = self._prs(limit)
        limit = int(limit) if limit else self.limit
        return best_options(game)[:-limit]

    @line_magic
    def novelty(self, words):
        game, words = self._prs(words)
        words = words.split()
        return [(score, word) for score, word in zip(novelty(game, *words), words)]

    def _best_elim(self, game, wordlist):
        self._summarize(game)

        try:
            return [_format_welim(t) for t in best_elim(hashable(game), wordlist)[-self.limit :]]
        finally:
            elim_store.commit()

    @line_magic
    def best_elim(self, line):
        """Limit in this case only calculates against the first N words as
        scored by the best_novelty scorer.  This algorithm is N**2 and
        very expensive, so it generally shouldn't be run against lots
        of options.
        """
        game, limit_instr = self._prs(line)
        limit_instr += f" {auto_limit(len(get_options(game)))}"

        return self._best_elim(
            game,
            _instruction_line_to_chosen_wordlist(limit_instr, **all_or_opts_wordlist_creators([game])),
        )

    @line_magic
    def be(self, limit):
        return self.best_elim(limit)

    @line_magic
    def bootstrap(self, line):
        self.reset(None)
        guesses = line.split(" ")
        for i, guess in enumerate(guesses):
            self._guess(self._new_game(i), guess)

    @line_magic
    def games(self, _):
        for game in self.games.values():
            self._summarize(game)

    @line_magic
    def delete(self, game):
        del self.games[int(game)]

    @line_magic
    def cross(self, line):
        """Cross-elimination uses all games to find a good next guess"""

        games = list(self.games.values())

        wordlist = _instruction_line_to_chosen_wordlist(line, **all_or_opts_wordlist_creators(games))

        def fmt_ce(ce):
            solutions = "".join(["🟩" if k in ce.solved else "⬛" for k in self.games.keys()])
            options = "".join(["🟨" if k in ce.option else "⬛" for k in self.games.keys()])
            return (f"{ce.elim_ratio:8.3f}", solutions, options)

        try:
            return [(w, *fmt_ce(ce)) for w, ce in elim_across_games(self.games, wordlist)[-self.limit :]]
        finally:
            elim_store.commit()

    @line_magic
    def elim(self, words):
        game, words = self._prs(words)
        return self._best_elim(game, words.split())

    @line_magic
    def pop(self, line):
        game, count = self._prs(line)
        for _ in range(int(count) if count else 1):
            game.guesses.pop()
        return self.g("")

    @line_magic
    def scores(self, line):
        game, _ = self._prs(line)
        return construct_position_freqs(get_options(game))

    @line_magic
    def reset(self, game):
        if isinstance(game, int) or game and isinstance(game, str):
            self._new_game(int(game))
        else:
            self.games = dict()
            self.game_key = 1
            self._new_game(self.game_key)

    def _remove_prev_sols(self):
        """We don't do this by default. It's only for when you're pretty sure you've
        guessed a word before and you don't want to re-guess it, but also don't want to go
        check manually.
        """
        prev_sols = self._previous_solutions()
        for game in self.games.values():
            game.ignored |= set(prev_sols)
            self._summarize(game)

    @line_magic
    def rms(self, word):
        self._remove_prev_sols()


def load_ipython_extension(ipython):  # magic name
    ipython.register_magics(IpythonCli)
    ipython.register_magics(IpythonCli)
