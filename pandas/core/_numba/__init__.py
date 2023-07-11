def _register_extensions() -> None:
    """
    Exposes the DF/Series/Index extension types so users
    can use them in numba code.

    Called via the numba_extensions entry point in pyproject.toml
    """
