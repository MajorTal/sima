"""
Simulated Competition for the Attention Gate.

Implements a biologically-inspired competition mechanism where candidates
compete for workspace access through mutual inhibition dynamics.

This replaces LLM-as-judge ranking to avoid the "homunculus problem" —
instead of having a judge module that knows what's important, candidates
compete based on their intrinsic properties.

Algorithm:
1. Initialize each candidate with activation = salience
2. Run N competition iterations
3. At each iteration:
   - Apply self-excitation (winners keep winning)
   - Apply lateral inhibition (similar candidates suppress each other)
   - Normalize activations
4. Select top-K by final activation
5. Return selection with competition trace for telemetry

References:
- Inspired by competitive queuing models (Grossberg, 1978)
- Dehaene & Naccache (2001) on workspace access competition
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CompetitionResult:
    """Result of the simulated competition."""

    selected: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    selection_rationale: str
    competition_trace: list[dict[str, Any]] = field(default_factory=list)

    # Telemetry for GWT indicators
    iterations_run: int = 0
    convergence_delta: float = 0.0
    inhibition_events: int = 0


@dataclass
class CandidateState:
    """Internal state of a candidate during competition."""

    candidate: dict[str, Any]
    activation: float
    activation_history: list[float] = field(default_factory=list)


def compute_similarity(c1: dict, c2: dict) -> float:
    """
    Compute similarity between two candidates.

    Higher similarity means more mutual inhibition.
    Currently uses a simple overlap-based heuristic.
    """
    # Get string representations for comparison
    text1 = str(c1.get("content", "")) + str(c1.get("description", ""))
    text2 = str(c2.get("content", "")) + str(c2.get("description", ""))

    # Simple word overlap similarity
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())

    if not words1 or not words2:
        return 0.0

    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def run_competition(
    candidates: list[dict[str, Any]],
    workspace_capacity: int,
    iterations: int = 10,
    self_excitation: float = 0.1,
    lateral_inhibition: float = 0.2,
    similarity_threshold: float = 0.3,
    activation_floor: float = 0.01,
) -> CompetitionResult:
    """
    Run the simulated competition.

    Args:
        candidates: List of candidates with 'salience' and 'id' fields.
        workspace_capacity: K - max items to select.
        iterations: Number of competition cycles.
        self_excitation: Boost factor for high-activation items.
        lateral_inhibition: Suppression factor for similar items.
        similarity_threshold: Minimum similarity for inhibition to apply.
        activation_floor: Minimum activation to stay in competition.

    Returns:
        CompetitionResult with selected/rejected items and trace.
    """
    if not candidates:
        return CompetitionResult(
            selected=[],
            rejected=[],
            selection_rationale="No candidates provided.",
            iterations_run=0,
        )

    # Initialize candidate states
    states: list[CandidateState] = []
    for c in candidates:
        # Use salience as initial activation, default to 0.5
        initial_activation = float(c.get("salience", 0.5))
        # Clamp to valid range
        initial_activation = max(0.0, min(1.0, initial_activation))
        states.append(CandidateState(
            candidate=c,
            activation=initial_activation,
            activation_history=[initial_activation],
        ))

    # Competition trace for telemetry
    trace = []
    inhibition_events = 0
    prev_activations = [s.activation for s in states]

    # Run competition iterations
    for iteration in range(iterations):
        # 1. Self-excitation: high activation items get boosted
        for state in states:
            if state.activation > 0.5:
                state.activation += self_excitation * state.activation

        # 2. Lateral inhibition: similar candidates suppress each other
        for i, state_i in enumerate(states):
            for j, state_j in enumerate(states):
                if i >= j:
                    continue

                similarity = compute_similarity(
                    state_i.candidate,
                    state_j.candidate,
                )

                if similarity >= similarity_threshold:
                    inhibition_events += 1
                    # Stronger candidate inhibits weaker
                    if state_i.activation > state_j.activation:
                        state_j.activation -= lateral_inhibition * similarity
                    else:
                        state_i.activation -= lateral_inhibition * similarity

        # 3. Apply activation floor (candidates drop out if too low)
        for state in states:
            state.activation = max(activation_floor, state.activation)

        # 4. Normalize to [0, 1] range
        max_activation = max(s.activation for s in states)
        if max_activation > 1.0:
            for state in states:
                state.activation /= max_activation

        # Record history
        for state in states:
            state.activation_history.append(state.activation)

        # Record trace for this iteration
        trace.append({
            "iteration": iteration + 1,
            "activations": {
                s.candidate.get("id", f"c{i}"): round(s.activation, 4)
                for i, s in enumerate(states)
            },
        })

    # Calculate convergence (how much activations changed in final iteration)
    current_activations = [s.activation for s in states]
    convergence_delta = sum(
        abs(curr - prev)
        for curr, prev in zip(current_activations, prev_activations)
    ) / len(states) if states else 0.0

    # Sort by final activation
    sorted_states = sorted(states, key=lambda s: s.activation, reverse=True)

    # Select top-K
    selected_states = sorted_states[:workspace_capacity]
    rejected_states = sorted_states[workspace_capacity:]

    selected = [s.candidate for s in selected_states]
    rejected = [s.candidate for s in rejected_states]

    # Build rationale
    rationale_parts = [
        f"Ran {iterations} competition iterations with lateral inhibition.",
        f"Self-excitation: {self_excitation}, Lateral inhibition: {lateral_inhibition}.",
        f"Total inhibition events: {inhibition_events}.",
        f"Convergence delta: {convergence_delta:.4f}.",
    ]

    if selected:
        top_item = selected[0]
        top_activation = selected_states[0].activation
        rationale_parts.append(
            f"Top winner: '{top_item.get('id', 'unknown')}' "
            f"with activation {top_activation:.4f}."
        )

    selection_rationale = " ".join(rationale_parts)

    logger.debug(
        f"Competition complete: {len(selected)} selected, {len(rejected)} rejected, "
        f"{inhibition_events} inhibition events"
    )

    return CompetitionResult(
        selected=selected,
        rejected=rejected,
        selection_rationale=selection_rationale,
        competition_trace=trace,
        iterations_run=iterations,
        convergence_delta=convergence_delta,
        inhibition_events=inhibition_events,
    )
