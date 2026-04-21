"""
Embeddings Model - Sentence Transformers
Multilingual support for Vietnamese conversations
"""

import logging
from typing import List, Union, Optional
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingsModel:
    """Wrapper for sentence-transformers embeddings"""
    
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
        """
        Initialize embeddings model
        
        Args:
            model_name: HuggingFace model identifier
                - paraphrase-multilingual-mpnet-base-v2: 768-dim, multilingual
                - all-mpnet-base-v2: 768-dim, English
                - all-MiniLM-L6-v2: 384-dim, lightweight
        """
        self.model_name = model_name
        self.embedding_dim = 768  # Default for mpnet models
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the embeddings model"""
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Detect device (M1/M2 optimization)
            device = "mps" if torch.backends.mps.is_available() else "cpu"
            
            logger.info(f"Loading embeddings model: {self.model_name} on {device}")
            self.model = SentenceTransformer(self.model_name, device=device)
            logger.info(f"✓ Embeddings model loaded ({self.embedding_dim}-dim vectors)")
        
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load embeddings model: {e}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create embedding for single text
        
        Args:
            text: Input text (Vietnamese or English)
        
        Returns:
            Vector as list of floats
        """
        if not self.model:
            raise RuntimeError("Embeddings model not initialized")
        
        try:
            embeddings = self.model.encode([text], convert_to_tensor=False)
            return embeddings[0].tolist()
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Create embeddings for multiple texts
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
        
        Returns:
            List of vectors as lists of floats
        """
        if not self.model:
            raise RuntimeError("Embeddings model not initialized")
        
        try:
            embeddings = self.model.encode(texts, batch_size=batch_size, convert_to_tensor=False)
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"Failed to embed texts: {e}")
            raise
    
    def embed_conversation(self, messages: List[dict]) -> List[float]:
        """
        Create embedding for full conversation (summary)
        
        Args:
            messages: List of message dicts with 'role' and 'content'
        
        Returns:
            Vector representing entire conversation
        """
        # Create conversation summary text
        conversation_text = "\n".join([
            f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
            for msg in messages
        ])
        
        return self.embed_text(conversation_text)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Args:
            embedding1: First vector
            embedding2: Second vector
        
        Returns:
            Similarity score (0-1)
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            emb1 = np.array(embedding1).reshape(1, -1)
            emb2 = np.array(embedding2).reshape(1, -1)
            
            return float(cosine_similarity(emb1, emb2)[0][0])
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def batch_similarity(self, embedding: List[float], embeddings: List[List[float]]) -> List[float]:
        """
        Calculate similarity between one embedding and many
        
        Args:
            embedding: Query vector
            embeddings: List of vectors to compare
        
        Returns:
            List of similarity scores
        """
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            query = np.array(embedding).reshape(1, -1)
            targets = np.array(embeddings)
            
            similarities = cosine_similarity(query, targets)[0]
            return [float(s) for s in similarities]
        except Exception as e:
            logger.error(f"Failed to calculate batch similarity: {e}")
            return [0.0] * len(embeddings)


# Global embeddings model instance
embeddings_model = None


def get_embeddings_model() -> EmbeddingsModel:
    """Get or initialize global embeddings model"""
    global embeddings_model
    
    if embeddings_model is None:
        try:
            embeddings_model = EmbeddingsModel()
        except Exception as e:
            logger.error(f"Failed to initialize embeddings model: {e}")
            # Continue without embeddings (graceful degradation)
            return None
    
    return embeddings_model


def initialize_embeddings(model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"):
    """Initialize embeddings model with custom name"""
    global embeddings_model
    embeddings_model = EmbeddingsModel(model_name)
    return embeddings_model
