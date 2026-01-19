"""
Unit tests for HOT (Higher-Order Theory) belief revision loop logic.

Tests the metacognitive belief revision mechanism that re-runs earlier
modules when confidence is too low, implementing causal coupling for HOT.
"""

import pytest
from dataclasses import dataclass


@dataclass
class BeliefRevisionConfig:
    """Configuration for belief revision."""
    threshold: float = 0.4
    max_iterations: int = 2


class BeliefRevisionState:
    """State tracking for belief revision loop."""

    def __init__(self, config: BeliefRevisionConfig | None = None):
        self.config = config or BeliefRevisionConfig()
        self.revision_count = 0
        self.confidence_history: list[float] = []
        self.revision_events: list[dict] = []

    def should_revise(self, confidence: float) -> bool:
        """Check if belief revision should be triggered."""
        return (
            confidence < self.config.threshold
            and self.revision_count < self.config.max_iterations
        )

    def record_revision(self, confidence: float, uncertainties: list[str]) -> dict:
        """Record a belief revision event."""
        self.revision_count += 1
        self.confidence_history.append(confidence)

        event = {
            "iteration": self.revision_count,
            "trigger_confidence": confidence,
            "threshold": self.config.threshold,
            "uncertainties": uncertainties,
            "action": "re-running modules to reduce uncertainty",
        }
        self.revision_events.append(event)
        return event

    def check_convergence(self, new_confidence: float, previous_confidence: float) -> bool:
        """Check if confidence has converged (not improving)."""
        return new_confidence <= previous_confidence


class TestShouldRevise:
    """Tests for the should_revise decision logic."""

    def test_triggers_when_below_threshold(self):
        """Revision should trigger when confidence < threshold."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4, max_iterations=2))

        assert state.should_revise(0.35) is True
        assert state.should_revise(0.39) is True
        assert state.should_revise(0.1) is True

    def test_does_not_trigger_when_at_threshold(self):
        """Revision should not trigger when confidence == threshold."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4, max_iterations=2))

        assert state.should_revise(0.4) is False

    def test_does_not_trigger_when_above_threshold(self):
        """Revision should not trigger when confidence > threshold."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4, max_iterations=2))

        assert state.should_revise(0.5) is False
        assert state.should_revise(0.8) is False
        assert state.should_revise(1.0) is False

    def test_stops_at_max_iterations(self):
        """Revision should stop after max iterations reached."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4, max_iterations=2))

        # First two iterations should be allowed
        assert state.should_revise(0.3) is True
        state.revision_count = 1
        assert state.should_revise(0.3) is True
        state.revision_count = 2

        # Third should be blocked
        assert state.should_revise(0.3) is False

    def test_single_iteration_limit(self):
        """When max_iterations=1, only one revision allowed."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.5, max_iterations=1))

        assert state.should_revise(0.3) is True
        state.revision_count = 1
        assert state.should_revise(0.3) is False

    def test_zero_iterations_limit(self):
        """When max_iterations=0, no revisions allowed."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.5, max_iterations=0))

        assert state.should_revise(0.1) is False

    def test_very_low_threshold(self):
        """Very low threshold should rarely trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.1, max_iterations=2))

        assert state.should_revise(0.2) is False
        assert state.should_revise(0.15) is False
        assert state.should_revise(0.05) is True

    def test_very_high_threshold(self):
        """Very high threshold should frequently trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.9, max_iterations=2))

        assert state.should_revise(0.5) is True
        assert state.should_revise(0.85) is True
        assert state.should_revise(0.91) is False


