from typing import List
import json
import random

from IPython.core.magic import Magics, magics_class, line_magic

from .constrain import given2, regexes2, ALPHA, guess_to_word
from .colors import colorize
from .elimination import answer, options, elimination_scorer, make_options
from .scoring import (
    construct_position_freqs,
    best_next_score,
    score_words,
    score_for_novelty,
    replace_solved_with_average_totals,
)
from .words import five_letter_word_list, sols


def kill_words(*words: str) -> None:
    with open("killed.txt", "a") as f:
        for word in words:
            if word:
                f.write(word + "\n")


def _simple_words(*guesses) -> List[str]:
    return [guess_to_word(guess) for guess in guesses]


@magics_class
class IpythonCli(Magics):
    def __init__(self, shell, guesses: List[str] = list()):
        # You must call the parent constructor
        super().__init__(shell)
        self.limit = 30
        self.reset(None)
        self.n = 5
        self.wl = five_letter_word_list
        self.alpha = ALPHA

    @line_magic
    def word_list(self, _):
        if self.wl is five_letter_word_list:
            self.wl = sols
            print("Switched to solutions - cheater...")
        else:
            self.wl = five_letter_word_list
            print("Switched to full word list")
        return self.guesses(_)

    @line_magic
    def wl(self, _):
        self.word_list(_)

    def possibilities(self):
        return given2(*self._guesses, alpha=self.alpha, empty_n=self.n)

    @line_magic
    def poss(self, _):
        return self.possibilities()

    def _cur_options(self) -> List[str]:
        return [w for w in options(regexes2(self.possibilities()), wl=self.wl) if w not in self._ignored]

    def format(self, guess):
        assert self._solution
        return answer(self._solution, guess) or guess

    @line_magic
    def ignore(self, words):
        self._ignored |= set(words.split())

    @line_magic
    def limit(self, line):
        if line:
            self.limit = int(line)
        else:
            return self.limit

    @line_magic
    def play(self, _):
        self.solution(random.choice(sols))

    @line_magic
    def record(self, _):
        """Call this after finishing a game."""
        if len(guess_to_word(self._guesses[-1])) == self.n and len(self._cur_options()) == 1:
            with open("played.json", "a") as f:
                f.write(json.dumps(self._guesses) + "\n")

    @line_magic
    def solution(self, line):
        """For testing purposes. If you know the answer and want to manually
        try to 'discover' it using various tools, you can put the
        solution in, and that will make typing easier.
        """
        if line:
            self.reset(None)
            self._solution = line
        else:
            import getpass

            self._solution = getpass.getpass("Solution? ")

    @line_magic
    def p(self, _):
        for colorized in colorize(*self._guesses):
            print(colorized)

    @line_magic
    def words(self, _):
        return _simple_words(*self._guesses)

    @line_magic
    def score(self, words):
        return score_words(construct_position_freqs(self._cur_options()))(*words.split())

    @line_magic
    def guesses(self, _):
        print(f"# options: {len(self._cur_options())}, input options: {len(self.input_options())}")
        self.p(None)
        return self._guesses

    @line_magic
    def guess(self, line: str):
        for guess in line.split(" "):
            if guess:
                if self._solution:
                    guess = self.format(guess)
                if guess_to_word(guess) not in five_letter_word_list:
                    return None
                if guess not in self._guesses:
                    self._guesses.append(guess)
                if len(guess) == 5 and len(self._cur_options()) == 1:
                    print("\nSUCCESS!! Don't forget to %record this result!\n")
        return self.guesses(None)

    @line_magic
    def letters(self, _):
        pos_allowed, _ = self.possibilities()
        return " ".join(sorted({c.upper() for allowed in pos_allowed.values() for c in allowed}))

    @line_magic
    def g(self, line):
        return self.guess(line)

    @line_magic
    def n(self, line):
        self.reset(None)
        self.g(line)

    def input_options(self):
        opts = set(self._cur_options())
        return sorted([k for k in self._input_options if k in opts])

    @line_magic
    def o(self, line):
        """Input an option that you have considered."""
        for word in line.split():
            if word not in self._cur_options():
                print(f"{word} not an option")
            self._input_options.add(word)
        self.guesses(None)
        return self.input_options()

    @line_magic
    def ideas(self, _):
        return [f"{idea} ({i + 1})" for i, idea in enumerate(self.ideas)]

    @line_magic
    def idea(self, line):
        idea_num = int(line)
        if idea_num > 0 and idea_num <= len(self.ideas):
            self.guess(self.ideas[idea_num - 1])

    @line_magic
    def kill(self, words):
        self.ignore(words)
        kill_words(*words.split())

    @line_magic
    def options(self, _):
        opts = self._cur_options()
        return opts, len(opts)

    @line_magic
    def best_options(self, limit):
        """Scores all remaining options against the position scores for remaining words"""
        remaining_words = self._cur_options()
        limit = int(limit) if limit else self.limit
        return best_next_score(
            remaining_words,
            *_simple_words(*self._guesses),
            scorer=score_words(construct_position_freqs(remaining_words)),
        )[-limit:]

    def _info_scorer(self):
        return score_for_novelty(
            replace_solved_with_average_totals(construct_position_freqs(self._cur_options()))
        )

    @line_magic
    def info(self, words):
        scorer = self._info_scorer()
        cur_words = _simple_words(*self._guesses)
        return [scorer(*cur_words, w) for w in words.split()]

    @line_magic
    def best_info(self, limit):
        """Uses full word list to maximize information score, rather than limiting to words it 'could' be"""
        limit = int(limit) if limit else self.limit
        return [
            (info_score, self.elim(word)[0][0], word)
            for info_score, word in best_next_score(
                [w for w in self.wl if w not in self._ignored],
                *_simple_words(*self._guesses),
                scorer=self._info_scorer(),
            )[-limit:]
        ]

    @line_magic
    def best_elim(self, limit, wl=None):
        """Limit in this case only calculates against the first N words as
        scored by the best_info scorer.  This algorithm is N**2 and
        very expensive, so it generally shouldn't be run against lots
        of options.
        """
        opts = self._cur_options()
        words_to_test = wl or (set([res[2] for res in self.best_info(limit)]) | set(opts[:30]))
        return [
            (score, self.info(word)[0], "⬜" if word in opts else "⬛", word)
            for score, word in best_next_score(
                words_to_test,
                *list(map(guess_to_word, self._guesses)),
                scorer=elimination_scorer(
                    opts,
                    make_options(
                        self.alpha,
                        opts,
                        self._guesses,
                    ),
                ),
            )[-self.limit :]
        ]

    @line_magic
    def elim(self, words):
        words = words.split()
        return self.best_elim(None, wl=words)

    @line_magic
    def elim_opts(self, limit):
        return self.best_elim(limit, wl=self._cur_options())

    @line_magic
    def pop(self, count):
        count = int(count) if count else 1
        for _ in range(count):
            idea = self._guesses.pop()
            if idea not in self.ideas:
                self.ideas.append(idea)
        return self.guesses(None)

    @line_magic
    def scores(self, _):
        return construct_position_freqs(self._cur_options())

    @line_magic
    def reset(self, _):
        self._guesses = list()
        self.ideas = list()
        self._solution = ""
        self._input_options = set()
        with open("killed.txt") as f:
            self._ignored = set(f.read().splitlines())


def load_ipython_extension(ipython):  # magic name
    ipython.register_magics(IpythonCli)
