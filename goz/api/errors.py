"""Error types for Z.AI API client.

These error types are used throughout the API client for consistent error handling.
"""

from __future__ import annotations



class ZaiError(Exception):
    """Base error class for all Z.AI API errors.

    Attributes:
        message: Human-readable error message
        code: Error code for programmatic handling
        statusCode: HTTP status code (optional)
        help: Helpful hint for resolving the error (optional)
    """

    def __init__(
        self,
        message: str,
        code: str = "ZAI_ERROR",
        statusCode: int | None = None,
        help: str | None = None,
    ) -> None:
        """Initialize ZaiError.

        Args:
            message: Human-readable error message
            code: Error code for programmatic handling
            statusCode: HTTP status code (optional)
            help: Helpful hint for resolving the error (optional)
        """
        self.message = message
        self.code = code
        self.statusCode = statusCode
        self.help = help
        super().__init__(self.message)

    def __str__(self) -> str:
        """Return string representation showing error code and message."""
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        """Return detailed string representation."""
        return (
            f"{self.__class__.__name__}(message={self.message!r}, code={self.code!r}, "
            f"statusCode={self.statusCode!r}, help={self.help!r})"
        )


class AuthError(ZaiError):
    """Authentication/authorization error (401, 403).

    This error is raised when the API token is invalid, expired, or missing.
    """

    def __init__(self, message: str, statusCode: int = 401) -> None:
        """Initialize AuthError.

        Args:
            message: Human-readable error message
            statusCode: HTTP status code (default: 401)
        """
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            statusCode=statusCode,
            help="Authentication failed. Check your API key in ~/.config/goz/config.json. "
            "Run 'goz config set zai_token <your-token>' to update.",
        )


class ApiError(ZaiError):
    """General API error (4xx, 5xx responses).

    This error is raised for API errors that are not authentication-related.
    """

    def __init__(self, message: str, statusCode: int = 500) -> None:
        """Initialize ApiError.

        Args:
            message: Human-readable error message
            statusCode: HTTP status code (default: 500)
        """
        super().__init__(
            message=message,
            code="API_ERROR",
            statusCode=statusCode,
            help=self._default_help(statusCode),
        )

    @staticmethod
    def _default_help(status_code: int) -> str:
        """Return actionable guidance based on HTTP status code."""
        if status_code == 429:
            return "Rate limit hit. Wait a moment before retrying, or reduce request volume."
        if status_code >= 500:
            return "The service is having problems. Retry shortly; if it persists, try again later."
        return "Check the request input and try again."


class NetworkError(ZaiError):
    """Network connection error.

    This error is raised when the client cannot connect to the API server.
    """

    def __init__(self, message: str) -> None:
        """Initialize NetworkError.

        Args:
            message: Human-readable error message
        """
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            help="Network connection failed. Check your internet connection and try again.",
        )


class TimeoutError(ZaiError):
    """Request timeout error.

    This error is raised when the API request takes too long to complete.
    """

    def __init__(self, timeoutMs: int) -> None:
        """Initialize TimeoutError.

        Args:
            timeoutMs: Timeout value in milliseconds
        """
        super().__init__(
            message=f"Request timed out after {timeoutMs}ms",
            code="TIMEOUT_ERROR",
            help="Try again or increase timeout with Z_AI_TIMEOUT env var",
        )


class ValidationError(ZaiError):
    """Validation error for invalid input parameters.

    This error is raised when input validation fails, such as invalid URLs,
    invalid format values, or other parameter validation issues.
    """

    def __init__(self, message: str) -> None:
        """Initialize ValidationError.

        Args:
            message: Human-readable error message describing the validation failure
        """
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            help="Check your input parameters and try again.",
        )
