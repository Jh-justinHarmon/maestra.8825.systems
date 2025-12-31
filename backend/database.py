"""Database persistence layer for hosted backend"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations
    
    Handles:
    - Conversation persistence
    - Peer registry persistence
    - Connection pooling
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.database_url = os.getenv("DATABASE_URL")
        
        if not self.database_url:
            logger.warning("DATABASE_URL not set, persistence disabled")
    
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        if not self.database_url:
            logger.warning("Cannot initialize database: DATABASE_URL not set")
            return
        
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            logger.info("✓ Database connection pool created")
            
            # Create tables
            await self._create_tables()
            
            logger.info("✓ Database initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("✓ Database connection pool closed")
    
    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self.pool.acquire() as conn:
            # Conversations table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id VARCHAR(255) PRIMARY KEY,
                    title TEXT,
                    surface VARCHAR(50),
                    messages JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)
            
            # Peer registry table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS peer_registry (
                    backend_id VARCHAR(255) PRIMARY KEY,
                    sbt JSONB,
                    public_key TEXT,
                    capabilities JSONB,
                    registered_at TIMESTAMP,
                    last_sync_at TIMESTAMP
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_updated_at 
                ON conversations(updated_at DESC)
            """)
            
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_peer_registry_last_sync 
                ON peer_registry(last_sync_at DESC)
            """)
            
            logger.info("✓ Database tables created")
    
    # Conversation operations
    
    async def save_conversation(self, conversation: Dict[str, Any]) -> bool:
        """
        Save or update a conversation
        
        Args:
            conversation: Conversation data dictionary
            
        Returns:
            True if successful
        """
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO conversations 
                    (conversation_id, title, surface, messages, metadata, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (conversation_id) 
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        messages = EXCLUDED.messages,
                        metadata = EXCLUDED.metadata,
                        updated_at = EXCLUDED.updated_at
                """,
                    conversation['conversation_id'],
                    conversation.get('title', ''),
                    conversation.get('surface', 'unknown'),
                    json.dumps(conversation.get('messages', [])),
                    json.dumps(conversation.get('metadata', {})),
                    datetime.fromisoformat(conversation.get('created_at', datetime.utcnow().isoformat())),
                    datetime.fromisoformat(conversation.get('updated_at', datetime.utcnow().isoformat()))
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
            return False
    
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Conversation data or None
        """
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM conversations WHERE conversation_id = $1
                """, conversation_id)
                
                if not row:
                    return None
                
                return {
                    'conversation_id': row['conversation_id'],
                    'title': row['title'],
                    'surface': row['surface'],
                    'messages': json.loads(row['messages']),
                    'metadata': json.loads(row['metadata']),
                    'created_at': row['created_at'].isoformat(),
                    'updated_at': row['updated_at'].isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None
    
    async def list_conversations(self, limit: int = 100) -> List[str]:
        """
        List conversation IDs
        
        Args:
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation IDs
        """
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT conversation_id FROM conversations 
                    ORDER BY updated_at DESC 
                    LIMIT $1
                """, limit)
                
                return [row['conversation_id'] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []
    
    # Peer registry operations
    
    async def register_peer(
        self,
        backend_id: str,
        sbt: Dict[str, Any],
        public_key: str,
        capabilities: List[str]
    ) -> bool:
        """
        Register a peer backend
        
        Args:
            backend_id: Peer's backend ID
            sbt: Session Binding Token
            public_key: Peer's public key
            capabilities: Peer's capabilities
            
        Returns:
            True if successful
        """
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO peer_registry 
                    (backend_id, sbt, public_key, capabilities, registered_at, last_sync_at)
                    VALUES ($1, $2, $3, $4, $5, $5)
                    ON CONFLICT (backend_id) 
                    DO UPDATE SET
                        sbt = EXCLUDED.sbt,
                        public_key = EXCLUDED.public_key,
                        capabilities = EXCLUDED.capabilities,
                        registered_at = EXCLUDED.registered_at
                """,
                    backend_id,
                    json.dumps(sbt),
                    public_key,
                    json.dumps(capabilities),
                    datetime.utcnow()
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register peer: {e}")
            return False
    
    async def get_peer(self, backend_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a peer by backend ID
        
        Args:
            backend_id: Peer's backend ID
            
        Returns:
            Peer data or None
        """
        if not self.pool:
            return None
        
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM peer_registry WHERE backend_id = $1
                """, backend_id)
                
                if not row:
                    return None
                
                return {
                    'backend_id': row['backend_id'],
                    'sbt': json.loads(row['sbt']),
                    'public_key': row['public_key'],
                    'capabilities': json.loads(row['capabilities']),
                    'registered_at': row['registered_at'].isoformat(),
                    'last_sync_at': row['last_sync_at'].isoformat() if row['last_sync_at'] else None
                }
                
        except Exception as e:
            logger.error(f"Failed to get peer: {e}")
            return None
    
    async def list_peers(self) -> List[Dict[str, Any]]:
        """
        List all registered peers
        
        Returns:
            List of peer data
        """
        if not self.pool:
            return []
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT * FROM peer_registry 
                    ORDER BY registered_at DESC
                """)
                
                return [
                    {
                        'backend_id': row['backend_id'],
                        'sbt': json.loads(row['sbt']),
                        'public_key': row['public_key'],
                        'capabilities': json.loads(row['capabilities']),
                        'registered_at': row['registered_at'].isoformat()
                    }
                    for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Failed to list peers: {e}")
            return []
    
    async def update_peer_sync_time(self, backend_id: str) -> bool:
        """
        Update last sync time for a peer
        
        Args:
            backend_id: Peer's backend ID
            
        Returns:
            True if successful
        """
        if not self.pool:
            return False
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE peer_registry 
                    SET last_sync_at = $1 
                    WHERE backend_id = $2
                """, datetime.utcnow(), backend_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update peer sync time: {e}")
            return False


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager
