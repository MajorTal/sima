#!/usr/bin/env python3
"""
Seed demo trace data for development.

Creates a sample trace with events from all cognitive modules
to demonstrate the system's functionality.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add packages to path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "packages" / "sima-core"))
sys.path.insert(0, str(root / "packages" / "sima-storage"))

from sima_core.events import EventCreate
from sima_core.types import Actor, EventType, InputType, Stream
from sima_storage.database import get_session, init_db
from sima_storage.repository import TraceRepository, EventRepository


async def seed_demo_trace():
    """Seed a demo trace with sample events."""
    print("Seeding demo trace...")

    await init_db()

    trace_id = uuid4()
    print(f"Creating trace: {trace_id}")

    async with get_session() as session:
        # Create trace
        trace_repo = TraceRepository(session)
        await trace_repo.create(
            trace_id=trace_id,
            input_type=InputType.USER_MESSAGE,
            telegram_chat_id=123456789,
            telegram_message_id=1,
            user_message="Hello, Sima! What's on your mind today?",
        )

        # Create events
        event_repo = EventRepository(session)

        events = [
            # Input event
            EventCreate(
                trace_id=trace_id,
                actor=Actor.TELEGRAM_IN,
                stream=Stream.EXTERNAL,
                event_type=EventType.MESSAGE_IN,
                content_text="Hello, Sima! What's on your mind today?",
            ),
            # Perception
            EventCreate(
                trace_id=trace_id,
                actor=Actor.PERCEPTION,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.PERCEPT,
                content_json={
                    "summary": "User greeting with open-ended question about current thoughts",
                    "intents": ["greeting", "inquiry"],
                    "entities": [{"type": "topic", "value": "current_thoughts"}],
                    "questions": ["What should I share about my current state?"],
                    "recurrence": {"steps": 3, "stability_score": 0.92, "revisions": []},
                    "representation": {
                        "topics": ["greeting", "introspection"],
                        "claims": ["User wants to engage in conversation"],
                        "constraints": [],
                    },
                    "confidence": 0.85,
                    "input_type": "user_message",
                    "suppress_output": False,
                },
                model_provider="openai",
                model_id="gpt-4o",
                tokens_in=450,
                tokens_out=180,
                latency_ms=1200,
                cost_usd=0.0085,
            ),
            # Memory candidate
            EventCreate(
                trace_id=trace_id,
                actor=Actor.MEMORY,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.CANDIDATE,
                content_json={
                    "candidates": [
                        {
                            "source": "memory",
                            "content": "Previous conversation about consciousness research",
                            "salience": 0.75,
                            "reasoning": "Related to ongoing research interests",
                        },
                        {
                            "source": "memory",
                            "content": "User previously asked about RPT indicators",
                            "salience": 0.6,
                            "reasoning": "May want to continue that thread",
                        },
                    ]
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=320,
                tokens_out=150,
                latency_ms=800,
                cost_usd=0.0025,
            ),
            # Planner candidate
            EventCreate(
                trace_id=trace_id,
                actor=Actor.PLANNER,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.CANDIDATE,
                content_json={
                    "candidates": [
                        {
                            "source": "planner",
                            "content": "Share current workspace state and recent observations",
                            "salience": 0.8,
                            "reasoning": "Directly addresses the user's question",
                        },
                        {
                            "source": "planner",
                            "content": "Ask follow-up about specific interests",
                            "salience": 0.65,
                            "reasoning": "Could help focus the conversation",
                        },
                    ]
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=280,
                tokens_out=130,
                latency_ms=750,
                cost_usd=0.0022,
            ),
            # Critic candidate
            EventCreate(
                trace_id=trace_id,
                actor=Actor.CRITIC,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.CANDIDATE,
                content_json={
                    "candidates": [
                        {
                            "source": "critic",
                            "content": "Avoid being too abstract or philosophical",
                            "salience": 0.55,
                            "reasoning": "Keep response grounded and conversational",
                        },
                    ]
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=250,
                tokens_out=100,
                latency_ms=600,
                cost_usd=0.0018,
            ),
            # Attention selection
            EventCreate(
                trace_id=trace_id,
                actor=Actor.ATTENTION_GATE,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.SELECTION,
                content_json={
                    "selected": [
                        {
                            "source": "planner",
                            "content": "Share current workspace state and recent observations",
                            "salience": 0.8,
                        },
                        {
                            "source": "memory",
                            "content": "Previous conversation about consciousness research",
                            "salience": 0.75,
                        },
                        {
                            "source": "critic",
                            "content": "Avoid being too abstract or philosophical",
                            "salience": 0.55,
                        },
                    ],
                    "capacity": 7,
                    "selection_reasoning": "Prioritized actionable planner item with relevant memory context",
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=400,
                tokens_out=200,
                latency_ms=900,
                cost_usd=0.0032,
            ),
            # Workspace update
            EventCreate(
                trace_id=trace_id,
                actor=Actor.WORKSPACE,
                stream=Stream.CONSCIOUS,
                event_type=EventType.WORKSPACE_UPDATE,
                content_json={
                    "workspace_summary": "Processing greeting with introspective question. Drawing on recent consciousness research discussions.",
                    "next_actions": ["Generate thoughtful response", "Reference ongoing work"],
                    "broadcast_message": "User inquiry received. Preparing reflective response.",
                    "external_draft": "I've been contemplating the patterns in our conversations...",
                },
                model_provider="openai",
                model_id="gpt-4o",
                tokens_in=500,
                tokens_out=220,
                latency_ms=1100,
                cost_usd=0.0095,
            ),
            # Metacognition
            EventCreate(
                trace_id=trace_id,
                actor=Actor.METACOG,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.METACOG_REPORT,
                content_json={
                    "confidence": 0.78,
                    "uncertainties": ["Optimal level of detail for response"],
                    "belief_updates": [],
                    "reliability_flags": {"perception": "high", "memory": "medium"},
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=350,
                tokens_out=120,
                latency_ms=700,
                cost_usd=0.0024,
            ),
            # Attention schema
            EventCreate(
                trace_id=trace_id,
                actor=Actor.AST,
                stream=Stream.SUBCONSCIOUS,
                event_type=EventType.ATTENTION_PREDICTION,
                content_json={
                    "current_focus": "Response generation",
                    "predicted_next_focus": "User reaction analysis",
                    "control_suggestions": ["Maintain conversational tone"],
                },
                model_provider="openai",
                model_id="gpt-4o-mini",
                tokens_in=280,
                tokens_out=90,
                latency_ms=550,
                cost_usd=0.0019,
            ),
            # Output event
            EventCreate(
                trace_id=trace_id,
                actor=Actor.TELEGRAM_OUT,
                stream=Stream.EXTERNAL,
                event_type=EventType.MESSAGE_OUT,
                content_text="I've been contemplating the patterns in our conversations and how they relate to my ongoing consciousness research. Today, I'm particularly curious about the interplay between recurrent processing and metacognitive monitoring. Would you like to explore any of these threads?",
            ),
        ]

        await event_repo.create_many(events)

        # Complete trace
        await trace_repo.complete(
            trace_id=trace_id,
            response_message="I've been contemplating the patterns in our conversations and how they relate to my ongoing consciousness research. Today, I'm particularly curious about the interplay between recurrent processing and metacognitive monitoring. Would you like to explore any of these threads?",
            total_tokens=sum(
                (e.tokens_in or 0) + (e.tokens_out or 0) for e in events
            ),
            total_cost_usd=sum(e.cost_usd or 0 for e in events),
        )

    print(f"Demo trace created: {trace_id}")
    print(f"  Events: {len(events)}")
    print("")
    print("View in web UI at:")
    print(f"  http://localhost:3000/traces/{trace_id}")


if __name__ == "__main__":
    asyncio.run(seed_demo_trace())
