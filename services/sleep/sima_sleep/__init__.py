"""
SIMA Sleep Consolidation Service.

This service handles memory consolidation during "sleep" cycles:
- Compacts traces into digests (L1)
- Extracts stable semantic memories
- Maintains L3 core memories (genesis.md, stable beliefs)
- Posts sleep telemetry to Telegram
"""

__version__ = "0.1.0"
