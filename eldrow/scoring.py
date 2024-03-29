from collections import defaultdict
from typing import Callable, Collection, Dict, List, Tuple

from .words import five_letter_word_list

PositionScores = Dict[int, Dict[str, float]]


def _sort_dict_by_values(d):
    return {k: v for k, v in sorted(d.items(), key=lambda item: item[1])}


def _xf_dict_vals(xf, d):
    return {k: xf(v) for k, v in d.items()}


def construct_position_freqs(word_list: Collection[str], decimal_points=5) -> PositionScores:
    counts: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(int))
    for word in word_list:
        for i, char in enumerate(word):
            counts[i][char] += 1

    def count_to_freq(count: int) -> float:
        return round(count / len(word_list), decimal_points)

    return {k: _xf_dict_vals(count_to_freq, _sort_dict_by_values(v)) for k, v in counts.items()}


position_scores: PositionScores = construct_position_freqs(five_letter_word_list)


Scorer = Callable[..., float]


def score_words(position_scores: dict = position_scores) -> Scorer:
    """Scores words based on total positional score across the word list."""

    def _score_words(*words: str) -> float:
        scored_in_position: dict[int, dict[str, bool]] = defaultdict(lambda: defaultdict(lambda: False))

        def score_word(w: str) -> float:
            word_score = 0
            for i, c in enumerate(w):
                if i not in position_scores:
                    break
                pos = position_scores[i]
                if c not in pos:
                    # letter literally not an option in this location.
                    # it gets no score here, and will be fully scored
                    # elsewhere.
                    continue
                pos_score = pos[c]
                if scored_in_position[i][c]:
                    continue
                scored_in_position[i][c] = True
                word_score += pos_score
            return word_score

        return round(sum(score_word(w) for w in words), 3)

    return _score_words


def score_for_novelty(position_scores: dict = position_scores) -> Scorer:
    """Scores words based on novelty of each character.

    In other words, we want as many different characters as possible,
    with as high a score in each position as possible.
    """

    def _score_for_novelty(*words: str) -> float:
        characters_scored = set()

        def score_word(word: str) -> float:
            wscore = 0.0
            sorted_pos_scores = sorted(
                [(position_scores[i].get(c, 0.0), i, c) for i, c in enumerate(word)],
                reverse=True,
            )
            for pos_score, i, c in sorted_pos_scores:
                if c in characters_scored:
                    continue
                characters_scored.add(c)
                wscore += pos_score
            return wscore

        return round(sum(score_word(word) for word in words), 3)

    return _score_for_novelty


def best_next_score(
    word_list: Collection[str], *starting_words, scorer=score_words()
) -> List[Tuple[int, str]]:
    """Determines a best next word score without regard to solving.

    Mostly useful for playing around with different combinations of
    two and three word starts, to find something you actually like.
    """
    best_words = list()
    for w_next in word_list:
        best_words.append((scorer(*starting_words, w_next), w_next))

    try:
        print(scorer.hit_rate)
    except AttributeError:
        pass

    return sorted(best_words, key=lambda t: t[0])


def _remove_solved(position_scores: PositionScores) -> PositionScores:
    return {pos: (val if len(val) > 1 else dict()) for pos, val in position_scores.items()}


def replace_solved_with_average_totals(
    position_scores: PositionScores,
) -> PositionScores:
    avg_unsolved_total: dict[str, float] = defaultdict(int)
    solved_letters = {
        list(letters.keys())[0] for letters in position_scores.values() if len(letters) == 1
    }
    for pos, scores in position_scores.items():
        if len(scores) > 1:
            for letter, score in scores.items():
                if letter not in solved_letters:
                    avg_unsolved_total[letter] += score / len(position_scores)
    return {
        pos: (scores if len(scores) > 1 else dict(avg_unsolved_total))
        for pos, scores in position_scores.items()
    }
