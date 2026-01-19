"""
Memory Tiering System.

Implements the three-tier memory architecture:
- L0: Raw event log (already in DB, not managed here)
- L1: Per-trace digests (created during sleep)
- L2: Weekly topic maps (aggregated from L1)
- L3: Core memories (genesis.md, stable beliefs) - always in context
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from sima_storage.models import MemoryModel
from sima_storage.repository import MemoryRepository

logger = logging.getLogger(__name__)


# Memory type constants
class MemoryType:
    """Constants for memory types."""
    L1_TRACE_DIGEST = "l1_trace_digest"
    L2_TOPIC_MAP = "l2_topic_map"
    L3_CORE = "l3_core"
    L3_GENESIS = "l3_genesis"
    SEMANTIC = "semantic"


@dataclass
class L1TraceDigest:
    """A digest of a single trace (L1 memory)."""
    trace_id: str
    topic: str
    digest: str
    timestamp: datetime
    source_event_ids: list[str]


@dataclass
class SemanticMemory:
    """A semantic memory entry extracted from traces."""
    claim: str
    confidence: float
    provenance_event_ids: list[str]


@dataclass
class L3CoreMemory:
    """Core memory that is always available in context."""
    name: str
    content: str
    memory_type: str  # l3_genesis or l3_core


class MemoryTierManager:
    """
    Manages the memory tiering system.

    Responsibilities:
    - Create L1 trace digests during sleep
    - Aggregate L1 into L2 topic maps (weekly)
    - Load and persist L3 core memories
    - Surface memories for retrieval by memory module
    """

    def __init__(self, session: AsyncSession, genesis_path: str | Path | None = None):
        """
        Initialize the memory tier manager.

        Args:
            session: Database session.
            genesis_path: Path to genesis.md file. If None, uses default location.
        """
        self.session = session
        self.repo = MemoryRepository(session)

        if genesis_path is None:
            # Default: project_root/docs/genesis.md
            project_root = Path(__file__).parent.parent.parent.parent
            genesis_path = project_root / "docs" / "genesis.md"

        self.genesis_path = Path(genesis_path)
        self._genesis_content: str | None = None

    def load_genesis(self) -> str:
        """
        Load genesis.md content.

        Returns:
            The content of genesis.md.

        Raises:
            FileNotFoundError: If genesis.md doesn't exist.
        """
        if self._genesis_content is not None:
            return self._genesis_content

        if not self.genesis_path.exists():
            raise FileNotFoundError(f"Genesis file not found: {self.genesis_path}")

        with open(self.genesis_path, "r", encoding="utf-8") as f:
            self._genesis_content = f.read()

        logger.info(f"Loaded genesis.md from {self.genesis_path}")
        return self._genesis_content

    async def ensure_genesis_in_db(self) -> MemoryModel:
        """
        Ensure genesis.md is stored as L3 memory in the database.

        Creates or updates the genesis memory entry.

        Returns:
            The genesis memory model.
        """
        content = self.load_genesis()

        # Check if genesis already exists
        existing = await self.repo.list_by_type(MemoryType.L3_GENESIS, limit=1)

        if existing:
            # Genesis exists, check if content changed
            genesis = existing[0]
            if genesis.content != content:
                # Update content
                genesis.content = content
                await self.session.flush()
                logger.info("Updated genesis.md in database")
            return genesis

        # Create new genesis entry
        genesis = await self.repo.create(
            memory_id=uuid4(),
            memory_type=MemoryType.L3_GENESIS,
            content=content,
            metadata_json={"name": "genesis", "source": str(self.genesis_path)},
        )
        logger.info("Created genesis.md in database")
        return genesis

    async def get_l3_memories(self) -> list[L3CoreMemory]:
        """
        Get all L3 core memories.

        Returns:
            List of core memories (genesis + any stable beliefs).
        """
        memories = []

        # Get genesis
        genesis_list = await self.repo.list_by_type(MemoryType.L3_GENESIS, limit=1)
        if genesis_list:
            genesis = genesis_list[0]
            memories.append(L3CoreMemory(
                name="genesis",
                content=genesis.content,
                memory_type=MemoryType.L3_GENESIS,
            ))

        # Get other L3 core memories (stable beliefs)
        core_list = await self.repo.list_by_type(MemoryType.L3_CORE, limit=50)
        for mem in core_list:
            name = mem.metadata_json.get("name", "core") if mem.metadata_json else "core"
            memories.append(L3CoreMemory(
                name=name,
                content=mem.content,
                memory_type=MemoryType.L3_CORE,
            ))

        return memories

    async def create_l1_digest(
        self,
        trace_id: str,
        topic: str,
        digest: str,
        source_event_ids: list[str],
    ) -> MemoryModel:
        """
        Create an L1 trace digest.

        Args:
            trace_id: ID of the trace being digested.
            topic: Topic/theme of the trace.
            digest: Summary of the trace.
            source_event_ids: Event IDs that contributed to this digest.

        Returns:
            The created memory model.
        """
        return await self.repo.create(
            memory_id=uuid4(),
            memory_type=MemoryType.L1_TRACE_DIGEST,
            content=digest,
            metadata_json={
                "trace_id": trace_id,
                "topic": topic,
            },
            source_trace_ids=[trace_id],
        )

    async def create_semantic_memory(
        self,
        claim: str,
        confidence: float,
        provenance_event_ids: list[str],
        source_trace_ids: list[str],
    ) -> MemoryModel:
        """
        Create a semantic memory entry.

        Args:
            claim: The claim/fact being stored.
            confidence: Confidence level (0-1).
            provenance_event_ids: Events that support this claim.
            source_trace_ids: Traces that contributed to this memory.

        Returns:
            The created memory model.
        """
        return await self.repo.create(
            memory_id=uuid4(),
            memory_type=MemoryType.SEMANTIC,
            content=claim,
            metadata_json={
                "confidence": confidence,
                "provenance_event_ids": provenance_event_ids,
            },
            source_trace_ids=source_trace_ids,
        )

    async def get_semantic_memories(
        self,
        limit: int = 50,
    ) -> Sequence[MemoryModel]:
        """
        Get semantic memories ordered by relevance.

        Args:
            limit: Maximum number of memories to return.

        Returns:
            List of semantic memory models.
        """
        return await self.repo.list_by_type(MemoryType.SEMANTIC, limit=limit)

    async def search_memories(
        self,
        query: str,
        limit: int = 10,
    ) -> Sequence[MemoryModel]:
        """
        Search memories by content.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            Matching memories.
        """
        return await self.repo.search(query, limit=limit)

    async def promote_to_l3(
        self,
        claim: str,
        name: str,
    ) -> MemoryModel:
        """
        Promote a stable belief to L3 core memory.

        This is called when a semantic memory has been consistently reinforced
        and should become part of Sima's core identity/beliefs.

        Args:
            claim: The belief to promote.
            name: Name for the core memory.

        Returns:
            The created L3 memory.
        """
        return await self.repo.create(
            memory_id=uuid4(),
            memory_type=MemoryType.L3_CORE,
            content=claim,
            metadata_json={"name": name, "promoted_at": datetime.utcnow().isoformat()},
        )

    def format_l3_for_context(self, memories: list[L3CoreMemory]) -> str:
        """
        Format L3 memories for inclusion in LLM context.

        Args:
            memories: List of L3 memories.

        Returns:
            Formatted string for context injection.
        """
        if not memories:
            return ""

        sections = []
        for mem in memories:
            if mem.memory_type == MemoryType.L3_GENESIS:
                sections.append(f"=== GENESIS ===\n{mem.content}")
            else:
                sections.append(f"=== Core Belief: {mem.name} ===\n{mem.content}")

        return "\n\n".join(sections)

    def format_semantic_for_context(self, memories: Sequence[MemoryModel]) -> str:
        """
        Format semantic memories for inclusion in LLM context.

        Args:
            memories: List of semantic memory models.

        Returns:
            Formatted string for context injection.
        """
        if not memories:
            return "No semantic memories yet."

        lines = []
        for mem in memories:
            confidence = mem.metadata_json.get("confidence", 1.0) if mem.metadata_json else 1.0
            lines.append(f"- [{confidence:.2f}] {mem.content}")

        return "Semantic Memories:\n" + "\n".join(lines)
