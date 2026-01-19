"""Initial schema with events, traces, and memories.

Revision ID: 001
Revises:
Create Date: 2025-01-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enums
    input_type_enum = postgresql.ENUM(
        "user_message", "minute_tick", "autonomous_tick",
        name="input_type_enum",
        create_type=True,
    )
    input_type_enum.create(op.get_bind(), checkfirst=True)

    stream_enum = postgresql.ENUM(
        "external", "conscious", "subconscious", "sleep",
        name="stream_enum",
        create_type=True,
    )
    stream_enum.create(op.get_bind(), checkfirst=True)

    actor_enum = postgresql.ENUM(
        "telegram_in", "perception", "memory", "planner", "critic",
        "attention_gate", "workspace", "metacog", "ast", "speaker",
        "monologue", "sleep", "telegram_out", "system",
        name="actor_enum",
        create_type=True,
    )
    actor_enum.create(op.get_bind(), checkfirst=True)

    event_type_enum = postgresql.ENUM(
        "message_in", "tick", "percept", "candidate", "selection",
        "workspace_update", "broadcast", "metacog_report", "belief_revision",
        "attention_prediction", "attention_comparison", "monologue",
        "message_out", "sleep_start", "sleep_digest", "memory_consolidation",
        "sleep_end", "error", "pause", "resume",
        name="event_type_enum",
        create_type=True,
    )
    event_type_enum.create(op.get_bind(), checkfirst=True)

    # Create traces table
    op.create_table(
        "traces",
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "input_type",
            sa.Enum("user_message", "minute_tick", "autonomous_tick", name="input_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("telegram_chat_id", sa.Integer(), nullable=True),
        sa.Column("telegram_message_id", sa.Integer(), nullable=True),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.Column("response_message", sa.Text(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), default=0),
        sa.Column("total_cost_usd", sa.Float(), default=0.0),
        sa.PrimaryKeyConstraint("trace_id"),
    )
    op.create_index("ix_traces_started_at", "traces", ["started_at"])
    op.create_index("ix_traces_input_type", "traces", ["input_type"])

    # Create events table
    op.create_table(
        "events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column(
            "actor",
            sa.Enum(
                "telegram_in", "perception", "memory", "planner", "critic",
                "attention_gate", "workspace", "metacog", "ast", "speaker",
                "monologue", "sleep", "telegram_out", "system",
                name="actor_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "stream",
            sa.Enum("external", "conscious", "subconscious", "sleep", name="stream_enum", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "message_in", "tick", "percept", "candidate", "selection",
                "workspace_update", "broadcast", "metacog_report", "belief_revision",
                "attention_prediction", "attention_comparison", "monologue",
                "message_out", "sleep_start", "sleep_digest", "memory_consolidation",
                "sleep_end", "error", "pause", "resume",
                name="event_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("content_json", postgresql.JSONB(), nullable=True),
        sa.Column("model_provider", sa.String(50), nullable=True),
        sa.Column("model_id", sa.String(100), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("parent_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String()), default=[]),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
        sa.ForeignKeyConstraint(["trace_id"], ["traces.trace_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_event_id"], ["events.event_id"], ondelete="SET NULL"),
    )
    op.create_index("ix_events_trace_id", "events", ["trace_id"])
    op.create_index("ix_events_ts", "events", ["ts"])
    op.create_index("ix_events_actor", "events", ["actor"])
    op.create_index("ix_events_stream", "events", ["stream"])
    op.create_index("ix_events_event_type", "events", ["event_type"])
    op.create_index("ix_events_content_json", "events", ["content_json"], postgresql_using="gin")

    # Create memories table
    op.create_table(
        "memories",
        sa.Column("memory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("memory_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("source_trace_ids", postgresql.ARRAY(sa.String()), default=[]),
        sa.Column("relevance_score", sa.Float(), default=1.0),
        sa.Column("access_count", sa.Integer(), default=0),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("memory_id"),
    )
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])
    op.create_index("ix_memories_created_at", "memories", ["created_at"])
    op.create_index("ix_memories_relevance_score", "memories", ["relevance_score"])

    # Create system_state table
    op.create_table(
        "system_state",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )

    # Create ParadeDB BM25 indexes for full-text search
    op.execute("""
        CALL paradedb.create_bm25(
            index_name => 'events_content_bm25',
            table_name => 'events',
            key_field => 'event_id',
            text_fields => paradedb.field('content_text')
        )
    """)

    op.execute("""
        CALL paradedb.create_bm25(
            index_name => 'memories_content_bm25',
            table_name => 'memories',
            key_field => 'memory_id',
            text_fields => paradedb.field('content')
        )
    """)


def downgrade() -> None:
    # Drop BM25 indexes
    op.execute("CALL paradedb.drop_bm25('events_content_bm25')")
    op.execute("CALL paradedb.drop_bm25('memories_content_bm25')")

    # Drop tables
    op.drop_table("system_state")
    op.drop_table("memories")
    op.drop_table("events")
    op.drop_table("traces")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS event_type_enum")
    op.execute("DROP TYPE IF EXISTS actor_enum")
    op.execute("DROP TYPE IF EXISTS stream_enum")
    op.execute("DROP TYPE IF EXISTS input_type_enum")
