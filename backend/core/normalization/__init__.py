from .normalizer import normalize_ingredient_key

__all__ = ["normalize_ingredient_key", "flatten_ingredients"]


def __getattr__(name: str):
    if name == "flatten_ingredients":
        from .parser import flatten_ingredients as _flatten

        return _flatten
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
