"""Unit tests for image/video processing utilities (Issue 04)."""
import base64

import pytest

from goz.api.image import (
    is_url,
    validate_image_source,
    validate_video_source,
    encode_image_to_base64,
    encode_video_to_base64,
    process_image_source,
    process_video_source,
    MAX_IMAGE_SIZE,
    MAX_VIDEO_SIZE,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
)


class TestIsUrl:
    """Unit Tests: is_url() correctly identifies URLs."""

    def test_is_url_with_https(self):
        """Test is_url returns True for https URLs."""
        assert is_url("https://example.com/image.png") is True

    def test_is_url_with_http(self):
        """Test is_url returns True for http URLs."""
        assert is_url("http://example.com/image.png") is True

    def test_is_url_with_local_path(self):
        """Test is_url returns False for local paths."""
        assert is_url("/path/to/image.png") is False
        assert is_url("C:\\path\\to\\image.png") is False
        assert is_url("./image.png") is False
        assert is_url("../image.png") is False

    def test_is_url_with_relative_path(self):
        """Test is_url returns False for relative paths."""
        assert is_url("image.png") is False

    def test_is_url_with_tilde(self):
        """Test is_url returns False for tilde paths."""
        assert is_url("~/image.png") is False


class TestValidateImageSource:
    """Unit Tests: validate_image_source() for local files and URLs."""

    def test_validate_image_source_accepts_valid_local_file(self, tmp_path):
        """Test validate_image_source accepts valid local files."""
        # Create a small valid image file (just dummy data)
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"PNG_DUMMY_DATA")

        # Should not raise
        validate_image_source(str(image_file))

    def test_validate_image_source_accepts_url(self):
        """Test validate_image_source accepts URLs."""
        # Should not raise
        validate_image_source("https://example.com/image.png")

    def test_validate_image_source_rejects_nonexistent_file(self, tmp_path):
        """Test validate_image_source rejects non-existent files."""
        nonexistent = tmp_path / "does_not_exist.png"

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_image_source(str(nonexistent))

        assert "File not found" in str(exc_info.value)
        assert str(nonexistent) in str(exc_info.value)

    def test_validate_image_source_rejects_file_over_5mb(self, tmp_path):
        """Test validate_image_source rejects files > 5MB."""
        large_file = tmp_path / "large.png"
        # Create a file larger than 5MB
        large_file.write_bytes(b"x" * (MAX_IMAGE_SIZE + 1))

        with pytest.raises(ValueError) as exc_info:
            validate_image_source(str(large_file))

        assert "exceeds 5MB limit" in str(exc_info.value)

    def test_validate_image_source_accepts_exactly_5mb(self, tmp_path):
        """Test validate_image_source accepts exactly 5MB file."""
        # Create a file exactly 5MB
        large_file = tmp_path / "exactly_5mb.png"
        large_file.write_bytes(b"x" * MAX_IMAGE_SIZE)

        # Should not raise
        validate_image_source(str(large_file))

    def test_validate_image_source_rejects_unsupported_format(self, tmp_path):
        """Test validate_image_source rejects unsupported formats."""
        svg_file = tmp_path / "diagram.svg"
        svg_file.write_bytes(b"<svg></svg>")

        with pytest.raises(ValueError) as exc_info:
            validate_image_source(str(svg_file))

        assert "Unsupported image format" in str(exc_info.value)
        assert ".svg" in str(exc_info.value)
        for ext in IMAGE_EXTENSIONS:
            assert ext in str(exc_info.value)

    def test_validate_image_source_accepts_jpg(self, tmp_path):
        """Test validate_image_source accepts .jpg files."""
        jpg_file = tmp_path / "test.jpg"
        jpg_file.write_bytes(b"JPEG_DUMMY_DATA")
        validate_image_source(str(jpg_file))

    def test_validate_image_source_accepts_jpeg(self, tmp_path):
        """Test validate_image_source accepts .jpeg files."""
        jpeg_file = tmp_path / "test.jpeg"
        jpeg_file.write_bytes(b"JPEG_DUMMY_DATA")
        validate_image_source(str(jpeg_file))

    def test_validate_image_source_accepts_png(self, tmp_path):
        """Test validate_image_source accepts .png files."""
        png_file = tmp_path / "test.png"
        png_file.write_bytes(b"PNG_DUMMY_DATA")
        validate_image_source(str(png_file))


