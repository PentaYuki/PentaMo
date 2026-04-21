"""
Cleanup FAISS - v3 Optimization
Finds and removes duplicate entries from FAISS indexes and rebuilds them.
"""

import sys
import os
from pathlib import Path

# Add root folder to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from services.faiss_memory import get_faiss_memory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_index(index_name: str):
    logger.info(f"Cleaning up FAISS index: {index_name}")
    memory = get_faiss_memory(index_name=index_name)
    
    total_before = len(memory.metadata)
    if total_before == 0:
        logger.info(f"Index {index_name} is empty. Skipping.")
        return

    # 1. Identify duplicates based on query text
    seen_queries = set()
    unique_metadata = []
    
    for item in memory.metadata:
        query = item.get("text", "").strip().lower()
        if query and query not in seen_queries:
            seen_queries.add(query)
            unique_metadata.append(item)
    
    total_after = len(unique_metadata)
    
    if total_after < total_before:
        logger.info(f"Removing {total_before - total_after} duplicate entries.")
        
        # 2. Rebuild index
        # We need to re-encode all unique texts
        import faiss # type: ignore
        import numpy as np
        
        # Reset memory object state
        memory.metadata = unique_metadata
        memory.index = faiss.IndexFlatL2(memory.dimension)
        
        # Re-add entries
        # (Using a simplified approach here, normally we'd batch encode)
        texts = [m["text"] for m in unique_metadata]
        if texts:
            embeddings = memory.model.encode(texts)
            memory.index.add(np.array(embeddings).astype('float32'))
            
        # 3. Save
        memory.save()
        logger.info(f"Index {index_name} cleaned and saved. (Total: {total_after})")
    else:
        logger.info(f"No duplicates found in {index_name}.")

if __name__ == "__main__":
    # Cleanup typical indexes
    cleanup_index("main")
    cleanup_index("mode_classifier")
