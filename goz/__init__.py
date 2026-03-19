from goz.__version__ import __version__


def hello(name: str = "world") -> str:
    """Say hello to someone."""
    return f"Hello, {name}!"


__all__ = ["__version__", "hello"]
