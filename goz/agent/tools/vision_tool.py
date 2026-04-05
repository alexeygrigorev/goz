"""Vision tool for image and video analysis (Issue 20).

This module provides the DescribeImageTool class for analyzing images
and videos using the Z.AI Vision API.
"""
from __future__ import annotations

from typing import Any

from goz.agent.tools.base import BaseTool, ToolInputError
from goz.api.vision import VisionClient
from goz.api.image import validate_image_source, validate_video_source, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS


class DescribeImageTool(BaseTool):
    """Tool for analyzing images and videos using the Vision API.

    Wraps the existing VisionClient to provide image/video analysis
    functionality for the agent, including:
    - General image description
    - Text extraction (OCR)
    - Error diagnosis from screenshots
    - UI-to-code conversion

    Attributes:
        name: Tool identifier ("describe_image")
        description: Human-readable description
        input_schema: JSON Schema for tool inputs
    """

    name = "describe_image"
    description = (
        "Analyze an image or video. Supports local files (jpg, jpeg, png, mp4, mov, etc.) "
        "and URLs (http/https). Use for understanding screenshots, diagrams, UI designs, "
        "error messages, or extracting text from images."
    )
    input_schema = {
        "type": "object",
        "properties": {
            "source": {
                "type": "string",
                "description": (
                    "Path to a local image/video file or a URL (http/https). "
                    "Supported image formats: .jpg, .jpeg, .png (max 5MB). "
                    "Supported video formats: .mp4, .mov, .m4v, .avi, .webm, .wmv (max 8MB)."
                ),
            },
            "prompt": {
                "type": "string",
                "description": (
                    "Optional custom prompt for analysis. "
                    "If not provided, a general description prompt is used."
                ),
            },
            "task": {
                "type": "string",
                "enum": ["describe", "extract_text", "diagnose_error", "ui_to_code"],
                "description": (
                    "Analysis task type. 'describe' for general analysis (default), "
                    "'extract_text' for OCR, 'diagnose_error' for error screenshots, "
                    "'ui_to_code' to convert UI designs to HTML/CSS."
                ),
            },
        },
        "required": ["source"],
    }

    def __init__(self, config: Any) -> None:
        """Initialize DescribeImageTool.

        Args:
            config: Configuration object for the VisionClient
        """
        super().__init__()
        self.config = config
        self.client = VisionClient(config)

    async def execute(
        self,
        source: str,
        prompt: str | None = None,
        task: str = "describe",
    ) -> str:
        """Analyze an image or video.

        Args:
            source: Image/video file path or URL
            prompt: Optional custom prompt for analysis
            task: Analysis task type (describe, extract_text, diagnose_error, ui_to_code)

        Returns:
            Analysis result text
        """
        data: dict[str, Any] = {"source": source}
        if prompt is not None:
            data["prompt"] = prompt
        if task is not None:
            data["task"] = task
        self.validate_input(self.input_schema, data)

        if not source.strip():
            raise ToolInputError("Field 'source' cannot be empty")

        if task not in ("describe", "extract_text", "diagnose_error", "ui_to_code"):
            raise ToolInputError(
                f"Field 'task' must be one of: describe, extract_text, diagnose_error, ui_to_code. Got: {task}"
            )

        if prompt is not None and not prompt.strip():
            raise ToolInputError("Field 'prompt' cannot be empty when provided")

        # Validate the source file/url
        try:
            from goz.api.image import is_url
            if is_url(source):
                # URLs are always valid per existing validation
                pass
            else:
                from pathlib import Path
                ext = Path(source).suffix.lower()
                if ext in VIDEO_EXTENSIONS:
                    validate_video_source(source)
                else:
                    validate_image_source(source)
        except (FileNotFoundError, ValueError) as e:
            return str(e)

        # Execute the appropriate analysis task
        try:
            if task == "extract_text":
                result = await self.client.extract_text(source)
            elif task == "diagnose_error":
                result = await self.client.diagnose_error(source)
            elif task == "ui_to_code":
                result = await self.client.ui_to_code(source)
            else:
                result = await self.client.analyze(source, prompt=prompt)
        except Exception as e:
            return f"Image analysis failed: {e}"

        return result
