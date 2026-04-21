"""
FAISS Memory Service
Lưu trữ các cặp (câu hỏi → câu trả lời) dùng FAISS để truy xuất nhanh
Hỗ trợ hai chế độ: consultant (tư vấn viên) và trader (phân tích buôn bán)
"""

import faiss
import numpy as np
import pickle
import os
import logging
from datetime import datetime
from sentence_transformers import SentenceTransformer
from typing import List, Tuple, Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class FAISSMemory:
    def __init__(self, index_name="main", index_dir="data/faiss", dim=384):
        """
        Initialize FAISS memory service
        
        Args:
            index_name: Name of the index (e.g., "main", "mode_classifier")
            index_dir: Directory to store FAISS index and metadata
            dim: Dimension of embeddings (paraphrase-multilingual-MiniLM-L12-v2 uses 384)
        """
        self.dim = dim
        self.index_name = index_name
        self.index_dir = index_dir
        self.index_path = os.path.join(index_dir, f"{index_name}_index")
        self.meta_path = os.path.join(index_dir, f"{index_name}_metadata.pkl")
        
        # Create directory if not exists
        Path(index_dir).mkdir(parents=True, exist_ok=True)
        
        # Load or initialize embedding model
        # SentenceTransformer is heavy, only load if not already loaded globally
        self.model = self._get_model()
        
        self.index = None
        self.metadata = []  # list of dict: {"question": str, "answer": str, "mode": str}
        self.last_updated = None
        
        self._load_or_create()
        logger.info(f"FAISS memory '{index_name}' initialized. Size: {self.index.ntotal}")

    _shared_model = None
    
    @classmethod
    def _get_model(cls):
        if cls._shared_model is None:
            logger.info("Loading sentence transformer model (shared)...")
            model_name = 'paraphrase-multilingual-MiniLM-L12-v2'
            
            # Try to find absolute path in HuggingFace cache to bypass network checks perfectly
            cache_base = Path.home() / ".cache" / "huggingface" / "hub"
            model_cache_prefix = "models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2"
            model_cache_dir = cache_base / model_cache_prefix / "snapshots"
            
            absolute_path = None
            if model_cache_dir.exists():
                snapshots = sorted(list(model_cache_dir.iterdir()), key=lambda x: x.stat().st_mtime, reverse=True)
                if snapshots:
                    absolute_path = str(snapshots[0])
            
            try:
                if absolute_path:
                    logger.info(f"✓ Found local cache at: {absolute_path}")
                    cls._shared_model = SentenceTransformer(absolute_path)
                else:
                    # Fallback to name if cache not found in expected structure
                    cls._shared_model = SentenceTransformer(model_name)
                logger.info("✓ Model loaded successfully.")
            except Exception as e:
                logger.error(f"🛑 CRITICAL: Could not load embedding model: {e}")
                raise e
        return cls._shared_model
    
    def _load_or_create(self):
        """Load existing FAISS index or create new one"""
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                logger.info(f"Loading FAISS index from {self.index_path}")
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        self.metadata = data.get("metadata", [])
                        self.last_updated = data.get("last_updated")
                    else:
                        self.metadata = data
                logger.info(f"Loaded {len(self.metadata)} metadata records for '{self.index_name}'")
            except Exception as e:
                logger.error(f"Error loading FAISS index '{self.index_name}': {e}. Creating new one...")
                self.index = faiss.IndexFlatL2(self.dim)
                self.metadata = []
        else:
            logger.info(f"Creating new FAISS index '{self.index_name}'")
            self.index = faiss.IndexFlatL2(self.dim)
            self.metadata = []
    
    def add(self, question: str, answer: str, mode: str, metadata_extra: Dict = None) -> None:
        """
        Add a question-answer pair or labeled sample to FAISS index
        """
        try:
            # Generate embedding for question
            emb = self.model.encode([question])[0].astype(np.float32)
            
            # Add to FAISS index
            self.index.add(np.array([emb]))
            
            # Store metadata
            record = {
                "question": question.strip(),
                "answer": answer.strip(),
                "mode": mode
            }
            if metadata_extra:
                record.update(metadata_extra)
                
            self.metadata.append(record)
            self.last_updated = datetime.now().isoformat()
            
            # Save to disk
            self._save()
            logger.debug(f"Added to FAISS '{self.index_name}': {mode} - Q: {question[:50]}...")
        except Exception as e:
            logger.error(f"Error adding to FAISS '{self.index_name}': {e}")
    
    def search(self, question: str, mode: str = None, k: int = 3, threshold: float = 0.7) -> Optional[str]:
        """
        Search for similar question in FAISS index and return the answer
        """
        results = self.search_metadata(question, k=k, threshold=threshold)
        
        for meta, similarity in results:
            # If mode is provided, filter by mode
            if mode and meta.get("mode") != mode:
                continue
            
            logger.info(
                f"FAISS '{self.index_name}' HIT: similarity={similarity:.3f}, "
                f"Q: {question[:40]}... → cached answer"
            )
            return meta["answer"]
            
        return None

    def search_metadata(self, question: str, k: int = 3, threshold: float = 0.7) -> List[Tuple[Dict, float]]:
        """
        Search for similar question in FAISS index and return metadata records
        
        Returns:
            List of (metadata_dict, similarity_score)
        """
        if self.index.ntotal == 0:
            return []
        
        try:
            # Generate embedding
            emb = self.model.encode([question])[0].astype(np.float32)
            
            # Search in FAISS
            D, I = self.index.search(np.array([emb]), min(k, self.index.ntotal))
            
            results = []
            distance_threshold = 2 * (1 - threshold)
            
            for i, idx in enumerate(I[0]):
                if idx == -1: continue
                
                distance = D[0][i]
                similarity = 1 - (distance / 2)
                
                if distance <= distance_threshold:
                    results.append((self.metadata[idx], similarity))
            
            return results
        except Exception as e:
            logger.error(f"Error searching FAISS '{self.index_name}': {e}")
            return []
    
    def get_stats(self) -> Dict[str, any]:
        """Get statistics about the index"""
        return {
            "index_name": self.index_name,
            "total_pairs": self.index.ntotal,
            "metadata_count": len(self.metadata),
            "consultant_count": sum(1 for m in self.metadata if m.get("mode") == "consultant"),
            "trader_count": sum(1 for m in self.metadata if m.get("mode") == "trader"),
            "last_updated": self.last_updated,
            "recent_learning": [
                {"q": m["question"][:60], "mode": m["mode"], "time": m.get("learned_at", "N/A")} 
                for m in self.metadata[-5:]
            ][::-1]
        }
    
    def _save(self):
        """Save FAISS index and metadata to disk"""
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "wb") as f:
                pickle.dump({
                    "metadata": self.metadata,
                    "last_updated": self.last_updated
                }, f)
            logger.debug(f"Saved FAISS index '{self.index_name}' to {self.index_path}")
        except Exception as e:
            logger.error(f"Error saving FAISS '{self.index_name}': {e}")


# Singleton instances
_instances = {}

def get_faiss_memory(index_name="main") -> FAISSMemory:
    """Get or create FAISS memory singleton for a specific index"""
    global _instances
    if index_name not in _instances:
        _instances[index_name] = FAISSMemory(index_name=index_name)
    return _instances[index_name]
