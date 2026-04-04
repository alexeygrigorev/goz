"""Unit tests for ThinkingIndicator widget (Issue 25)."""
import pytest

from goz.tui.widgets.thinking import ThinkingIndicator


class TestThinkingIndicatorExists:
    """Unit Tests: ThinkingIndicator exists and can be imported."""

    def test_thinking_indicator_class_exists(self):
        """Test ThinkingIndicator class can be imported."""
        from goz.tui.widgets.thinking import ThinkingIndicator  # noqa: F401
        assert ThinkingIndicator is not None


class TestThinkingIndicatorInit:
    """Unit Tests: ThinkingIndicator initialization."""

    def test_thinking_indicator_init_default(self):
        """Test ThinkingIndicator initializes with defaults."""
        indicator = ThinkingIndicator()
        assert indicator is not None

    def test_thinking_indicator_has_state_attribute(self):
        """Test ThinkingIndicator has state attribute."""
        indicator = ThinkingIndicator()
        assert hasattr(indicator, "state")
        assert indicator.state == "idle"

    def test_thinking_indicator_has_tool_name_attribute(self):
        """Test ThinkingIndicator has tool_name attribute."""
        indicator = ThinkingIndicator()
        assert hasattr(indicator, "tool_name")
        assert indicator.tool_name is None

    def test_thinking_indicator_has_animation_frame_attribute(self):
        """Test ThinkingIndicator has animation_frame attribute."""
        indicator = ThinkingIndicator()
        assert hasattr(indicator, "animation_frame")
        assert indicator.animation_frame == 0

    def test_thinking_indicator_init_with_id(self):
        """Test ThinkingIndicator can be initialized with id."""
        indicator = ThinkingIndicator(id="test-thinking")
        assert indicator.id == "test-thinking"


class TestThinkingIndicatorStates:
    """Unit Tests: ThinkingIndicator state management."""

    def test_set_state_to_thinking(self):
        """Test setting state to 'thinking'."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        assert indicator.state == "thinking"

    def test_set_state_to_planning(self):
        """Test setting state to 'planning'."""
        indicator = ThinkingIndicator()
        indicator.set_state("planning")
        assert indicator.state == "planning"

    def test_set_state_to_executing(self):
        """Test setting state to 'executing'."""
        indicator = ThinkingIndicator()
        indicator.set_state("executing")
        assert indicator.state == "executing"

    def test_set_state_to_error(self):
        """Test setting state to 'error'."""
        indicator = ThinkingIndicator()
        indicator.set_state("error")
        assert indicator.state == "error"

    def test_set_state_to_idle(self):
        """Test setting state to 'idle'."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        indicator.set_state("idle")
        assert indicator.state == "idle"

    def test_set_state_with_tool_name(self):
        """Test setting state with tool_name parameter."""
        indicator = ThinkingIndicator()
        indicator.set_state("executing", tool_name="view_file")
        assert indicator.tool_name == "view_file"

    def test_set_state_thinking_visible(self):
        """Test widget is visible when state is 'thinking'."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        assert indicator.visible is True

    def test_set_state_idle_not_visible(self):
        """Test widget is not visible when state is 'idle'."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        indicator.set_state("idle")
        assert indicator.visible is False


class TestThinkingIndicatorAnimation:
    """Unit Tests: ThinkingIndicator animation."""

    def test_animation_frame_increments(self):
        """Test animation_frame increments on animate call."""
        indicator = ThinkingIndicator()
        initial_frame = indicator.animation_frame
        indicator.animate()
        assert indicator.animation_frame != initial_frame

    def test_animation_frame_wraps_at_4(self):
        """Test animation_frame wraps at 4 (frames 0-3)."""
        indicator = ThinkingIndicator()
        indicator.animation_frame = 3
        indicator.animate()
        assert indicator.animation_frame == 0

    def test_animate_updates_content(self):
        """Test animate calls update_content."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        # Should not raise, and should update display
        indicator.animate()
        # Check that render produces expected output
        output = indicator.render()
        assert output is not None


class TestThinkingIndicatorRender:
    """Unit Tests: ThinkingIndicator rendering."""

    def test_render_thinking_state(self):
        """Test render output for 'thinking' state."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        output = indicator.render()
        assert "Thinking" in str(output)

    def test_render_planning_state(self):
        """Test render output for 'planning' state."""
        indicator = ThinkingIndicator()
        indicator.set_state("planning")
        output = indicator.render()
        assert "Planning" in str(output)

    def test_render_executing_state(self):
        """Test render output for 'executing' state."""
        indicator = ThinkingIndicator()
        indicator.set_state("executing", tool_name="view_file")
        output = indicator.render()
        assert "view_file" in str(output)

    def test_render_error_state(self):
        """Test render output for 'error' state."""
        indicator = ThinkingIndicator()
        indicator.set_state("error")
        output = indicator.render()
        assert "Error" in str(output)

    def test_render_idle_state_returns_empty(self):
        """Test render returns empty string for 'idle' state."""
        indicator = ThinkingIndicator()
        indicator.set_state("idle")
        output = indicator.render()
        assert output == ""


class TestThinkingIndicatorSpinnerFrames:
    """Unit Tests: ThinkingIndicator spinner frames."""

    def test_spinner_frames_exist(self):
        """Test ThinkingIndicator has spinner frames defined."""
        indicator = ThinkingIndicator()
        assert hasattr(indicator, "SPINNER_FRAMES")
        assert len(indicator.SPINNER_FRAMES) == 4

    def test_spinner_frames_are_correct(self):
        """Test spinner frames match expected pattern."""
        indicator = ThinkingIndicator()
        # Expected frames: |, / -, \
        expected = ["|", "/", "-", "\\"]
        assert indicator.SPINNER_FRAMES == expected


class TestThinkingIndicatorStyles:
    """Unit Tests: ThinkingIndicator styling for different states."""

    def test_thinking_style_has_dim(self):
        """Test 'thinking' state output includes dim styling."""
        indicator = ThinkingIndicator()
        indicator.set_state("thinking")
        output = indicator.render()
        assert "dim" in str(output).lower()

    def test_planning_style_has_cyan(self):
        """Test 'planning' state output includes cyan styling."""
        indicator = ThinkingIndicator()
        indicator.set_state("planning")
        output = indicator.render()
        assert "cyan" in str(output).lower()

    def test_executing_style_has_yellow(self):
        """Test 'executing' state output includes yellow styling."""
        indicator = ThinkingIndicator()
        indicator.set_state("executing")
        output = indicator.render()
        assert "yellow" in str(output).lower()

    def test_error_style_has_red(self):
        """Test 'error' state output includes red styling."""
        indicator = ThinkingIndicator()
        indicator.set_state("error")
        output = indicator.render()
        assert "red" in str(output).lower()


class TestThinkingIndicatorSuccessState:
    """Unit Tests: ThinkingIndicator success state (green)."""

    def test_set_state_to_success(self):
        """Test setting state to 'success'."""
        indicator = ThinkingIndicator()
        indicator.set_state("success")
        assert indicator.state == "success"

    def test_success_style_has_green(self):
        """Test 'success' state output includes green styling."""
        indicator = ThinkingIndicator()
        indicator.set_state("success")
        output = indicator.render()
        assert "green" in str(output).lower()
