from typing import List, Tuple
import json
import random
import re

import getpass
from IPython.core.magic import Magics, magics_class, line_magic

from .constrain import ALPHA, guess_to_word
from .colors import colorize
from .elimination import answer
from .scoring import construct_position_freqs, score_words
from .words import five_letter_word_list, sols
from .game import best_elim, best_options, Game, novelty, new_game, letters, get_options
from .multi import elim_across_games


def kill_words(*words: str) -> None:
    with open("killed.txt", "a") as f:
        for word in words:
            if word:
                f.write(word + "\n")


def _p(game: Game):
    return "  ".join(colorize(*game.guesses))


def _f(f: float) -> str:
    return f"{f:8.3f}"


@magics_class
class IpythonCli(Magics):
    def __init__(self, shell, guesses: List[str] = list()):
        # You must call the parent constructor
        super().__init__(shell)
        self.limit = 15
        self.wl = five_letter_word_list
        self.n = len(self.wl[0])
        self.reset(None)

    def _new_game(self, index: int):
        with open("killed.txt") as f:
            to_ignore = set(f.read().splitlines())
        game = new_game(ALPHA, self.wl)
        game.ignored = to_ignore
        self.games[index] = game

    def _prs(self, line) -> Tuple[Game, str]:
        m = re.match(r"^\s*(\d+)(.*)", line or "")
        if m:
            game_number = int(m.group(1))
            self.game_idx = game_number
            if game_number not in self.games:
                self._new_game(game_number)  # create new game
            return self.games[game_number], m.group(2)
        return self.games[self.game_idx], line

    @line_magic
    def game(self, index):
        index = int(index)
        assert index < len(self.games)
        self.game_idx = index
        self.guesses(str(index))

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

    def format(self, guess: str):
        game, guess = self._prs(guess)
        assert game.solution
        return answer(game.solution, guess) or guess

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
    def play(self, _):
        self.reset(None)
        self.games[0].solution = random.choice(sols)

    @line_magic
    def record(self, _):
        """Call this after finishing a game."""
        assert len(self.games) == 1
        game = self.games[0]
        if len(guess_to_word(game.guesses[-1])) == self.n and len(get_options(game)) == 1:
            with open("played.json", "a") as f:
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

    def _summarize(self, game):
        for game_number, g in self.games.items():
            if game is g:
                break
        print(
            f"# Game {game_number: 2}, options: {len(get_options(game)): 4}, "
            f"user-selected: {len(self.input_possibilities(game))}, guesses: " + _p(game)
        )
        return game.guesses

    def _guess(self, game, line):
        for guess in line.split(" "):
            if guess:
                if game.solution:
                    guess = self.format(guess)
                if guess_to_word(guess) not in five_letter_word_list:
                    return None
                if guess not in game.guesses:
                    game.guesses.append(guess)
                if len(guess) == self.n and guess.upper() == guess:
                    print("\nSUCCESS!! Don't forget to %record this result!\n")
        return self._summarize(game)

    @line_magic
    def guesses(self, _, game):
        game, _ = self._prs(_)
        self._summarize(game)

    @line_magic
    def guess(self, line: str):
        self._guess(*self._prs(line))

    @line_magic
    def g(self, line):
        return self.guess(line)

    @line_magic
    def n(self, line):
        game, line = self._prs(line)
        game.guesses = list()
        self._guess(game, line)

    @line_magic
    def o(self, line):
        """Input an option that you have considered."""
        game, line = self._prs(line)
        options = set(get_options(game))
        for word in line.split():
            if word not in options:
                print(f"{word} not an option")
            game.possibilities.add(word)
        self._summarize(game)
        return game.possibilities

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

    def _best_elim(self, game, wl, limit: int = 30):
        self._summarize(game)
        return [
            (t[0], t[1], "⬜" if t[2] else "⬛", t[3]) for t in best_elim(game, wl, limit)[-self.limit :]
        ]

    @line_magic
    def best_elim(self, limit):
        """Limit in this case only calculates against the first N words as
        scored by the best_novelty scorer.  This algorithm is N**2 and
        very expensive, so it generally shouldn't be run against lots
        of options.
        """
        game, limit = self._prs(limit)
        return self._best_elim(game, None, int(limit) if limit else 30)

    @line_magic
    def games(self, _):
        for game in self.games.values():
            self._summarize(game)

    @line_magic
    def delete(self, game):
        del self.games[int(game)]

    @line_magic
    def cross(self, num_to_test):
        def fmt_ce(ce):
            return (_f(ce.elim_ratio), ce.option_count, ce.solve_count)

        num_to_test = int(num_to_test) if num_to_test else 30
        return [
            (w, *fmt_ce(ce))
            for w, ce in elim_across_games(self.games.values(), num_to_test)[-self.limit :]
        ]

    @line_magic
    def elim(self, words):
        game, words = self._prs(words)
        return self._best_elim(game, wl=words.split())

    @line_magic
    def pop(self, line):
        game, count = self._prs(line)
        for _ in range(int(count) if count else 1):
            game.guesses.pop()
        return self.guesses(line.split()[0])

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
            self.game_idx = 0
            self._new_game(0)


def load_ipython_extension(ipython):  # magic name
    ipython.register_magics(IpythonCli)
