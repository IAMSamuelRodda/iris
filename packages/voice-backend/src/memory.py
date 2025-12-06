"""
IRIS Native Memory Module - Python port of memory-service.

Implements SQLite knowledge graph for persistent user memory.
Pattern: Anthropic MCP Memory Server (entities + observations + relations)

Tables:
- memory_entities: Named concepts (person, fleet, ship, location, etc.)
- memory_observations: Facts attached to entities
- memory_relations: Directed edges between entities
- memory_summaries: Cached prose summaries
- conversations: Short-term memory with TTL
"""

import os
import sqlite3
import uuid
import time
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


# Default paths
DEFAULT_DB_PATH = Path.home() / ".config" / "iris" / "memory.db"
CONVERSATION_TTL_MS = 48 * 60 * 60 * 1000  # 48 hours


@dataclass
class Entity:
    """A named concept in the knowledge graph."""
    name: str
    entity_type: str
    observations: list[str] = field(default_factory=list)


@dataclass
class Relation:
    """A directed edge between two entities."""
    from_entity: str
    to_entity: str
    relation_type: str


@dataclass
class KnowledgeGraph:
    """Complete graph structure."""
    entities: list[Entity]
    relations: list[Relation]


@dataclass
class ConversationMessage:
    """A message in conversation history."""
    id: str
    user_id: str
    role: str  # "user" or "assistant"
    content: str
    created_at: int
    expires_at: int


def _now_ms() -> int:
    """Current time in milliseconds."""
    return int(time.time() * 1000)