class TestRecordRevision:
    """Tests for revision event recording."""

    def test_records_correct_iteration_number(self):
        """Iteration number should increment correctly."""
        state = BeliefRevisionState()

        event1 = state.record_revision(0.3, ["uncertainty1"])
        event2 = state.record_revision(0.35, ["uncertainty2"])

        assert event1["iteration"] == 1
        assert event2["iteration"] == 2

    def test_records_trigger_confidence(self):
        """Trigger confidence should be recorded."""
        state = BeliefRevisionState()

        event = state.record_revision(0.35, [])

        assert event["trigger_confidence"] == 0.35

    def test_records_threshold(self):
        """Threshold should be recorded."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.5))

        event = state.record_revision(0.3, [])

        assert event["threshold"] == 0.5

    def test_records_uncertainties(self):
        """Uncertainties from metacog should be recorded."""
        state = BeliefRevisionState()

        uncertainties = ["Is this a question?", "Unclear intent", "Ambiguous reference"]
        event = state.record_revision(0.3, uncertainties)

        assert event["uncertainties"] == uncertainties

    def test_records_action(self):
        """Action description should be recorded."""
        state = BeliefRevisionState()

        event = state.record_revision(0.3, [])

        assert "re-running modules" in event["action"]

    def test_updates_confidence_history(self):
        """Confidence history should be tracked."""
        state = BeliefRevisionState()

        state.record_revision(0.3, [])
        state.record_revision(0.35, [])
        state.record_revision(0.38, [])

        assert state.confidence_history == [0.3, 0.35, 0.38]

    def test_stores_all_events(self):
        """All revision events should be stored."""
        state = BeliefRevisionState()

        state.record_revision(0.3, ["u1"])
        state.record_revision(0.35, ["u2"])

        assert len(state.revision_events) == 2
        assert state.revision_events[0]["trigger_confidence"] == 0.3
        assert state.revision_events[1]["trigger_confidence"] == 0.35


class TestConvergenceDetection:
    """Tests for convergence detection."""

    def test_converged_when_confidence_decreases(self):
        """Should detect convergence when confidence decreases."""
        state = BeliefRevisionState()

        assert state.check_convergence(new_confidence=0.3, previous_confidence=0.35) is True

    def test_converged_when_confidence_unchanged(self):
        """Should detect convergence when confidence stays the same."""
        state = BeliefRevisionState()

        assert state.check_convergence(new_confidence=0.35, previous_confidence=0.35) is True

    def test_not_converged_when_improving(self):
        """Should not detect convergence when confidence improves."""
        state = BeliefRevisionState()

        assert state.check_convergence(new_confidence=0.4, previous_confidence=0.35) is False

    def test_slight_improvement_not_converged(self):
        """Small improvements should not count as convergence."""
        state = BeliefRevisionState()

        assert state.check_convergence(new_confidence=0.351, previous_confidence=0.35) is False


class TestFullRevisionLoop:
    """Tests simulating a full belief revision loop."""

    def test_improving_confidence_stops_loop(self):
        """Loop should stop when confidence rises above threshold."""
        config = BeliefRevisionConfig(threshold=0.4, max_iterations=5)
        state = BeliefRevisionState(config)

        # Simulate: confidence starts at 0.3, improves to 0.45 after revision
        confidence = 0.3
        iterations = 0

        while state.should_revise(confidence) and iterations < 10:
            state.record_revision(confidence, [])
            iterations += 1
            # Simulate confidence improvement
            confidence = 0.45

        assert iterations == 1
        assert state.revision_count == 1

    def test_max_iterations_stops_loop(self):
        """Loop should stop at max iterations even if confidence stays low."""
        config = BeliefRevisionConfig(threshold=0.4, max_iterations=3)
        state = BeliefRevisionState(config)

        confidence = 0.2
        iterations = 0

        while state.should_revise(confidence) and iterations < 10:
            state.record_revision(confidence, [])
            iterations += 1
            # Confidence doesn't improve enough
            confidence = min(confidence + 0.05, 0.35)

        assert iterations == 3
        assert state.revision_count == 3

    def test_convergence_stops_loop(self):
        """Loop should stop when confidence converges."""
        config = BeliefRevisionConfig(threshold=0.5, max_iterations=10)
        state = BeliefRevisionState(config)

        # Simulate: confidence improves then stalls
        confidences = [0.3, 0.35, 0.38, 0.38]  # Stalls at 0.38
        iterations = 0
        previous_confidence = confidences[0]

        for i, confidence in enumerate(confidences):
            if not state.should_revise(confidence):
                break

            state.record_revision(confidence, [])
            iterations += 1

            if i > 0 and state.check_convergence(confidence, previous_confidence):
                break

            previous_confidence = confidence

        # Should stop at iteration 4 due to convergence (0.38 == 0.38)
        assert iterations == 4

    def test_no_revision_when_high_confidence(self):
        """No revision should occur when confidence is already high."""
        config = BeliefRevisionConfig(threshold=0.4, max_iterations=5)
        state = BeliefRevisionState(config)

        confidence = 0.8
        iterations = 0

        while state.should_revise(confidence) and iterations < 10:
            state.record_revision(confidence, [])
            iterations += 1

        assert iterations == 0
        assert state.revision_count == 0

    def test_complete_loop_simulation(self):
        """Simulate complete revision loop with realistic values."""
        config = BeliefRevisionConfig(threshold=0.4, max_iterations=2)
        state = BeliefRevisionState(config)

        # Initial metacog report
        initial_metacog = {
            "confidence": 0.25,
            "uncertainties": ["What is the user asking?", "Unclear context"],
        }

        # First revision
        if state.should_revise(initial_metacog["confidence"]):
            state.record_revision(
                initial_metacog["confidence"],
                initial_metacog["uncertainties"]
            )

            # After first revision, confidence improved
            revised_metacog = {
                "confidence": 0.38,
                "uncertainties": ["Some remaining ambiguity"],
            }

            # Second revision
            if state.should_revise(revised_metacog["confidence"]):
                if not state.check_convergence(revised_metacog["confidence"], initial_metacog["confidence"]):
                    state.record_revision(
                        revised_metacog["confidence"],
                        revised_metacog["uncertainties"]
                    )

                    # After second revision, confidence above threshold
                    final_metacog = {
                        "confidence": 0.55,
                        "uncertainties": [],
                    }

        assert state.revision_count == 2
        assert len(state.revision_events) == 2
        assert state.revision_events[0]["trigger_confidence"] == 0.25
        assert state.revision_events[1]["trigger_confidence"] == 0.38


class TestEdgeCases:
    """Edge cases for belief revision."""

    def test_confidence_exactly_zero(self):
        """Zero confidence should trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4))

        assert state.should_revise(0.0) is True

    def test_confidence_exactly_one(self):
        """Perfect confidence should not trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.99))

        assert state.should_revise(1.0) is False

    def test_negative_confidence_handled(self):
        """Negative confidence (invalid) should still trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4))

        # While invalid, the logic should handle it
        assert state.should_revise(-0.1) is True

    def test_confidence_above_one_handled(self):
        """Confidence > 1 (invalid) should not trigger revision."""
        state = BeliefRevisionState(BeliefRevisionConfig(threshold=0.4))

        assert state.should_revise(1.5) is False

    def test_empty_uncertainties_list(self):
        """Empty uncertainties list should be handled."""
        state = BeliefRevisionState()

        event = state.record_revision(0.3, [])

        assert event["uncertainties"] == []

    def test_very_many_uncertainties(self):
        """Large number of uncertainties should be handled."""
        state = BeliefRevisionState()

        uncertainties = [f"Uncertainty {i}" for i in range(100)]
        event = state.record_revision(0.3, uncertainties)

        assert len(event["uncertainties"]) == 100


class TestMetacogOutputParsing:
    """Tests for parsing metacog output."""

    def parse_metacog_confidence(self, metacog: dict | None) -> float:
        """
        Parse confidence from metacog output.
        Mirrors the logic in AwakeLoop._run_belief_revision_loop().
        """
        if not metacog:
            return 1.0  # High confidence when no metacog (don't revise)
        return metacog.get("confidence", 1.0)

    def test_extracts_confidence_from_metacog(self):
        """Should extract confidence value from metacog dict."""
        metacog = {
            "confidence": 0.35,
            "uncertainties": ["test"],
        }

        assert self.parse_metacog_confidence(metacog) == 0.35

    def test_defaults_to_one_when_missing(self):
        """Should default to 1.0 when confidence missing."""
        metacog = {"uncertainties": ["test"]}

        assert self.parse_metacog_confidence(metacog) == 1.0

    def test_defaults_to_one_when_none(self):
        """Should default to 1.0 when metacog is None."""
        assert self.parse_metacog_confidence(None) == 1.0

    def test_defaults_to_one_when_empty(self):
        """Should default to 1.0 when metacog is empty."""
        assert self.parse_metacog_confidence({}) == 1.0
