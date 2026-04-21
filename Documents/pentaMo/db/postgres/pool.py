"""PostgreSQL connection pooling (psycopg2-pool)"""

import logging
from typing import Optional
from psycopg2 import pool, sql, extensions
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseConnectionPool:
    """Manages PostgreSQL connections with pooling"""
    
    _instance: Optional['DatabaseConnectionPool'] = None
    _pool: Optional[pool.SimpleConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._pool is None:
            self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            db_url = settings.database_url
            
            # Parse PostgreSQL URL
            # postgres://user:pass@host:port/dbname
            if not db_url.startswith("postgresql://") and not db_url.startswith("postgres://"):
                logger.error(f"Invalid PostgreSQL URL: {db_url}")
                raise ValueError("DATABASE_URL must be a PostgreSQL URL")
            
            # Use SQLAlchemy or directly
            try:
                from sqlalchemy.engine.url import make_url
                parsed_url = make_url(db_url)
                
                self._pool = pool.SimpleConnectionPool(
                    1,  # min connections
                    5,  # max connections
                    host=parsed_url.host,
                    port=parsed_url.port or 5432,
                    database=parsed_url.database,
                    user=parsed_url.username,
                    password=parsed_url.password,
                    connect_timeout=5
                )
                logger.info("✓ PostgreSQL connection pool initialized")
            except ImportError:
                # Fallback: parse manually
                self._pool = pool.SimpleConnectionPool(
                    1, 5,
                    dsn=db_url,
                    connect_timeout=5
                )
                logger.info("✓ PostgreSQL connection pool initialized (manual parsing)")
        
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self._pool = None
    
    def get_connection(self):
        """Get a connection from the pool"""
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        
        try:
            conn = self._pool.getconn()
            conn.autocommit = False
            return conn
        except pool.PoolError as e:
            logger.error(f"Failed to get connection from pool: {e}")
            raise
    
    def put_connection(self, conn):
        """Return a connection to the pool"""
        if self._pool is None:
            return
        
        try:
            if conn:
                conn.rollback()  # Rollback any pending transactions
                self._pool.putconn(conn)
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
    
    def close_all(self):
        """Close all connections in the pool"""
        if self._pool:
            try:
                self._pool.closeall()
                self._pool = None
                logger.info("✓ Connection pool closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")


# Global pool instance
_pool_instance = DatabaseConnectionPool()


def get_connection_pool() -> DatabaseConnectionPool:
    """Get the global connection pool instance"""
    return _pool_instance


def get_db_connection():
    """Context manager for database connections
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT...")
    """
    from contextlib import contextmanager
    
    @contextmanager
    def connection_context():
        conn = _pool_instance.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            _pool_instance.put_connection(conn)
    
    return connection_context()