def _generate_id() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class MemoryDatabase:
    """SQLite database connection manager."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.environ.get("IRIS_DATABASE_PATH") or str(DEFAULT_DB_PATH)

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self):
        """Initialize database schema."""
        conn = self._get_connection()
        try:
            conn.executescript("""
                -- Users table (multi-tenancy)
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    wallet_address TEXT UNIQUE,
                    email TEXT UNIQUE,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_users_wallet ON users(wallet_address);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

                -- Memory entities (Tier 1 - long-term)
                CREATE TABLE IF NOT EXISTS memory_entities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'concept',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mem_ent_user ON memory_entities(user_id);

                -- Memory observations (facts)
                CREATE TABLE IF NOT EXISTS memory_observations (
                    id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    observation TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    is_user_edit INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (entity_id) REFERENCES memory_entities(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_mem_obs_ent ON memory_observations(entity_id);
                CREATE INDEX IF NOT EXISTS idx_mem_obs_user_edit ON memory_observations(is_user_edit);

                -- Memory relations (edges)
                CREATE TABLE IF NOT EXISTS memory_relations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    from_entity_id TEXT NOT NULL,
                    to_entity_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_mem_rel_user ON memory_relations(user_id);

                -- Memory summaries (cached prose)
                CREATE TABLE IF NOT EXISTS memory_summaries (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL UNIQUE,
                    summary TEXT NOT NULL,
                    generated_at INTEGER NOT NULL,
                    entity_count INTEGER NOT NULL DEFAULT 0,
                    observation_count INTEGER NOT NULL DEFAULT 0
                );

                -- Conversations (Tier 2 - short-term with TTL)
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id);
                CREATE INDEX IF NOT EXISTS idx_conv_expires ON conversations(expires_at);
            """)
            conn.commit()
        finally:
            conn.close()


class KnowledgeGraphManager:
    """Manages the knowledge graph for a specific user."""

    def __init__(self, db: MemoryDatabase, user_id: str):
        self.db = db
        self.user_id = user_id

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def create_entities(self, entities: list[dict], is_user_edit: bool = False) -> list[Entity]:
        """Create new entities with optional observations."""
        conn = self.db._get_connection()
        created = []
        now = _now_ms()

        try:
            for entity_data in entities:
                name = entity_data["name"]
                entity_type = entity_data.get("entityType", "concept")
                observations = entity_data.get("observations", [])

                # Check if entity already exists (case-insensitive)
                existing = conn.execute(
                    "SELECT id FROM memory_entities WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                    (self.user_id, name)
                ).fetchone()

                if existing:
                    entity_id = existing["id"]
                else:
                    entity_id = _generate_id()
                    conn.execute(
                        """INSERT INTO memory_entities (id, user_id, name, entity_type, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (entity_id, self.user_id, name, entity_type, now, now)
                    )

                # Add observations
                added_obs = []
                for obs in observations:
                    # Check for duplicate observation
                    dup = conn.execute(
                        "SELECT id FROM memory_observations WHERE entity_id = ? AND LOWER(observation) = LOWER(?)",
                        (entity_id, obs)
                    ).fetchone()

                    if not dup:
                        obs_id = _generate_id()
                        conn.execute(
                            """INSERT INTO memory_observations
                               (id, entity_id, observation, created_at, updated_at, is_user_edit)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (obs_id, entity_id, obs, now, now, 1 if is_user_edit else 0)
                        )
                        added_obs.append(obs)

                created.append(Entity(
                    name=name,
                    entity_type=entity_type,
                    observations=added_obs
                ))

            conn.commit()
        finally:
            conn.close()

        return created

    def delete_entities(self, entity_names: list[str]) -> list[str]:
        """Delete entities by name (cascades to observations and relations)."""
        conn = self.db._get_connection()
        deleted = []

        try:
            for name in entity_names:
                # Find entity
                entity = conn.execute(
                    "SELECT id, name FROM memory_entities WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                    (self.user_id, name)
                ).fetchone()

                if entity:
                    # Delete relations involving this entity
                    conn.execute(
                        """DELETE FROM memory_relations
                           WHERE user_id = ? AND (LOWER(from_entity_id) = LOWER(?) OR LOWER(to_entity_id) = LOWER(?))""",
                        (self.user_id, name, name)
                    )

                    # Delete entity (cascades to observations)
                    conn.execute("DELETE FROM memory_entities WHERE id = ?", (entity["id"],))
                    deleted.append(entity["name"])

            conn.commit()
        finally:
            conn.close()

        return deleted

    # =========================================================================
    # Observation Operations
    # =========================================================================

    def add_observations(self, observations: list[dict], is_user_edit: bool = False) -> list[dict]:
        """Add observations to existing entities."""
        conn = self.db._get_connection()
        results = []
        now = _now_ms()

        try:
            for obs_data in observations:
                entity_name = obs_data["entityName"]
                contents = obs_data["contents"]

                # Find entity
                entity = conn.execute(
                    "SELECT id FROM memory_entities WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                    (self.user_id, entity_name)
                ).fetchone()

                if not entity:
                    results.append({"entityName": entity_name, "added": [], "error": "Entity not found"})
                    continue

                entity_id = entity["id"]
                added = []

                for content in contents:
                    # Check for duplicate
                    dup = conn.execute(
                        "SELECT id FROM memory_observations WHERE entity_id = ? AND LOWER(observation) = LOWER(?)",
                        (entity_id, content)
                    ).fetchone()

                    if not dup:
                        obs_id = _generate_id()
                        conn.execute(
                            """INSERT INTO memory_observations
                               (id, entity_id, observation, created_at, updated_at, is_user_edit)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (obs_id, entity_id, content, now, now, 1 if is_user_edit else 0)
                        )
                        added.append(content)

                # Update entity timestamp
                conn.execute(
                    "UPDATE memory_entities SET updated_at = ? WHERE id = ?",
                    (now, entity_id)
                )

                results.append({"entityName": entity_name, "added": added})

            conn.commit()
        finally:
            conn.close()

        return results

    def delete_observations(self, deletions: list[dict]) -> list[dict]:
        """Delete specific observations from entities."""
        conn = self.db._get_connection()
        results = []

        try:
            for deletion in deletions:
                entity_name = deletion["entityName"]
                obs_to_delete = deletion["observations"]

                # Find entity
                entity = conn.execute(
                    "SELECT id FROM memory_entities WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                    (self.user_id, entity_name)
                ).fetchone()

                if not entity:
                    results.append({"entityName": entity_name, "deleted": []})
                    continue

                entity_id = entity["id"]
                deleted = []

                for obs in obs_to_delete:
                    result = conn.execute(
                        "DELETE FROM memory_observations WHERE entity_id = ? AND LOWER(observation) = LOWER(?)",
                        (entity_id, obs)
                    )
                    if result.rowcount > 0:
                        deleted.append(obs)

                results.append({"entityName": entity_name, "deleted": deleted})

            conn.commit()
        finally:
            conn.close()

        return results

    # =========================================================================
    # Relation Operations
    # =========================================================================

    def create_relations(self, relations: list[dict]) -> list[Relation]:
        """Create directed relationships between entities."""
        conn = self.db._get_connection()
        created = []
        now = _now_ms()

        try:
            for rel_data in relations:
                from_entity = rel_data["from"]
                to_entity = rel_data["to"]
                relation_type = rel_data["relationType"]

                # Check for duplicate
                existing = conn.execute(
                    """SELECT id FROM memory_relations
                       WHERE user_id = ? AND LOWER(from_entity_id) = LOWER(?)
                       AND LOWER(to_entity_id) = LOWER(?) AND LOWER(relation_type) = LOWER(?)""",
                    (self.user_id, from_entity, to_entity, relation_type)
                ).fetchone()

                if not existing:
                    rel_id = _generate_id()
                    conn.execute(
                        """INSERT INTO memory_relations
                           (id, user_id, from_entity_id, to_entity_id, relation_type, created_at)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (rel_id, self.user_id, from_entity, to_entity, relation_type, now)
                    )
                    created.append(Relation(
                        from_entity=from_entity,
                        to_entity=to_entity,
                        relation_type=relation_type
                    ))

            conn.commit()
        finally:
            conn.close()

        return created

    def delete_relations(self, relations: list[dict]) -> list[Relation]:
        """Delete relationships between entities."""
        conn = self.db._get_connection()
        deleted = []

        try:
            for rel_data in relations:
                from_entity = rel_data["from"]
                to_entity = rel_data["to"]
                relation_type = rel_data["relationType"]

                result = conn.execute(
                    """DELETE FROM memory_relations
                       WHERE user_id = ? AND LOWER(from_entity_id) = LOWER(?)
                       AND LOWER(to_entity_id) = LOWER(?) AND LOWER(relation_type) = LOWER(?)""",
                    (self.user_id, from_entity, to_entity, relation_type)
                )

                if result.rowcount > 0:
                    deleted.append(Relation(
                        from_entity=from_entity,
                        to_entity=to_entity,
                        relation_type=relation_type
                    ))

            conn.commit()
        finally:
            conn.close()

        return deleted

    # =========================================================================
    # Query Operations
    # =========================================================================

    def read_graph(self) -> KnowledgeGraph:
        """Read the entire knowledge graph for the user."""
        conn = self.db._get_connection()

        try:
            # Get all entities with observations
            entities_rows = conn.execute(
                "SELECT id, name, entity_type FROM memory_entities WHERE user_id = ?",
                (self.user_id,)
            ).fetchall()

            entities = []
            for row in entities_rows:
                obs_rows = conn.execute(
                    "SELECT observation FROM memory_observations WHERE entity_id = ?",
                    (row["id"],)
                ).fetchall()

                entities.append(Entity(
                    name=row["name"],
                    entity_type=row["entity_type"],
                    observations=[o["observation"] for o in obs_rows]
                ))

            # Get all relations
            rel_rows = conn.execute(
                "SELECT from_entity_id, to_entity_id, relation_type FROM memory_relations WHERE user_id = ?",
                (self.user_id,)
            ).fetchall()

            relations = [
                Relation(
                    from_entity=r["from_entity_id"],
                    to_entity=r["to_entity_id"],
                    relation_type=r["relation_type"]
                )
                for r in rel_rows
            ]

            return KnowledgeGraph(entities=entities, relations=relations)
        finally:
            conn.close()

    def search_nodes(self, query: str, limit: int = 10) -> list[Entity]:
        """Search entities by name or observation content."""
        conn = self.db._get_connection()
        query_lower = query.lower()
        query_words = query_lower.split()

        try:
            # Get all entities for user
            entities_rows = conn.execute(
                "SELECT id, name, entity_type FROM memory_entities WHERE user_id = ?",
                (self.user_id,)
            ).fetchall()

            scored_entities = []

            for row in entities_rows:
                score = 0
                name_lower = row["name"].lower()
                type_lower = row["entity_type"].lower()

                # Get observations
                obs_rows = conn.execute(
                    "SELECT observation FROM memory_observations WHERE entity_id = ?",
                    (row["id"],)
                ).fetchall()
                observations = [o["observation"] for o in obs_rows]
                obs_text = " ".join(observations).lower()

                # Scoring algorithm (matches TypeScript implementation)
                if query_lower in name_lower:
                    score += 10
                if query_lower in type_lower:
                    score += 5
                if query_lower in obs_text:
                    score += 8

                for word in query_words:
                    if word in name_lower:
                        score += 3
                    if word in obs_text:
                        score += 2

                if score > 0:
                    scored_entities.append((score, Entity(
                        name=row["name"],
                        entity_type=row["entity_type"],
                        observations=observations
                    )))

            # Sort by score descending
            scored_entities.sort(key=lambda x: x[0], reverse=True)

            return [e for _, e in scored_entities[:limit]]
        finally:
            conn.close()

    def open_nodes(self, names: list[str]) -> KnowledgeGraph:
        """Get specific entities with their relations."""
        conn = self.db._get_connection()

        try:
            entities = []

            for name in names:
                row = conn.execute(
                    "SELECT id, name, entity_type FROM memory_entities WHERE user_id = ? AND LOWER(name) = LOWER(?)",
                    (self.user_id, name)
                ).fetchone()

                if row:
                    obs_rows = conn.execute(
                        "SELECT observation FROM memory_observations WHERE entity_id = ?",
                        (row["id"],)
                    ).fetchall()

                    entities.append(Entity(
                        name=row["name"],
                        entity_type=row["entity_type"],
                        observations=[o["observation"] for o in obs_rows]
                    ))

            # Get relations touching any of these entities
            entity_names_lower = [n.lower() for n in names]
            placeholders = ",".join("?" * len(entity_names_lower))

            if entity_names_lower:
                rel_rows = conn.execute(
                    f"""SELECT from_entity_id, to_entity_id, relation_type
                        FROM memory_relations
                        WHERE user_id = ? AND (
                            LOWER(from_entity_id) IN ({placeholders}) OR
                            LOWER(to_entity_id) IN ({placeholders})
                        )""",
                    (self.user_id, *entity_names_lower, *entity_names_lower)
                ).fetchall()
            else:
                rel_rows = []

            relations = [
                Relation(
                    from_entity=r["from_entity_id"],
                    to_entity=r["to_entity_id"],
                    relation_type=r["relation_type"]
                )
                for r in rel_rows
            ]

            return KnowledgeGraph(entities=entities, relations=relations)
        finally:
            conn.close()

    # =========================================================================
    # Summary Operations
    # =========================================================================

    def get_summary(self) -> Optional[dict]:
        """Get cached prose summary."""
        conn = self.db._get_connection()

        try:
            row = conn.execute(
                "SELECT summary, generated_at, entity_count, observation_count FROM memory_summaries WHERE user_id = ?",
                (self.user_id,)
            ).fetchone()

            if not row:
                return None

            # Check if stale
            current_entity_count = conn.execute(
                "SELECT COUNT(*) as count FROM memory_entities WHERE user_id = ?",
                (self.user_id,)
            ).fetchone()["count"]

            current_obs_count = conn.execute(
                """SELECT COUNT(*) as count FROM memory_observations mo
                   JOIN memory_entities me ON mo.entity_id = me.id
                   WHERE me.user_id = ?""",
                (self.user_id,)
            ).fetchone()["count"]

            user_edit_count = conn.execute(
                """SELECT COUNT(*) as count FROM memory_observations mo
                   JOIN memory_entities me ON mo.entity_id = me.id
                   WHERE me.user_id = ? AND mo.is_user_edit = 1""",
                (self.user_id,)
            ).fetchone()["count"]

            is_stale = (
                current_entity_count != row["entity_count"] or
                current_obs_count != row["observation_count"]
            )

            return {
                "summary": row["summary"],
                "generatedAt": row["generated_at"],
                "entityCount": row["entity_count"],
                "observationCount": row["observation_count"],
                "isStale": is_stale,
                "userEditCount": user_edit_count
            }
        finally:
            conn.close()

    def save_summary(self, summary: str) -> bool:
        """Save prose summary."""
        if len(summary) < 10:
            return False

        conn = self.db._get_connection()
        now = _now_ms()

        try:
            # Get current counts
            entity_count = conn.execute(
                "SELECT COUNT(*) as count FROM memory_entities WHERE user_id = ?",
                (self.user_id,)
            ).fetchone()["count"]

            obs_count = conn.execute(
                """SELECT COUNT(*) as count FROM memory_observations mo
                   JOIN memory_entities me ON mo.entity_id = me.id
                   WHERE me.user_id = ?""",
                (self.user_id,)
            ).fetchone()["count"]

            # Upsert summary
            conn.execute(
                """INSERT INTO memory_summaries (id, user_id, summary, generated_at, entity_count, observation_count)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                   summary = excluded.summary,
                   generated_at = excluded.generated_at,
                   entity_count = excluded.entity_count,
                   observation_count = excluded.observation_count""",
                (_generate_id(), self.user_id, summary, now, entity_count, obs_count)
            )

            conn.commit()
            return True
        finally:
            conn.close()

    # =========================================================================
    # User Edit Tracking
    # =========================================================================

    def get_user_edits(self) -> list[dict]:
        """Get all user-requested memory edits."""
        conn = self.db._get_connection()

        try:
            rows = conn.execute(
                """SELECT me.name as entity_name, mo.observation, mo.created_at
                   FROM memory_observations mo
                   JOIN memory_entities me ON mo.entity_id = me.id
                   WHERE me.user_id = ? AND mo.is_user_edit = 1
                   ORDER BY mo.created_at DESC""",
                (self.user_id,)
            ).fetchall()

            return [
                {
                    "entityName": r["entity_name"],
                    "observation": r["observation"],
                    "createdAt": r["created_at"]
                }
                for r in rows
            ]
        finally:
            conn.close()


class ConversationManager:
    """Manages conversation history with TTL."""

    def __init__(self, db: MemoryDatabase, user_id: str):
        self.db = db
        self.user_id = user_id

    def add_message(self, role: str, content: str, ttl_ms: int = CONVERSATION_TTL_MS) -> ConversationMessage:
        """Add a message to conversation history."""
        conn = self.db._get_connection()
        now = _now_ms()
        msg_id = _generate_id()
        expires_at = now + ttl_ms

        try:
            conn.execute(
                """INSERT INTO conversations (id, user_id, role, content, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (msg_id, self.user_id, role, content, now, expires_at)
            )
            conn.commit()

            return ConversationMessage(
                id=msg_id,
                user_id=self.user_id,
                role=role,
                content=content,
                created_at=now,
                expires_at=expires_at
            )
        finally:
            conn.close()

    def get_history(self, limit: int = 20) -> list[ConversationMessage]:
        """Get recent conversation history (non-expired only)."""
        conn = self.db._get_connection()
        now = _now_ms()

        try:
            rows = conn.execute(
                """SELECT id, user_id, role, content, created_at, expires_at
                   FROM conversations
                   WHERE user_id = ? AND expires_at > ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (self.user_id, now, limit)
            ).fetchall()

            # Return in chronological order
            messages = [
                ConversationMessage(
                    id=r["id"],
                    user_id=r["user_id"],
                    role=r["role"],
                    content=r["content"],
                    created_at=r["created_at"],
                    expires_at=r["expires_at"]
                )
                for r in reversed(rows)
            ]

            return messages
        finally:
            conn.close()

    def cleanup_expired(self) -> int:
        """Delete expired conversation messages."""
        conn = self.db._get_connection()
        now = _now_ms()

        try:
            result = conn.execute(
                "DELETE FROM conversations WHERE expires_at < ?",
                (now,)
            )
            conn.commit()
            return result.rowcount
        finally:
            conn.close()

    def clear_history(self) -> int:
        """Clear all conversation history for user."""
        conn = self.db._get_connection()

        try:
            result = conn.execute(
                "DELETE FROM conversations WHERE user_id = ?",
                (self.user_id,)
            )
            conn.commit()
            return result.rowcount
        finally:
            conn.close()


# =============================================================================
# Module-level convenience functions
# =============================================================================

_db_instance: Optional[MemoryDatabase] = None


def get_database() -> MemoryDatabase:
    """Get or create the database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = MemoryDatabase()
    return _db_instance


def get_memory_manager(user_id: str = "default") -> KnowledgeGraphManager:
    """Get a knowledge graph manager for the user."""
    return KnowledgeGraphManager(get_database(), user_id)


def get_conversation_manager(user_id: str = "default") -> ConversationManager:
    """Get a conversation manager for the user."""
    return ConversationManager(get_database(), user_id)
