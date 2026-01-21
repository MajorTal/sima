"""
Unit tests for the simulated competition attention gate.

Tests the biologically-inspired competition mechanism where candidates
compete for workspace access through mutual inhibition dynamics.
"""

import pytest

from sima_brain.simulated_competition import (
    CompetitionResult,
    CandidateState,
    compute_similarity,
    run_competition,
)


class TestComputeSimilarity:
    """Tests for the similarity computation function."""

    def test_identical_candidates_have_high_similarity(self):
        """Two candidates with identical content should have similarity of 1.0."""
        c1 = {"content": "hello world test", "description": "a test"}
        c2 = {"content": "hello world test", "description": "a test"}

        similarity = compute_similarity(c1, c2)

        assert similarity == 1.0

    def test_completely_different_candidates_have_zero_similarity(self):
        """Candidates with no word overlap should have similarity of 0.0."""
        c1 = {"content": "alpha beta gamma", "description": "first"}
        c2 = {"content": "one two three", "description": "second"}

        similarity = compute_similarity(c1, c2)

        assert similarity == 0.0

    def test_partial_overlap_gives_intermediate_similarity(self):
        """Candidates with partial word overlap should have intermediate similarity."""
        # Note: content + description are concatenated, so "hello world" + "test" = "hello worldtest"
        # which splits to {hello, worldtest}. Use spaces in description to get distinct words.
        c1 = {"content": "hello world", "description": " test"}
        c2 = {"content": "hello there", "description": " example"}

        # c1: "hello world test" -> words: {hello, world, test}
        # c2: "hello there example" -> words: {hello, there, example}
        # Intersection: {hello} = 1
        # Union: {hello, world, test, there, example} = 5
        # Similarity: 1/5 = 0.2
        similarity = compute_similarity(c1, c2)

        assert 0 < similarity < 1
        assert similarity == pytest.approx(0.2, abs=0.01)

    def test_empty_content_gives_zero_similarity(self):
        """Candidates with empty content should have zero similarity."""
        c1 = {"content": "", "description": ""}
        c2 = {"content": "hello world", "description": "test"}

        similarity = compute_similarity(c1, c2)

        assert similarity == 0.0

    def test_missing_content_fields_handled(self):
        """Candidates missing content/description fields should not crash."""
        c1 = {"id": "c1"}
        c2 = {"id": "c2"}

        similarity = compute_similarity(c1, c2)

        assert similarity == 0.0

    def test_case_insensitive_similarity(self):
        """Similarity comparison should be case-insensitive."""
        c1 = {"content": "Hello World", "description": ""}
        c2 = {"content": "hello world", "description": ""}

        similarity = compute_similarity(c1, c2)

        assert similarity == 1.0


