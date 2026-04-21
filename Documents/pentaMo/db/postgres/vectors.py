"""
PostgreSQL pgvector operations for similarity search
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class VectorStore:
    """Manage vector embeddings in PostgreSQL with pgvector"""
    
    @staticmethod
    def create_vector_table(db: Session):
        """Create embeddings table with pgvector support"""
        try:
            # Create extension if not exists
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create embeddings table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id VARCHAR(36) PRIMARY KEY,
                    conversation_id VARCHAR(36),
                    type VARCHAR(50),  -- 'message', 'summary', 'fraud_pattern'
                    content TEXT,
                    embedding vector(768),  -- 768-dim for mpnet
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
            """))
            
            # Create index for fast similarity search (HNSW)
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS embeddings_vector_idx 
                ON embeddings USING hnsw (embedding vector_cosine_ops);
            """))
            
            # Create index on conversation_id for filtering
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS embeddings_conversation_idx 
                ON embeddings(conversation_id);
            """))
            
            db.commit()
            logger.info("✓ Vector embeddings table created")
        except Exception as e:
            logger.warning(f"Vector table setup: {e} (may already exist)")
            db.rollback()
    
    @staticmethod
    def store_embedding(
        db: Session,
        conversation_id: str,
        embedding_type: str,
        content: str,
        vector: List[float]
    ) -> str:
        """
        Store embedding in PostgreSQL
        
        Args:
            db: Database session
            conversation_id: Associated conversation
            embedding_type: 'message', 'summary', or 'fraud_pattern'
            content: Original text
            vector: Embedding vector (768-dim)
        
        Returns:
            Embedding ID
        """
        try:
            embedding_id = str(uuid.uuid4())
            
            # Format vector as PostgreSQL array
            vector_str = "[" + ",".join([str(v) for v in vector]) + "]"
            
            db.execute(text(f"""
                INSERT INTO embeddings (id, conversation_id, type, content, embedding, created_at)
                VALUES (:id, :conv_id, :type, :content, :embedding, :created_at)
            """), {
                "id": embedding_id,
                "conv_id": conversation_id,
                "type": embedding_type,
                "content": content,
                "embedding": vector_str,
                "created_at": datetime.utcnow()
            })
            
            db.commit()
            logger.info(f"Stored embedding {embedding_id} for conversation {conversation_id}")
            return embedding_id
        
        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            db.rollback()
            raise
    
    @staticmethod
    def search_similar(
        db: Session,
        query_vector: List[float],
        limit: int = 5,
        threshold: float = 0.5,
        conversation_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar embeddings using cosine distance
        
        Args:
            db: Database session
            query_vector: Query embedding (768-dim)
            limit: Max results
            threshold: Minimum similarity score (0-1)
            conversation_id: Optional filter by conversation
        
        Returns:
            List of similar embeddings with scores
        """
        try:
            # Format vector as PostgreSQL array
            vector_str = "[" + ",".join([str(v) for v in query_vector]) + "]"
            
            # Build query
            query = """
                SELECT 
                    id,
                    conversation_id,
                    type,
                    content,
                    created_at,
                    1 - (embedding <-> :vector::vector) as similarity_score
                FROM embeddings
            """
            
            params = {"vector": vector_str}
            
            if conversation_id:
                query += " WHERE conversation_id = :conv_id"
                params["conv_id"] = conversation_id
            
            query += f"""
                AND (1 - (embedding <-> :vector::vector)) >= :threshold
                ORDER BY embedding <-> :vector::vector
                LIMIT :limit
            """
            
            params["threshold"] = threshold
            params["limit"] = limit
            
            results = db.execute(text(query), params).fetchall()
            
            return [
                {
                    "id": row[0],
                    "conversation_id": row[1],
                    "type": row[2],
                    "content": row[3],
                    "created_at": row[4].isoformat() if row[4] else None,
                    "similarity": float(row[5])
                }
                for row in results
            ]
        
        except Exception as e:
            logger.error(f"Failed to search embeddings: {e}")
            return []
    
    @staticmethod
    def search_conversation_embeddings(
        db: Session,
        conversation_id: str,
        embedding_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get all embeddings for a specific conversation"""
        try:
            query = "SELECT id, type, content, created_at FROM embeddings WHERE conversation_id = :conv_id"
            params = {"conv_id": conversation_id}
            
            if embedding_type:
                query += " AND type = :type"
                params["type"] = embedding_type
            
            query += " ORDER BY created_at DESC LIMIT :limit"
            params["limit"] = limit
            
            results = db.execute(text(query), params).fetchall()
            
            return [
                {
                    "id": row[0],
                    "type": row[1],
                    "content": row[2],
                    "created_at": row[3].isoformat() if row[3] else None
                }
                for row in results
            ]
        
        except Exception as e:
            logger.error(f"Failed to get conversation embeddings: {e}")
            return []
    
    @staticmethod
    def delete_embedding(db: Session, embedding_id: str) -> bool:
        """Delete an embedding"""
        try:
            db.execute(text("DELETE FROM embeddings WHERE id = :id"), {"id": embedding_id})
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete embedding: {e}")
            db.rollback()
            return False
    
    @staticmethod
    def delete_conversation_embeddings(db: Session, conversation_id: str) -> bool:
        """Delete all embeddings for a conversation"""
        try:
            db.execute(
                text("DELETE FROM embeddings WHERE conversation_id = :conv_id"),
                {"conv_id": conversation_id}
            )
            db.commit()
            logger.info(f"Deleted embeddings for conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation embeddings: {e}")
            db.rollback()
            return False
