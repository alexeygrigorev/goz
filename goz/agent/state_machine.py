"""Chat State Machine for managing conversation states.

This module provides the ChatStateMachine class for managing the state
transitions during interactive chat sessions with the agent.

Acceptance Criteria (Issue 16):
1. ChatStateMachine class exists
2. State enum has: IDLE, THINKING, PLANNING_TOOLS, EXECUTING_TOOLS, RESPONDING
3. current_state property returns current state
4. transition() validates and executes state changes
5. Valid transitions match the state diagram
6. Invalid transitions raise StateTransitionError
7. State change events can be subscribed to
"""
import logging
from enum import Enum
from typing import Callable


logger = logging.getLogger(__name__)


class StateTransitionError(Exception):
    """Exception raised when an invalid state transition is attempted.

    Attributes:
        message: Human-readable error message

    Acceptance Criteria 10: StateTransitionError exception class
    """

    def __init__(self, message: str) -> None:
        """Initialize StateTransitionError.

        Args:
            message: Error message describing the invalid transition
        """
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class State(Enum):
    """States for the chat conversation state machine.

    Acceptance Criteria 2: State enum has: IDLE, THINKING, PLANNING_TOOLS, EXECUTING_TOOLS, RESPONDING

    State Flow:
    - IDLE: Ready for user input
    - THINKING: Processing user request, waiting for API response
    - PLANNING_TOOLS: API returned tool_use blocks, preparing to execute
    - EXECUTING_TOOLS: Currently executing tool(s)
    - RESPONDING: Streaming final response to user
    """

    IDLE = "idle"
    THINKING = "thinking"
    PLANNING_TOOLS = "planning_tools"
    EXECUTING_TOOLS = "executing_tools"
    RESPONDING = "responding"


class ChatStateMachine:
    """State machine for managing chat conversation states.

    This class enforces valid state transitions during interactive chat
    sessions. It also allows subscribers to be notified of state changes.

    Acceptance Criteria 1: ChatStateMachine class exists
    Acceptance Criteria 3: current_state property returns current state
    Acceptance Criteria 4: transition() validates and executes state changes
    Acceptance Criteria 7: State change events can be subscribed to

    Valid transitions:
    - IDLE -> THINKING
    - THINKING -> PLANNING_TOOLS
    - THINKING -> RESPONDING (no tools needed)
    - PLANNING_TOOLS -> EXECUTING_TOOLS
    - EXECUTING_TOOLS -> THINKING (more API calls needed)
    - EXECUTING_TOOLS -> RESPONDING (final response)
    - RESPONDING -> IDLE
    """

    # Valid state transitions as per the state diagram
    # Format: from_state -> set of valid to_states
    _VALID_TRANSITIONS: dict[State, set[State]] = {
        State.IDLE: {State.THINKING},
        State.THINKING: {State.PLANNING_TOOLS, State.RESPONDING},
        State.PLANNING_TOOLS: {State.EXECUTING_TOOLS},
        State.EXECUTING_TOOLS: {State.THINKING, State.RESPONDING},
        State.RESPONDING: {State.IDLE},
    }

    def __init__(self) -> None:
        """Initialize ChatStateMachine.

        The machine starts in the IDLE state.

        Acceptance Criteria 1: ChatStateMachine class exists
        """
        self._state = State.IDLE
        self._subscribers: list[Callable[[State, State], None]] = []

    @property
    def current_state(self) -> State:
        """Get the current state.

        Returns:
            The current State enum value

        Acceptance Criteria 3: current_state property returns current state
        """
        return self._state

    @current_state.setter
    def current_state(self, value: State) -> None:
        """Set the current state (for testing purposes).

        Args:
            value: The new state
        """
        self._state = value

    def can_transition(self, from_state: State, to_state: State) -> bool:
        """Check if a transition is valid.

        Args:
            from_state: The source state
            to_state: The destination state

        Returns:
            True if the transition is valid, False otherwise

        Acceptance Criteria 5: Valid transitions match the state diagram
        """
        if from_state not in self._VALID_TRANSITIONS:
            return False

        return to_state in self._VALID_TRANSITIONS[from_state]

    def transition(self, to_state: State) -> bool:
        """Transition to a new state.

        This method validates the transition and updates the current state.
        If the transition is invalid, a StateTransitionError is raised.
        All subscribers are notified of successful state changes.

        Args:
            to_state: The state to transition to

        Returns:
            True if the transition succeeded

        Raises:
            StateTransitionError: If the transition is invalid

        Acceptance Criteria 4: transition() validates and executes state changes
        Acceptance Criteria 6: Invalid transitions raise StateTransitionError
        """
        from_state = self._state

        if not self.can_transition(from_state, to_state):
            raise StateTransitionError(
                f"Invalid transition: {from_state.value} -> {to_state.value}"
            )

        # Perform the transition
        self._state = to_state

        # Notify subscribers
        self._notify_subscribers(from_state, to_state)

        return True

    def subscribe(self, callback: Callable[[State, State], None]) -> None:
        """Subscribe to state change events.

        The callback will be invoked with (from_state, to_state) arguments
        whenever a valid state transition occurs.

        Args:
            callback: Function to call on state changes

        Acceptance Criteria 7: State change events can be subscribed to
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[State, State], None]) -> None:
        """Unsubscribe from state change events.

        Args:
            callback: The callback to remove
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _notify_subscribers(self, from_state: State, to_state: State) -> None:
        """Notify all subscribers of a state change.

        Args:
            from_state: The previous state
            to_state: The new state
        """
        for callback in self._subscribers:
            try:
                callback(from_state, to_state)
            except Exception as e:
                logger.error(f"Error notifying state change subscriber: {e}")
