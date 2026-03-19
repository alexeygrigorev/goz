"""Configuration management for goz.

Config file location: ~/.config/goz/config.json
"""
import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


# Default config paths (Acceptance Criteria 1)
DEFAULT_CONFIG_DIR = Path.home() / ".config" / "goz"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"

# Default values (Acceptance Criteria 2)
DEFAULT_ZAI_BASE_URL = "https://api.z.ai/api/coding/paas/v4"
DEFAULT_TIMEOUT = 300000  # 5 minutes in milliseconds
DEFAULT_TIMEOUT_SECONDS = 120  # For Python clients (seconds)

# Default model names
DEFAULT_VISION_MODEL = "glm-4.6v"
DEFAULT_CHAT_MODEL = "glm-5-turbo"

# Generation parameters
DEFAULT_TEMPERATURE = 0.8
DEFAULT_TOP_P = 0.6
DEFAULT_MAX_TOKENS = 32768


class Config(BaseModel):
    """Configuration model for goz.

    Fields:
        zai_token: Z.AI auth token for API access (like apiKey in zai-cli)
        zai_base_url: Base URL for API (like baseUrl in zai-cli)
        timeout: Request timeout in seconds
        vision_model: Model for image/video analysis
        chat_model: Model for chat/text requests
        temperature: Generation temperature
        top_p: Generation top_p
        max_tokens: Maximum tokens in response
    """

    zai_token: str
    zai_base_url: str = DEFAULT_ZAI_BASE_URL
    timeout: int = Field(default=DEFAULT_TIMEOUT_SECONDS, gt=0)
    vision_model: str = DEFAULT_VISION_MODEL
    chat_model: str = DEFAULT_CHAT_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    top_p: float = DEFAULT_TOP_P
    max_tokens: int = DEFAULT_MAX_TOKENS

    @field_validator("zai_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        """Validate token is not empty."""
        if not v or not v.strip():
            raise ValueError("zai_token cannot be empty")
        return v


class ConfigManager:
    """Manager for loading and saving configuration."""

    def __init__(self, config_file: Path | None = None):
        """Initialize ConfigManager.

        Args:
            config_file: Path to config file. Defaults to DEFAULT_CONFIG_FILE.
        """
        self.config_file = config_file or DEFAULT_CONFIG_FILE
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Create config directory if it doesn't exist (Acceptance Criteria 3, 6)."""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Config:
        """Load configuration from file.

        Returns:
            Config object

        Raises:
            json.JSONDecodeError: If config file contains invalid JSON
            ValidationError: If config data is invalid
        """
        if not self.config_file.exists():
            return self._prompt_and_create()

        # Check if file is empty
        if self.config_file.stat().st_size == 0:
            return self._prompt_and_create()

        try:
            with open(self.config_file) as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # Invalid JSON - show error and re-raise
            print(f"Error: Invalid JSON in config file at {self.config_file}")
            raise

        return Config.model_validate(data)

    def save(self, config: Config) -> None:
        """Save configuration to file.

        Args:
            config: Config object to save
        """
        self._ensure_config_dir()
        with open(self.config_file, "w") as f:
            f.write(config.model_dump_json(indent=2))

    def _prompt_and_create(self) -> Config:
        """Prompt user for token and create config file (Acceptance Criteria 3, 4)."""
        token = input("Enter your Z.AI auth token: ")

        config = Config(zai_token=token)
        self.save(config)

        print(f"Config saved to {self.config_file}")
        return config

    def show_config(self) -> None:
        """Display current configuration with masked token (Acceptance Criteria 6, 7)."""
        config = self.load()

        # Mask token - show only last 4 chars (Acceptance Criteria 7)
        masked_token = self._mask_token(config.zai_token)

        print(f"zai_token: {masked_token}")
        print(f"zai_base_url: {config.zai_base_url}")
        print(f"timeout: {config.timeout}")

    def _mask_token(self, token: str) -> str:
        """Mask token showing only last 4 characters.

        Args:
            token: The token to mask

        Returns:
            Masked token string
        """
        if len(token) <= 4:
            return f"****{token}"
        return f"****{token[-4:]}"

    def set_config(self, key: str, value: str) -> None:
        """Update a specific configuration field (Acceptance Criteria 8).

        Args:
            key: Configuration key to update
            value: New value

        Raises:
            ValueError: If key is invalid or value cannot be converted
        """
        config = self.load()

        valid_keys = ["zai_token", "zai_base_url", "timeout", "vision_model", "ocr_model", "chat_model"]

        if key not in valid_keys:
            raise ValueError(f"Invalid config key: {key}. Valid keys: {', '.join(valid_keys)}")

        if key == "timeout":
            try:
                value_int = int(value)
                if value_int <= 0:
                    raise ValueError("timeout must be a positive integer")
                setattr(config, key, value_int)
            except ValueError as e:
                raise ValueError(f"Invalid timeout value: {e}") from e
        else:
            setattr(config, key, value)

        self.save(config)
        print("Config updated successfully")


def load_config() -> Config:
    """Load configuration, prompting for first-time setup if needed.

    Returns:
        Config object
    """
    manager = ConfigManager()
    return manager.load()
