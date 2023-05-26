import typing as ty
from functools import wraps

from sqlitedict import SqliteDict

F = ty.TypeVar("F", bound=ty.Callable)
Deco = ty.Callable[[F], F]
DecoFactory = ty.Callable[..., Deco]

sb = str | bytes


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
            @wraps(f)
            def wrapper(*args, **kwargs):
                try:
                    tup = (args, tuple(kwargs.items()))
                    if base_hash is not None:
                        tup = (base_hash, *tup)  # type: ignore
                    composite_hash = str(hash(tup))
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

    return deco_factory


elim_store = SqliteDict("elim_store.sqlite", autocommit=True)
elim_cache = pickle_cache(elim_store)
