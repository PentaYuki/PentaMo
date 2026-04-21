"""PostgreSQL health monitoring"""

import logging
from typing import Dict, Any
from datetime import datetime
from .pool import get_connection_pool

logger = logging.getLogger(__name__)

class DatabaseHealthChecker:
    """Monitor PostgreSQL database health"""
    
    @staticmethod
    def check_connectivity() -> Dict[str, Any]:
        """Check basic PostgreSQL connectivity"""
        try:
            pool = get_connection_pool()
            conn = pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            pool.put_connection(conn)
            
            return {
                "status": "healthy" if result else "degraded",
                "timestamp": datetime.utcnow().isoformat(),
                "message": "PostgreSQL connection successful"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    @staticmethod
    def check_database_size() -> Dict[str, Any]:
        """Check database size"""
        try:
            pool = get_connection_pool()
            conn = pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    pg_size_pretty(pg_database_size(current_database())) as size,
                    (pg_database_size(current_database()) / 1024 / 1024)::int as size_mb
            """)
            result = cursor.fetchone()
            cursor.close()
            pool.put_connection(conn)
            
            return {
                "size_human": result[0] if result else "N/A",
                "size_mb": result[1] if result else 0
            }
        except Exception as e:
            logger.error(f"Failed to check database size: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def check_table_stats() -> Dict[str, Any]:
        """Check row counts per table"""
        try:
            pool = get_connection_pool()
            conn = pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_live_tup as row_count,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """)
            results = cursor.fetchall()
            cursor.close()
            pool.put_connection(conn)
            
            return {
                "tables": [
                    {
                        "name": row[1],
                        "rows": row[2],
                        "size": row[3]
                    }
                    for row in results
                ]
            }
        except Exception as e:
            logger.error(f"Failed to check table stats: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def check_connections() -> Dict[str, Any]:
        """Check active connections"""
        try:
            pool = get_connection_pool()
            conn = pool.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as active,
                    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') as max
                FROM pg_stat_activity
                WHERE state is not null
            """)
            result = cursor.fetchone()
            cursor.close()
            pool.put_connection(conn)
            
            return {
                "active": result[0] if result else 0,
                "max": result[1] if result else 0
            }
        except Exception as e:
            logger.error(f"Failed to check connections: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def full_health_check() -> Dict[str, Any]:
        """Full health check report"""
        return {
            "connectivity": DatabaseHealthChecker.check_connectivity(),
            "database_size": DatabaseHealthChecker.check_database_size(),
            "table_stats": DatabaseHealthChecker.check_table_stats(),
            "connections": DatabaseHealthChecker.check_connections(),
            "timestamp": datetime.utcnow().isoformat()
        }


def check_database_health() -> Dict[str, Any]:
    """Check database health (exported function)"""
    return DatabaseHealthChecker.full_health_check()
