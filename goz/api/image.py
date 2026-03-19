"""Image and video processing utilities for vision API.

This module provides utilities for validating, encoding, and processing
image and video files for the Z.AI vision API.
"""
import base64
from pathlib import Path

# Constants (Acceptance Criteria 5-8)
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_VIDEO_SIZE = 8 * 1024 * 1024  # 8MB

# Supported file extensions
IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
VIDEO_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.avi', '.webm', '.wmv']

# MIME type mapping for images
IMAGE_MIME_TYPES = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
}

# MIME type mapping for videos
VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mov': 'video/quicktime',
    '.m4v': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.webm': 'video/webm',
    '.wmv': 'video/x-ms-wmv',
}


def is_url(source: str) -> bool:
    """Check if source is a URL (http:// or https://).

    Args:
        source: The source string to check

    Returns:
        True if source is a URL, False otherwise
    """
    return source.startswith('http://') or source.startswith('https://')


def validate_image_source(source: str) -> None:
    """Validate an image source (local file or URL).

    Args:
        source: Image file path or URL

    Raises:
        FileNotFoundError: If local file doesn't exist
        ValueError: If file size exceeds limit or format is unsupported
    """
    # URLs are always valid
    if is_url(source):
        return

    # Resolve and validate local file
    file_path = Path(source).expanduser().resolve()

    # Check file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {source}. Check the file path is correct.")

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_IMAGE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(f"Image exceeds 5MB limit ({size_mb:.2f}MB)")

    # Check file extension
    ext = file_path.suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        supported = ', '.join(IMAGE_EXTENSIONS)
        raise ValueError(f"Unsupported image format: {ext}. Supported: {supported}")


def validate_video_source(source: str) -> None:
    """Validate a video source (local file or URL).

    Args:
        source: Video file path or URL

    Raises:
        FileNotFoundError: If local file doesn't exist
        ValueError: If file size exceeds limit or format is unsupported
    """
    # URLs are always valid
    if is_url(source):
        return

    # Resolve and validate local file
    file_path = Path(source).expanduser().resolve()

    # Check file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {source}. Check the file path is correct.")

    # Check file size
    file_size = file_path.stat().st_size
    if file_size > MAX_VIDEO_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise ValueError(f"Video exceeds 8MB limit ({size_mb:.2f}MB)")

    # Check file extension
    ext = file_path.suffix.lower()
    if ext not in VIDEO_EXTENSIONS:
        supported = ', '.join(VIDEO_EXTENSIONS)
        raise ValueError(f"Unsupported video format: {ext}. Supported: {supported}")


def encode_image_to_base64(file_path: str) -> str:
    """Encode an image file to base64 data URI with proper MIME type.

    Args:
        file_path: Path to the image file

    Returns:
        Data URI string in format "data:image/<type>;base64,<encoded>"
    """
    path = Path(file_path).expanduser().resolve()

    # Read file bytes
    with open(path, 'rb') as f:
        data = f.read()

    # Get MIME type
    ext = path.suffix.lower()
    mime_type = IMAGE_MIME_TYPES[ext]

    # Encode to base64
    encoded = base64.b64encode(data).decode('utf-8')

    return f"data:{mime_type};base64,{encoded}"


def encode_video_to_base64(file_path: str) -> str:
    """Encode a video file to base64 data URI with proper MIME type.

    Args:
        file_path: Path to the video file

    Returns:
        Data URI string in format "data:video/<type>;base64,<encoded>"
    """
    path = Path(file_path).expanduser().resolve()

    # Read file bytes
    with open(path, 'rb') as f:
        data = f.read()

    # Get MIME type
    ext = path.suffix.lower()
    mime_type = VIDEO_MIME_TYPES[ext]

    # Encode to base64
    encoded = base64.b64encode(data).decode('utf-8')

    return f"data:{mime_type};base64,{encoded}"


def process_image_source(source: str) -> str:
    """Process an image source for API request.

    For URLs: returns the URL as-is.
    For local files: returns base64 data URI.

    Args:
        source: Image file path or URL

    Returns:
        URL string or base64 data URI
    """
    if is_url(source):
        return source
    return encode_image_to_base64(source)


def process_video_source(source: str) -> str:
    """Process a video source for API request.

    For URLs: returns the URL as-is.
    For local files: returns base64 data URI.

    Args:
        source: Video file path or URL

    Returns:
        URL string or base64 data URI
    """
    if is_url(source):
        return source
    return encode_video_to_base64(source)
