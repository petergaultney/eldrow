import sys
import typing as ty
from functools import wraps

from sqlitedict import SqliteDict

F = ty.TypeVar("F", bound=ty.Callable)
Deco = ty.Callable[[F], F]
DecoFactory = ty.Callable[..., Deco]

sb = str | bytes


assert sys.flags.hash_randomization == 0, "hash randomization must be disabled for memoization to work"


class Memoizing:
    def __init__(self, db: ty.MutableMapping[sb, bytes], base_hash: ty.Hashable, f: F):
        self.db = db
        self.base_hash = base_hash
        self.f = f

        self._misses = 0
        self._tot = 0

    def __call__(self, *args, **kwargs):
        self._tot += 1
        db, base_hash, f = self.db, self.base_hash, self.f
        try:
            tup = (args, tuple(kwargs.items()))
            if base_hash is not None:
                tup = (base_hash, *tup)  # type: ignore
            composite_hash = str(hash(tup))
        except TypeError:
            print("Failed to hash: ", args, kwargs)
            raise
        try:
            return db[composite_hash]
        except KeyError:
            result = f(*args, **kwargs)
            db[composite_hash] = result
            self._misses += 1
            return result

    @property
    def hits(self) -> int:
        return self._tot - self._misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self._tot


def pickle_cache(db: ty.MutableMapping[sb, bytes]) -> DecoFactory:
    """Memoize very expensive functions across multiple runs of the
    same program.

    All arguments to the decorated function must be recursively
    hashable with the builtin `hash` function, and its return value
    must be pickleable.
    """

    def deco_factory(*outer_args, **outer_kwargs) -> Deco:
        if outer_args or outer_kwargs:
            base_hash = hash((outer_args, tuple(outer_kwargs.items())))
        else:
            base_hash = None

        def deco(f: F) -> F:
            return ty.cast(F, wraps(f)(Memoizing(db, base_hash, f)))

        return deco

    return deco_factory


elim_store = SqliteDict("eldrow_elim_store.sqlite", outer_stack=False)
elim_cache = pickle_cache(elim_store)
