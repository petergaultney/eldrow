import math
import os

_IS_SLOW = os.getenv("ELDROW_SLOW")


TAKES_ONE_SECOND = 14000
TAKES_TWENTY_SECONDS = TAKES_ONE_SECOND * 20


def auto_limit(n_options: int) -> int:
    if not _IS_SLOW:
        return 14000
    max = TAKES_TWENTY_SECONDS / n_options
    al = math.ceil(max / 1000) * 1000
    print(f"Using auto limit {al} with {n_options} options")
    return al
