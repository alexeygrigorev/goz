"""API module for goz."""

from goz.api.client import ZaiApiClient
from goz.api.errors import ApiError, AuthError, NetworkError, TimeoutError, ValidationError, ZaiError
from goz.api.reader import ReaderClient, ReaderResult
from goz.api.search import SearchClient, SearchResult, RecencyFilter

__all__ = [
    "ZaiApiClient",
    "ZaiError",
    "AuthError",
    "ApiError",
    "NetworkError",
    "TimeoutError",
    "ValidationError",
    "ReaderClient",
    "ReaderResult",
    "SearchClient",
    "SearchResult",
    "RecencyFilter",
]
