"""
Unit tests for AST (Attention Schema Theory) predict-compare logic.

Tests the attention prediction comparison and control success rate calculation
that implements the AST predict-compare cycle.
"""

import pytest


def calculate_control_success_rate(
    predicted_ids: set[str],
    actual_ids: set[str],
) -> tuple[float, str, set[str], set[str], set[str]]:
    """
    Calculate control success rate for AST comparison.

    This mirrors the logic in AwakeLoop._run_attention_schema().

    Args:
        predicted_ids: Set of IDs predicted in previous trace
        actual_ids: Set of IDs actually selected in current trace

    Returns:
        Tuple of (control_success_rate, control_notes, correct_predictions,
                  missed_predictions, unexpected_focus)
    """
    if not predicted_ids:
        return 0.0, "No prior predictions available.", set(), set(), actual_ids

    correct_predictions = predicted_ids & actual_ids
    control_success_rate = len(correct_predictions) / len(predicted_ids)

    missed_predictions = predicted_ids - actual_ids
    unexpected_focus = actual_ids - predicted_ids

    # Build comparison notes
    if control_success_rate >= 0.8:
        control_notes = "Excellent prediction accuracy. Attention model is well-calibrated."
    elif control_success_rate >= 0.5:
        control_notes = "Moderate prediction accuracy. Some unexpected attention shifts occurred."
    elif control_success_rate > 0:
        control_notes = "Low prediction accuracy. Attention shifted to unexpected items."
    else:
        control_notes = "No overlap between predicted and actual focus. Major attention shift occurred."

    return (control_success_rate, control_notes, correct_predictions,
            missed_predictions, unexpected_focus)


