import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import create_tables
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("Running manual database migration...")
    try:
        create_tables()
        logger.info("✓ Migration completed successfully.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
