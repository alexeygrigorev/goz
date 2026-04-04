"""Unit tests for ChatStateMachine (Issue 16).

TDD: Tests written FIRST, expected to FAIL initially.
"""
import pytest

from goz.agent.state_machine import (
    ChatStateMachine,
    State,
    StateTransitionError,
)


class TestStateEnum:
    """Tests for State enum (Acceptance Criteria 2)."""

    def test_state_enum_has_all_states(self):
        """Test State enum has all required states (Acceptance Criteria 2)."""
        # Check all required states exist
        assert hasattr(State, 'IDLE')
        assert hasattr(State, 'THINKING')
        assert hasattr(State, 'PLANNING_TOOLS')
        assert hasattr(State, 'EXECUTING_TOOLS')
        assert hasattr(State, 'RESPONDING')

        # Check enum values
        assert State.IDLE.value == "idle"
        assert State.THINKING.value == "thinking"
        assert State.PLANNING_TOOLS.value == "planning_tools"
        assert State.EXECUTING_TOOLS.value == "executing_tools"
        assert State.RESPONDING.value == "responding"

    def test_state_enum_string_representation(self):
        """Test State enum string representation."""
        assert str(State.IDLE) == "State.idle" or State.IDLE.value == "idle"


class TestStateTransitionError:
    """Tests for StateTransitionError exception (Acceptance Criteria 10)."""

    def test_state_transition_error_exists(self):
        """Test StateTransitionError exception class exists."""
        error = StateTransitionError("Invalid transition")

        assert isinstance(error, Exception)
        assert "Invalid transition" in str(error)

    def test_state_transition_error_message(self):
        """Test StateTransitionError stores message."""
        error = StateTransitionError("Cannot go from IDLE to EXECUTING_TOOLS")

        assert str(error) == "Cannot go from IDLE to EXECUTING_TOOLS"
        assert error.message == "Cannot go from IDLE to EXECUTING_TOOLS"


class TestChatStateMachineClass:
    """Tests for ChatStateMachine class (Acceptance Criteria 1)."""

    def test_state_machine_class_exists(self):
        """Test ChatStateMachine class exists (Acceptance Criteria 1)."""
        machine = ChatStateMachine()

        assert machine is not None
        assert isinstance(machine, ChatStateMachine)

    def test_state_machine_initializes_in_idle_state(self):
        """Test ChatStateMachine initializes in IDLE state."""
        machine = ChatStateMachine()

        assert machine.current_state == State.IDLE


class TestCurrentState:
    """Tests for current_state property (Acceptance Criteria 3)."""

    def test_current_state_property_exists(self):
        """Test current_state property exists (Acceptance Criteria 3)."""
        machine = ChatStateMachine()

        assert hasattr(machine, 'current_state')
        assert machine.current_state == State.IDLE

    def test_current_state_returns_state_enum(self):
        """Test current_state returns State enum."""
        machine = ChatStateMachine()

        assert isinstance(machine.current_state, State)