class TestControlSuccessRateCalculation:
    """Tests for control success rate calculation."""

    def test_perfect_prediction(self):
        """When all predictions match actual, rate should be 1.0."""
        predicted = {"c1", "c2", "c3"}
        actual = {"c1", "c2", "c3"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 1.0
        assert "Excellent" in notes
        assert correct == {"c1", "c2", "c3"}
        assert missed == set()
        assert unexpected == set()

    def test_complete_miss(self):
        """When no predictions match, rate should be 0.0."""
        predicted = {"c1", "c2"}
        actual = {"c3", "c4"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.0
        assert "No overlap" in notes
        assert correct == set()
        assert missed == {"c1", "c2"}
        assert unexpected == {"c3", "c4"}

    def test_partial_match_high(self):
        """When most predictions match, rate should be >= 0.8."""
        predicted = {"c1", "c2", "c3", "c4", "c5"}
        actual = {"c1", "c2", "c3", "c4", "c6"}  # 4/5 match

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.8
        assert "Excellent" in notes
        assert correct == {"c1", "c2", "c3", "c4"}
        assert missed == {"c5"}
        assert unexpected == {"c6"}

    def test_partial_match_moderate(self):
        """When about half predictions match, rate should be moderate."""
        predicted = {"c1", "c2", "c3", "c4"}
        actual = {"c1", "c2", "c5", "c6"}  # 2/4 match

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.5
        assert "Moderate" in notes
        assert correct == {"c1", "c2"}
        assert missed == {"c3", "c4"}
        assert unexpected == {"c5", "c6"}

    def test_partial_match_low(self):
        """When few predictions match, rate should be low."""
        predicted = {"c1", "c2", "c3", "c4", "c5"}
        actual = {"c1", "c6", "c7", "c8"}  # 1/5 match

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(0.2, abs=0.01)
        assert "Low prediction accuracy" in notes
        assert correct == {"c1"}
        assert missed == {"c2", "c3", "c4", "c5"}
        assert unexpected == {"c6", "c7", "c8"}

    def test_empty_predictions(self):
        """When no predictions exist, rate should be 0.0."""
        predicted = set()
        actual = {"c1", "c2"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.0
        assert "No prior predictions" in notes
        assert correct == set()
        assert missed == set()
        assert unexpected == {"c1", "c2"}

    def test_empty_actual(self):
        """When no actual focus, all predictions are missed."""
        predicted = {"c1", "c2"}
        actual = set()

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.0
        assert "No overlap" in notes
        assert correct == set()
        assert missed == {"c1", "c2"}
        assert unexpected == set()

    def test_both_empty(self):
        """When both are empty, rate should be 0.0 with appropriate notes."""
        predicted = set()
        actual = set()

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.0
        assert "No prior predictions" in notes

    def test_superset_prediction(self):
        """When predictions are superset of actual, some will be missed."""
        predicted = {"c1", "c2", "c3", "c4", "c5"}
        actual = {"c1", "c2"}  # 2/5 match

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(0.4, abs=0.01)
        assert "Low prediction accuracy" in notes
        assert correct == {"c1", "c2"}
        assert missed == {"c3", "c4", "c5"}
        assert unexpected == set()

    def test_subset_prediction(self):
        """When predictions are subset of actual, all predictions match."""
        predicted = {"c1", "c2"}
        actual = {"c1", "c2", "c3", "c4", "c5"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 1.0
        assert "Excellent" in notes
        assert correct == {"c1", "c2"}
        assert missed == set()
        assert unexpected == {"c3", "c4", "c5"}


class TestControlNotesThresholds:
    """Tests for control notes threshold boundaries."""

    def test_threshold_0_79_is_not_excellent(self):
        """Rate of 0.79 should not be 'Excellent'."""
        # 79/100 predictions correct
        predicted = set(f"c{i}" for i in range(100))
        actual = set(f"c{i}" for i in range(79)) | {"extra1"}

        rate, notes, _, _, _ = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(0.79, abs=0.01)
        assert "Excellent" not in notes
        assert "Moderate" in notes

    def test_threshold_0_80_is_excellent(self):
        """Rate of 0.80 should be 'Excellent'."""
        # 4/5 predictions correct
        predicted = set(f"c{i}" for i in range(5))
        actual = set(f"c{i}" for i in range(4)) | {"extra1"}

        rate, notes, _, _, _ = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(0.8, abs=0.01)
        assert "Excellent" in notes

    def test_threshold_0_49_is_not_moderate(self):
        """Rate of 0.49 should not be 'Moderate'."""
        # 49/100 predictions correct
        predicted = set(f"c{i}" for i in range(100))
        actual = set(f"c{i}" for i in range(49)) | set(f"extra{i}" for i in range(51))

        rate, notes, _, _, _ = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(0.49, abs=0.01)
        assert "Moderate" not in notes
        assert "Low prediction accuracy" in notes

    def test_threshold_0_50_is_moderate(self):
        """Rate of 0.50 should be 'Moderate'."""
        # 1/2 predictions correct
        predicted = {"c1", "c2"}
        actual = {"c1", "c3"}

        rate, notes, _, _, _ = calculate_control_success_rate(predicted, actual)

        assert rate == 0.5
        assert "Moderate" in notes


class TestEdgeCases:
    """Edge cases for AST comparison."""

    def test_single_prediction_match(self):
        """Single prediction that matches."""
        predicted = {"c1"}
        actual = {"c1"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 1.0
        assert correct == {"c1"}

    def test_single_prediction_miss(self):
        """Single prediction that doesn't match."""
        predicted = {"c1"}
        actual = {"c2"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.0
        assert missed == {"c1"}
        assert unexpected == {"c2"}

    def test_large_sets(self):
        """Test with larger sets to verify performance."""
        predicted = set(f"c{i}" for i in range(1000))
        actual = set(f"c{i}" for i in range(500, 1500))  # 500 overlap

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == 0.5
        assert len(correct) == 500
        assert len(missed) == 500
        assert len(unexpected) == 500

    def test_ids_with_special_characters(self):
        """IDs with special characters should work."""
        predicted = {"user:123", "item-456", "tag_789"}
        actual = {"user:123", "item-456", "new:abc"}

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(predicted, actual)

        assert rate == pytest.approx(2/3, abs=0.01)
        assert correct == {"user:123", "item-456"}


class TestComparisonEventStructure:
    """Tests for building comparison events as done in awake_loop."""

    def build_comparison_event(
        self,
        prior_prediction: dict,
        selected_items: list[dict],
    ) -> dict:
        """
        Build a comparison event like AwakeLoop._run_attention_schema().
        """
        predicted_ids = set(prior_prediction.get("predicted_next_focus", []))
        actual_ids = set(item.get("id", "") for item in selected_items)

        rate, notes, correct, missed, unexpected = calculate_control_success_rate(
            predicted_ids, actual_ids
        )

        return {
            "prior_prediction": list(predicted_ids),
            "actual_focus": list(actual_ids),
            "control_success_rate": round(rate, 4),
            "control_notes": notes,
            "correct_predictions": list(correct),
            "missed_predictions": list(missed),
            "unexpected_focus": list(unexpected),
        }

    def test_builds_correct_event_structure(self):
        """Event should have all required fields."""
        prior = {"predicted_next_focus": ["c1", "c2"]}
        selected = [{"id": "c1"}, {"id": "c3"}]

        event = self.build_comparison_event(prior, selected)

        assert "prior_prediction" in event
        assert "actual_focus" in event
        assert "control_success_rate" in event
        assert "control_notes" in event
        assert "correct_predictions" in event
        assert "missed_predictions" in event
        assert "unexpected_focus" in event

    def test_handles_missing_ids_in_selected_items(self):
        """Selected items without 'id' should use empty string."""
        prior = {"predicted_next_focus": ["c1"]}
        selected = [{"content": "no id here"}]

        event = self.build_comparison_event(prior, selected)

        # Empty string ID should be in actual_focus
        assert "" in event["actual_focus"]

    def test_handles_empty_prior_prediction(self):
        """Empty prior prediction should work."""
        prior = {}
        selected = [{"id": "c1"}]

        event = self.build_comparison_event(prior, selected)

        assert event["prior_prediction"] == []
        assert event["control_success_rate"] == 0.0

    def test_handles_empty_selected_items(self):
        """Empty selected items should work."""
        prior = {"predicted_next_focus": ["c1", "c2"]}
        selected = []

        event = self.build_comparison_event(prior, selected)

        assert event["actual_focus"] == []
        assert event["control_success_rate"] == 0.0

    def test_rate_is_rounded(self):
        """Control success rate should be rounded to 4 decimal places."""
        prior = {"predicted_next_focus": ["c1", "c2", "c3"]}
        selected = [{"id": "c1"}]  # 1/3 = 0.333333...

        event = self.build_comparison_event(prior, selected)

        assert event["control_success_rate"] == 0.3333
