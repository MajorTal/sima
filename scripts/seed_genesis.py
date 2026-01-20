#!/usr/bin/env python3
"""
Seed the genesis memory (L3 core identity) for Sima.

This script reads docs/genesis.md and inserts it as an L3 core memory.
Run this after a system reset to restore Sima's identity.
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add packages to path
root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "packages" / "sima-core"))
sys.path.insert(0, str(root / "packages" / "sima-storage"))

from sima_storage.database import get_session, init_db
from sima_storage.repository import MemoryRepository


async def seed_genesis():
    """Seed the genesis memory."""
    print("Seeding genesis memory...")

    # Read genesis.md
    genesis_path = root / "docs" / "genesis.md"
    if not genesis_path.exists():
        print(f"Error: {genesis_path} not found")
        sys.exit(1)

    genesis_content = genesis_path.read_text()
    print(f"Read genesis content: {len(genesis_content)} characters")

    await init_db()

    async with get_session() as session:
        repo = MemoryRepository(session)

        # Check if genesis memory already exists
        existing = await repo.list_by_type("l3_genesis", limit=1)
        if existing:
            print("Genesis memory already exists, skipping.")
            return

        # Create genesis memory
        memory_id = uuid4()
        await repo.create(
            memory_id=memory_id,
            memory_type="l3_genesis",
            content=genesis_content,
            metadata_json={
                "source": "docs/genesis.md",
                "category": "core_identity",
                "immutable": True,
            },
            source_trace_ids=[],
        )

        await session.commit()

        print(f"Genesis memory created: {memory_id}")
        print("  Type: l3_genesis (L3 core identity)")
        print("  Source: docs/genesis.md")


if __name__ == "__main__":
    asyncio.run(seed_genesis())