class TestCanTransition:
    """Tests for can_transition method (Acceptance Criteria 5)."""

    def test_can_transition_idle_to_thinking(self):
        """Test can_transition from IDLE to THINKING (valid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.IDLE, State.THINKING) is True

    def test_can_transition_thinking_to_planning_tools(self):
        """Test can_transition from THINKING to PLANNING_TOOLS (valid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.THINKING, State.PLANNING_TOOLS) is True

    def test_can_transition_thinking_to_responding(self):
        """Test can_transition from THINKING to RESPONDING (valid, no tools)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.THINKING, State.RESPONDING) is True

    def test_can_transition_planning_tools_to_executing_tools(self):
        """Test can_transition from PLANNING_TOOLS to EXECUTING_TOOLS (valid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.PLANNING_TOOLS, State.EXECUTING_TOOLS) is True

    def test_can_transition_executing_tools_to_thinking(self):
        """Test can_transition from EXECUTING_TOOLS to THINKING (valid, more API calls)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.EXECUTING_TOOLS, State.THINKING) is True

    def test_can_transition_executing_tools_to_responding(self):
        """Test can_transition from EXECUTING_TOOLS to RESPONDING (valid, final response)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.EXECUTING_TOOLS, State.RESPONDING) is True

    def test_can_transition_responding_to_idle(self):
        """Test can_transition from RESPONDING to IDLE (valid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.RESPONDING, State.IDLE) is True

    def test_can_transition_invalid_idle_to_executing_tools(self):
        """Test can_transition from IDLE to EXECUTING_TOOLS (invalid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.IDLE, State.EXECUTING_TOOLS) is False

    def test_can_transition_invalid_idle_to_planning_tools(self):
        """Test can_transition from IDLE to PLANNING_TOOLS (invalid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.IDLE, State.PLANNING_TOOLS) is False

    def test_can_transition_invalid_thinking_to_idle(self):
        """Test can_transition from THINKING to IDLE (invalid)."""
        machine = ChatStateMachine()

        assert machine.can_transition(State.THINKING, State.IDLE) is False


class TestTransition:
    """Tests for transition method (Acceptance Criteria 4, 6)."""

    def test_transition_idle_to_thinking_succeeds(self):
        """Test valid transition IDLE -> THINKING succeeds."""
        machine = ChatStateMachine()

        machine.transition(State.THINKING)

        assert machine.current_state == State.THINKING

    def test_transition_thinking_to_planning_tools_succeeds(self):
        """Test valid transition THINKING -> PLANNING_TOOLS succeeds."""
        machine = ChatStateMachine()
        machine.current_state = State.THINKING

        machine.transition(State.PLANNING_TOOLS)

        assert machine.current_state == State.PLANNING_TOOLS

    def test_transition_thinking_to_responding_succeeds(self):
        """Test valid transition THINKING -> RESPONDING succeeds (no tools)."""
        machine = ChatStateMachine()
        machine.current_state = State.THINKING

        machine.transition(State.RESPONDING)

        assert machine.current_state == State.RESPONDING

    def test_transition_planning_tools_to_executing_tools_succeeds(self):
        """Test valid transition PLANNING_TOOLS -> EXECUTING_TOOLS succeeds."""
        machine = ChatStateMachine()
        machine.current_state = State.PLANNING_TOOLS

        machine.transition(State.EXECUTING_TOOLS)

        assert machine.current_state == State.EXECUTING_TOOLS

    def test_transition_executing_tools_to_thinking_succeeds(self):
        """Test valid transition EXECUTING_TOOLS -> THINKING succeeds."""
        machine = ChatStateMachine()
        machine.current_state = State.EXECUTING_TOOLS

        machine.transition(State.THINKING)

        assert machine.current_state == State.THINKING

    def test_transition_executing_tools_to_responding_succeeds(self):
        """Test valid transition EXECUTING_TOOLS -> RESPONDING succeeds."""
        machine = ChatStateMachine()
        machine.current_state = State.EXECUTING_TOOLS

        machine.transition(State.RESPONDING)

        assert machine.current_state == State.RESPONDING

    def test_transition_responding_to_idle_succeeds(self):
        """Test valid transition RESPONDING -> IDLE succeeds."""
        machine = ChatStateMachine()
        machine.current_state = State.RESPONDING

        machine.transition(State.IDLE)

        assert machine.current_state == State.IDLE

    def test_transition_invalid_idle_to_executing_tools_raises_error(self):
        """Test invalid transition IDLE -> EXECUTING_TOOLS raises StateTransitionError (Acceptance Criteria 6)."""
        machine = ChatStateMachine()

        with pytest.raises(StateTransitionError) as exc_info:
            machine.transition(State.EXECUTING_TOOLS)

        assert "Invalid transition" in str(exc_info.value)
        assert "idle" in str(exc_info.value)
        assert "executing_tools" in str(exc_info.value)

    def test_transition_invalid_thinking_to_idle_raises_error(self):
        """Test invalid transition THINKING -> IDLE raises StateTransitionError."""
        machine = ChatStateMachine()
        machine.current_state = State.THINKING

        with pytest.raises(StateTransitionError) as exc_info:
            machine.transition(State.IDLE)

        assert "Invalid transition" in str(exc_info.value)

    def test_transition_returns_true_on_success(self):
        """Test transition returns True on successful transition (Acceptance Criteria 4)."""
        machine = ChatStateMachine()

        result = machine.transition(State.THINKING)

        assert result is True


class TestStateChangeSubscription:
    """Tests for state change event subscription (Acceptance Criteria 7)."""

    def test_state_change_events_can_be_subscribed(self):
        """Test state change events can be subscribed to (Acceptance Criteria 7)."""
        machine = ChatStateMachine()

        # Track state changes
        changes = []

        def on_state_change(from_state: State, to_state: State):
            changes.append((from_state, to_state))

        # Subscribe
        machine.subscribe(on_state_change)

        # Trigger transition
        machine.transition(State.THINKING)

        assert len(changes) == 1
        assert changes[0] == (State.IDLE, State.THINKING)

    def test_multiple_subscribers_get_notified(self):
        """Test multiple subscribers get notified of state changes."""
        machine = ChatStateMachine()

        changes1 = []
        changes2 = []

        def subscriber1(from_state: State, to_state: State):
            changes1.append((from_state, to_state))

        def subscriber2(from_state: State, to_state: State):
            changes2.append((from_state, to_state))

        machine.subscribe(subscriber1)
        machine.subscribe(subscriber2)

        machine.transition(State.THINKING)

        assert len(changes1) == 1
        assert len(changes2) == 1
        assert changes1[0] == (State.IDLE, State.THINKING)
        assert changes2[0] == (State.IDLE, State.THINKING)

    def test_invalid_transition_does_not_notify_subscribers(self):
        """Test subscribers are not notified on invalid transition."""
        machine = ChatStateMachine()

        changes = []

        def on_state_change(from_state: State, to_state: State):
            changes.append((from_state, to_state))

        machine.subscribe(on_state_change)

        try:
            machine.transition(State.EXECUTING_TOOLS)
        except StateTransitionError:
            pass

        assert len(changes) == 0

    def test_unsubscribe_stops_notifications(self):
        """Test unsubscribe stops notifications."""
        machine = ChatStateMachine()

        changes = []

        def on_state_change(from_state: State, to_state: State):
            changes.append((from_state, to_state))

        machine.subscribe(on_state_change)
        machine.unsubscribe(on_state_change)

        machine.transition(State.THINKING)

        assert len(changes) == 0


class TestValidTransitionsMatchDiagram:
    """Tests that valid transitions match the state diagram (Acceptance Criteria 5)."""

    def test_all_valid_transitions_from_spec(self):
        """Test all valid transitions from the specification diagram work.

        Valid transitions:
        - IDLE -> THINKING
        - THINKING -> PLANNING_TOOLS
        - THINKING -> RESPONDING (no tools)
        - PLANNING_TOOLS -> EXECUTING_TOOLS
        - EXECUTING_TOOLS -> THINKING (more API calls needed)
        - EXECUTING_TOOLS -> RESPONDING (final response)
        - RESPONDING -> IDLE
        """
        machine = ChatStateMachine()

        # All valid transitions should return True for can_transition
        valid_transitions = [
            (State.IDLE, State.THINKING),
            (State.THINKING, State.PLANNING_TOOLS),
            (State.THINKING, State.RESPONDING),
            (State.PLANNING_TOOLS, State.EXECUTING_TOOLS),
            (State.EXECUTING_TOOLS, State.THINKING),
            (State.EXECUTING_TOOLS, State.RESPONDING),
            (State.RESPONDING, State.IDLE),
        ]

        for from_state, to_state in valid_transitions:
            assert machine.can_transition(from_state, to_state) is True, \
                f"Expected {from_state} -> {to_state} to be valid"

    def test_all_invalid_transitions_from_spec_fail(self):
        """Test that invalid transitions fail.

        Invalid transitions (any not in the valid list):
        - IDLE -> anything except THINKING
        - THINKING -> IDLE, EXECUTING_TOOLS
        - PLANNING_TOOLS -> anything except EXECUTING_TOOLS
        - EXECUTING_TOOLS -> IDLE, PLANNING_TOOLS
        - RESPONDING -> anything except IDLE
        """
        machine = ChatStateMachine()

        # Some example invalid transitions
        invalid_transitions = [
            (State.IDLE, State.PLANNING_TOOLS),
            (State.IDLE, State.EXECUTING_TOOLS),
            (State.IDLE, State.RESPONDING),
            (State.THINKING, State.IDLE),
            (State.THINKING, State.EXECUTING_TOOLS),
            (State.PLANNING_TOOLS, State.THINKING),
            (State.PLANNING_TOOLS, State.IDLE),
            (State.EXECUTING_TOOLS, State.IDLE),
            (State.EXECUTING_TOOLS, State.PLANNING_TOOLS),
            (State.RESPONDING, State.THINKING),
            (State.RESPONDING, State.PLANNING_TOOLS),
            (State.RESPONDING, State.EXECUTING_TOOLS),
        ]

        for from_state, to_state in invalid_transitions:
            assert machine.can_transition(from_state, to_state) is False, \
                f"Expected {from_state} -> {to_state} to be invalid"
