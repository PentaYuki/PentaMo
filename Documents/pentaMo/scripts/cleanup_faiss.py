"""
cleanup_faiss.py — FAISS Index Maintenance (v2)

What it does:
  1. Removes duplicate entries (keyed by question string, case-insensitive)
  2. Rebuilds the cosine index (IndexFlatIP) from scratch using batch encoding
  3. Reports stats before and after

Usage:
    python scripts/cleanup_faiss.py [index_name ...]
    python scripts/cleanup_faiss.py             # defaults: main + mode_classifier
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.faiss_memory import get_faiss_memory

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("cleanup_faiss")


def cleanup_index(index_name: str) -> None:
    logger.info(f"{'─'*50}")
    logger.info(f"  Cleaning index: '{index_name}'")
    memory = get_faiss_memory(index_name=index_name)

    before = len(memory.metadata)
    logger.info(f"  Records before: {before}")

    if before == 0:
        logger.info("  Index is empty — nothing to do.")
        return

    removed = memory.rebuild_dedup()

    after = len(memory.metadata)
    logger.info(f"  Duplicates removed : {removed}")
    logger.info(f"  Records after      : {after}")

    stats = memory.get_stats()
    logger.info(
        f"  Breakdown — consultant: {stats['consultant_count']}, "
        f"trader: {stats['trader_count']}"
    )


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else ["main", "mode_classifier"]
    for name in targets:
        cleanup_index(name)
    logger.info("✓ FAISS cleanup done.")