class TestValidateVideoSource:
    """Unit Tests: validate_video_source() for video files."""

    def test_validate_video_source_accepts_valid_video_file(self, tmp_path):
        """Test validate_video_source accepts valid video files."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"MP4_DUMMY_DATA")

        # Should not raise
        validate_video_source(str(video_file))

    def test_validate_video_source_rejects_nonexistent_file(self, tmp_path):
        """Test validate_video_source rejects non-existent files."""
        nonexistent = tmp_path / "does_not_exist.mp4"

        with pytest.raises(FileNotFoundError) as exc_info:
            validate_video_source(str(nonexistent))

        assert "File not found" in str(exc_info.value)

    def test_validate_video_source_rejects_file_over_8mb(self, tmp_path):
        """Test validate_video_source rejects files > 8MB."""
        large_file = tmp_path / "large.mp4"
        # Create a file larger than 8MB
        large_file.write_bytes(b"x" * (MAX_VIDEO_SIZE + 1))

        with pytest.raises(ValueError) as exc_info:
            validate_video_source(str(large_file))

        assert "exceeds 8MB limit" in str(exc_info.value)

    def test_validate_video_source_accepts_exactly_8mb(self, tmp_path):
        """Test validate_video_source accepts exactly 8MB file."""
        # Create a file exactly 8MB
        video_file = tmp_path / "exactly_8mb.mp4"
        video_file.write_bytes(b"x" * MAX_VIDEO_SIZE)

        # Should not raise
        validate_video_source(str(video_file))

    def test_validate_video_source_rejects_unsupported_format(self, tmp_path):
        """Test validate_video_source rejects unsupported formats."""
        flv_file = tmp_path / "video.flv"
        flv_file.write_bytes(b"FLV_DUMMY_DATA")

        with pytest.raises(ValueError) as exc_info:
            validate_video_source(str(flv_file))

        assert "Unsupported video format" in str(exc_info.value)
        assert ".flv" in str(exc_info.value)

    def test_validate_video_source_accepts_all_supported_formats(self, tmp_path):
        """Test validate_video_source accepts all supported video formats."""
        for ext in VIDEO_EXTENSIONS:
            video_file = tmp_path / f"test{ext}"
            video_file.write_bytes(b"VIDEO_DUMMY_DATA")
            validate_video_source(str(video_file))


class TestEncodeImageToBase64:
    """Unit Tests: encode_image_to_base64() returns correct data URI format."""

    def test_encode_png_to_base64(self, tmp_path):
        """Test encode_image_to_base64 for PNG files."""
        image_file = tmp_path / "test.png"
        # Create a small PNG with valid header
        # PNG header: 137 80 78 71 13 10 26 10
        png_data = b'\x89PNG\r\n\x1a\n' + b'x' * 100
        image_file.write_bytes(png_data)

        result = encode_image_to_base64(str(image_file))

        # Should be a data URI with correct MIME type
        assert result.startswith("data:image/png;base64,")
        # Should be valid base64 after the prefix
        encoded = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded)
        assert decoded == png_data

    def test_encode_jpg_to_base64(self, tmp_path):
        """Test encode_image_to_base64 for JPEG files."""
        image_file = tmp_path / "test.jpg"
        # JPEG header: FF D8 FF
        jpg_data = b'\xff\xd8\xff' + b'x' * 100
        image_file.write_bytes(jpg_data)

        result = encode_image_to_base64(str(image_file))

        # Should be a data URI with correct MIME type
        assert result.startswith("data:image/jpeg;base64,")

    def test_encode_jpeg_to_base64(self, tmp_path):
        """Test encode_image_to_base64 for .jpeg extension."""
        image_file = tmp_path / "test.jpeg"
        jpg_data = b'\xff\xd8\xff' + b'x' * 100
        image_file.write_bytes(jpg_data)

        result = encode_image_to_base64(str(image_file))

        assert result.startswith("data:image/jpeg;base64,")

    def test_encode_returns_valid_base64(self, tmp_path):
        """Test encode_image_to_base64 returns valid base64."""
        image_file = tmp_path / "test.png"
        original_data = b'\x89PNG\r\n\x1a\n' + b'test data'
        image_file.write_bytes(original_data)

        result = encode_image_to_base64(str(image_file))

        # Decode and verify
        encoded_part = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == original_data


class TestEncodeVideoToBase64:
    """Unit Tests: encode_video_to_base64() returns correct data URI format."""

    def test_encode_mp4_to_base64(self, tmp_path):
        """Test encode_video_to_base64 for MP4 files."""
        video_file = tmp_path / "test.mp4"
        # MP4 header typically starts with ftyp box
        mp4_data = b'\x00\x00\x00\x20\x66\x74\x79\x70' + b'x' * 100
        video_file.write_bytes(mp4_data)

        result = encode_video_to_base64(str(video_file))

        # Should be a data URI with correct MIME type
        assert result.startswith("data:video/mp4;base64,")
        # Should be valid base64 after the prefix
        encoded = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded)
        assert decoded == mp4_data

    def test_encode_mov_to_base64(self, tmp_path):
        """Test encode_video_to_base64 for MOV files."""
        video_file = tmp_path / "test.mov"
        mov_data = b'x' * 100
        video_file.write_bytes(mov_data)

        result = encode_video_to_base64(str(video_file))

        assert result.startswith("data:video/quicktime;base64,")

    def test_encode_returns_valid_base64(self, tmp_path):
        """Test encode_video_to_base64 returns valid base64."""
        video_file = tmp_path / "test.mp4"
        original_data = b'\x00\x00\x00\x20\x66\x74\x79\x70' + b'test data'
        video_file.write_bytes(original_data)

        result = encode_video_to_base64(str(video_file))

        # Decode and verify
        encoded_part = result.split(",", 1)[1]
        decoded = base64.b64decode(encoded_part)
        assert decoded == original_data


class TestProcessImageSource:
    """Unit Tests: process_image_source() for URLs vs local files."""

    def test_process_image_source_with_url(self):
        """Test process_image_source returns URL directly for URLs."""
        url = "https://example.com/image.png"
        result = process_image_source(url)
        assert result == url

    def test_process_image_source_with_local_file(self, tmp_path):
        """Test process_image_source returns base64 data URI for local files."""
        image_file = tmp_path / "test.png"
        png_data = b'\x89PNG\r\n\x1a\n' + b'test'
        image_file.write_bytes(png_data)

        result = process_image_source(str(image_file))

        # Should return base64 data URI
        assert result.startswith("data:image/png;base64,")


class TestProcessVideoSource:
    """Unit Tests: process_video_source() for URLs vs local files."""

    def test_process_video_source_with_url(self):
        """Test process_video_source returns URL directly for URLs."""
        url = "https://example.com/video.mp4"
        result = process_video_source(url)
        assert result == url

    def test_process_video_source_with_local_file(self, tmp_path):
        """Test process_video_source returns base64 data URI for local files."""
        video_file = tmp_path / "test.mp4"
        mp4_data = b'\x00\x00\x00\x20\x66\x74\x79\x70' + b'test'
        video_file.write_bytes(mp4_data)

        result = process_video_source(str(video_file))

        # Should return base64 data URI
        assert result.startswith("data:video/mp4;base64,")


class TestSpecialCharactersInPath:
    """Edge Case Tests: Image with special characters in path."""

    def test_image_with_spaces_in_path(self, tmp_path):
        """Test image file with spaces in path."""
        image_file = tmp_path / "my image.png"
        image_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'test')
        validate_image_source(str(image_file))

    def test_image_with_unicode_in_path(self, tmp_path):
        """Test image file with unicode characters in path."""
        image_file = tmp_path / "imagen.png"
        image_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'test')
        validate_image_source(str(image_file))
