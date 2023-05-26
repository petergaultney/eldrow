import typing as ty
from functools import wraps

from sqlitedict import SqliteDict

F = ty.TypeVar("F", bound=ty.Callable)

sb = str | bytes


def pickle_cache(db: ty.MutableMapping[sb, bytes]) -> ty.Callable[[F], F]:
    """Memoize very expensive functions across multiple runs of the
    same program.

    All arguments to the decorated function must be recursively
    hashable with the builtin `hash` function, and its return value
    must be pickleable.
    """

    def deco(f: F) -> F:
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                composite_hash = str(hash((args, tuple(kwargs.items()))))
            except TypeError:
                print("Failed to hash: ", args, kwargs)
                raise
            if composite_hash in db:
                return db[composite_hash]
            result = f(*args, **kwargs)
            db[composite_hash] = result
            return result

        return ty.cast(F, wrapper)

    return deco


elim_store = SqliteDict("elim_store.sqlite", autocommit=True)
elim_cache = pickle_cache(elim_store)