class TestRunCompetitionBasic:
    """Basic tests for the competition algorithm."""

    def test_empty_candidates_returns_empty_result(self):
        """Competition with no candidates should return empty result."""
        result = run_competition(candidates=[], workspace_capacity=5)

        assert result.selected == []
        assert result.rejected == []
        assert result.iterations_run == 0
        assert "No candidates" in result.selection_rationale

    def test_single_candidate_is_always_selected(self):
        """A single candidate should always be selected."""
        candidates = [
            {"id": "c1", "salience": 0.8, "content": "test", "description": "a candidate"}
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5)

        assert len(result.selected) == 1
        assert result.selected[0]["id"] == "c1"
        assert len(result.rejected) == 0

    def test_selects_top_k_by_capacity(self):
        """Should select exactly K candidates when more than K are provided."""
        candidates = [
            {"id": "c1", "salience": 0.9, "content": "unique one", "description": "first"},
            {"id": "c2", "salience": 0.8, "content": "unique two", "description": "second"},
            {"id": "c3", "salience": 0.7, "content": "unique three", "description": "third"},
            {"id": "c4", "salience": 0.6, "content": "unique four", "description": "fourth"},
            {"id": "c5", "salience": 0.5, "content": "unique five", "description": "fifth"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=3)

        assert len(result.selected) == 3
        assert len(result.rejected) == 2

    def test_high_salience_candidates_tend_to_win(self):
        """Candidates with higher salience should tend to be selected."""
        candidates = [
            {"id": "high", "salience": 0.95, "content": "alpha", "description": "high priority"},
            {"id": "low", "salience": 0.1, "content": "beta", "description": "low priority"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=1)

        # High salience candidate should win
        assert len(result.selected) == 1
        assert result.selected[0]["id"] == "high"

    def test_default_salience_used_when_missing(self):
        """Candidates missing salience should get default value of 0.5."""
        candidates = [
            {"id": "c1", "content": "test", "description": "no salience"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5)

        # Should not crash and should select the candidate
        assert len(result.selected) == 1


class TestSelfExcitation:
    """Tests for the self-excitation dynamics."""

    def test_high_activation_items_get_boosted(self):
        """Items with activation > 0.5 should get boosted via self-excitation."""
        # Two candidates with different starting saliences
        # With iterations, the higher one should pull further ahead
        candidates = [
            {"id": "high", "salience": 0.8, "content": "unique alpha", "description": "one"},
            {"id": "medium", "salience": 0.6, "content": "unique beta", "description": "two"},
        ]

        result = run_competition(
            candidates=candidates,
            workspace_capacity=2,
            iterations=10,
            self_excitation=0.2,  # Strong self-excitation
            lateral_inhibition=0.0,  # Disable inhibition for this test
        )

        # Both should be selected (capacity=2)
        # Check that the trace shows increasing activation for high salience item
        assert len(result.competition_trace) == 10

        # First iteration activations
        first_iter = result.competition_trace[0]["activations"]
        last_iter = result.competition_trace[-1]["activations"]

        # The "high" candidate should have increased relative to start
        # (or at least maintained due to normalization)
        assert last_iter["high"] >= first_iter["high"] or last_iter["high"] >= 0.5


class TestLateralInhibition:
    """Tests for the lateral inhibition dynamics."""

    def test_similar_candidates_suppress_each_other(self):
        """Similar candidates should inhibit each other, with weaker losing."""
        # Two candidates with overlapping content
        candidates = [
            {"id": "strong", "salience": 0.8, "content": "hello world test", "description": "match"},
            {"id": "weak", "salience": 0.5, "content": "hello world test", "description": "match"},
        ]

        result = run_competition(
            candidates=candidates,
            workspace_capacity=1,
            iterations=10,
            lateral_inhibition=0.3,
            similarity_threshold=0.5,
        )

        # Strong should win, weak should be rejected
        assert len(result.selected) == 1
        assert result.selected[0]["id"] == "strong"
        # Should have had inhibition events
        assert result.inhibition_events > 0

    def test_dissimilar_candidates_do_not_inhibit(self):
        """Candidates below similarity threshold should not inhibit each other."""
        candidates = [
            {"id": "c1", "salience": 0.6, "content": "alpha beta gamma", "description": "first"},
            {"id": "c2", "salience": 0.6, "content": "one two three", "description": "second"},
        ]

        result = run_competition(
            candidates=candidates,
            workspace_capacity=1,
            iterations=10,
            lateral_inhibition=0.5,  # Strong inhibition
            similarity_threshold=0.9,  # High threshold - won't trigger
        )

        # No inhibition should have occurred
        assert result.inhibition_events == 0

    def test_inhibition_events_counted(self):
        """The number of inhibition events should be tracked."""
        # Create similar candidates to trigger inhibition
        candidates = [
            {"id": "c1", "salience": 0.7, "content": "same same", "description": "test"},
            {"id": "c2", "salience": 0.6, "content": "same same", "description": "test"},
            {"id": "c3", "salience": 0.5, "content": "same same", "description": "test"},
        ]

        result = run_competition(
            candidates=candidates,
            workspace_capacity=2,
            iterations=5,
            lateral_inhibition=0.2,
            similarity_threshold=0.3,
        )

        # Should have multiple inhibition events (3 pairs × 5 iterations)
        assert result.inhibition_events > 0


class TestActivationFloor:
    """Tests for the activation floor mechanism."""

    def test_activation_cannot_drop_below_floor(self):
        """Activations should never drop below the floor value."""
        # Set up candidates where inhibition would drive one to zero
        candidates = [
            {"id": "strong", "salience": 0.99, "content": "hello world", "description": "test"},
            {"id": "weak", "salience": 0.1, "content": "hello world", "description": "test"},
        ]

        activation_floor = 0.05
        result = run_competition(
            candidates=candidates,
            workspace_capacity=2,
            iterations=20,  # Many iterations
            lateral_inhibition=0.9,  # Very strong inhibition
            activation_floor=activation_floor,
        )

        # Check trace - weak should never go below floor (accounting for floating point and rounding)
        # Trace values are rounded to 4 decimal places, so allow for small floating point errors
        for trace_entry in result.competition_trace:
            for activation in trace_entry["activations"].values():
                assert activation >= activation_floor - 0.01  # Allow small floating point tolerance


class TestConvergence:
    """Tests for convergence measurement."""

    def test_convergence_delta_measured(self):
        """The convergence delta should be computed."""
        candidates = [
            {"id": "c1", "salience": 0.8, "content": "test", "description": "one"},
            {"id": "c2", "salience": 0.5, "content": "other", "description": "two"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=2)

        # Should have a non-negative convergence delta
        assert result.convergence_delta >= 0


class TestCompetitionTrace:
    """Tests for the competition trace telemetry."""

    def test_trace_has_correct_iterations(self):
        """Trace should have one entry per iteration."""
        candidates = [
            {"id": "c1", "salience": 0.5, "content": "test", "description": "one"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5, iterations=7)

        assert len(result.competition_trace) == 7
        assert result.iterations_run == 7

    def test_trace_contains_activation_history(self):
        """Each trace entry should contain activation values for each candidate."""
        candidates = [
            {"id": "c1", "salience": 0.5, "content": "test1", "description": "one"},
            {"id": "c2", "salience": 0.6, "content": "test2", "description": "two"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=2, iterations=3)

        for trace_entry in result.competition_trace:
            assert "iteration" in trace_entry
            assert "activations" in trace_entry
            assert "c1" in trace_entry["activations"]
            assert "c2" in trace_entry["activations"]


class TestCompetitionResult:
    """Tests for the CompetitionResult dataclass."""

    def test_selection_rationale_generated(self):
        """A selection rationale should be generated."""
        candidates = [
            {"id": "c1", "salience": 0.8, "content": "test", "description": "one"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5)

        assert result.selection_rationale
        assert len(result.selection_rationale) > 0

    def test_result_contains_all_fields(self):
        """CompetitionResult should have all expected fields."""
        candidates = [
            {"id": "c1", "salience": 0.5, "content": "test", "description": "one"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5)

        assert isinstance(result, CompetitionResult)
        assert isinstance(result.selected, list)
        assert isinstance(result.rejected, list)
        assert isinstance(result.selection_rationale, str)
        assert isinstance(result.competition_trace, list)
        assert isinstance(result.iterations_run, int)
        assert isinstance(result.convergence_delta, float)
        assert isinstance(result.inhibition_events, int)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_all_candidates_same_salience(self):
        """When all candidates have same salience, selection should still work."""
        candidates = [
            {"id": "c1", "salience": 0.5, "content": "unique one", "description": "first"},
            {"id": "c2", "salience": 0.5, "content": "unique two", "description": "second"},
            {"id": "c3", "salience": 0.5, "content": "unique three", "description": "third"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=2)

        assert len(result.selected) == 2
        assert len(result.rejected) == 1

    def test_capacity_larger_than_candidates(self):
        """When capacity exceeds candidate count, all should be selected."""
        candidates = [
            {"id": "c1", "salience": 0.5, "content": "test", "description": "one"},
            {"id": "c2", "salience": 0.6, "content": "other", "description": "two"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=10)

        assert len(result.selected) == 2
        assert len(result.rejected) == 0

    def test_salience_out_of_range_clamped(self):
        """Salience values outside [0, 1] should be clamped."""
        candidates = [
            {"id": "too_high", "salience": 2.0, "content": "test", "description": "one"},
            {"id": "too_low", "salience": -0.5, "content": "other", "description": "two"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=5)

        # Should not crash and should process normally
        assert len(result.selected) == 2

    def test_zero_iterations(self):
        """Zero iterations should still produce valid result."""
        candidates = [
            {"id": "c1", "salience": 0.8, "content": "test", "description": "one"},
            {"id": "c2", "salience": 0.5, "content": "other", "description": "two"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=1, iterations=0)

        # Selection based on initial salience only
        assert len(result.selected) == 1
        assert result.iterations_run == 0
        assert len(result.competition_trace) == 0

    def test_capacity_zero(self):
        """Workspace capacity of 0 should select nothing."""
        candidates = [
            {"id": "c1", "salience": 0.9, "content": "test", "description": "one"},
        ]

        result = run_competition(candidates=candidates, workspace_capacity=0)

        assert len(result.selected) == 0
        assert len(result.rejected) == 1

    def test_very_small_lateral_inhibition(self):
        """Very small lateral inhibition should have minimal effect."""
        candidates = [
            {"id": "c1", "salience": 0.6, "content": "same content", "description": "test"},
            {"id": "c2", "salience": 0.5, "content": "same content", "description": "test"},
        ]

        result = run_competition(
            candidates=candidates,
            workspace_capacity=2,
            lateral_inhibition=0.001,  # Very small
        )

        # Both should still be selected
        assert len(result.selected) == 2
