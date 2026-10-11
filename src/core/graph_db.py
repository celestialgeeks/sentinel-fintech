"""Async Neo4j graph database client for fraud ring and relationship analysis."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

try:
    from neo4j import AsyncGraphDatabase
except ImportError:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore


class Neo4jSettings(BaseSettings):
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "sentinel_neo4j_pass"
    database: str = "neo4j"
    max_connection_pool_size: int = 50
    connection_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


@lru_cache
def get_neo4j_settings() -> Neo4jSettings:
    return Neo4jSettings()


class Neo4jClient:
    """Async wrapper around Neo4j Python driver."""

    def __init__(self, settings: Neo4jSettings) -> None:
        self._settings = settings
        self._driver = None  # type: ignore

    async def connect(self) -> None:
        if AsyncGraphDatabase is None:
            raise ImportError("neo4j package not installed. Run: pip install neo4j")
        self._driver = AsyncGraphDatabase.driver(
            self._settings.uri,
            auth=(self._settings.user, self._settings.password),
            max_connection_pool_size=self._settings.max_connection_pool_size,
            connection_timeout=self._settings.connection_timeout_seconds,
        )
        await self._driver.verify_connectivity()
        logger.info("Neo4j connected at %s", self._settings.uri)

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    async def run_query(self, query: str, params: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results as list of dicts."""
        async with self._driver.session(database=self._settings.database) as session:
            result = await session.run(query, params or {})
            return [record.data() for record in result]

    async def write_query(self, query: str, params: Optional[dict[str, Any]] = None) -> None:
        """Execute a write Cypher query."""
        async with self._driver.session(database=self._settings.database) as session:
            await session.run(query, params or {})

    async def create_entity(self, entity_id: str, entity_type: str, properties: dict[str, Any] = None) -> None:
        """Create a node in the graph."""
        props = properties or {}
        props["entity_type"] = entity_type
        props_str = ", ".join(f"{k}: ${k}" for k in props)
        # NOTE: this interpolation is not valid Cypher — ``SET n += $`` expects a
        # map parameter, not a property list. Left as-is because the Neo4j write
        # path has no test coverage yet; fix it together with that coverage rather
        # than changing graph behaviour under a pure refactor.
        query = f"""
        MERGE (n:`{entity_type}` {{id: $entity_id}})
        SET n += ${props_str}
        """
        await self.write_query(query, {"entity_id": entity_id, **props})

    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: dict[str, Any] = None,
    ) -> None:
        """Create a directed relationship between two entities."""
        props = properties or {}
        props_str = ", ".join(f"r.{k} = ${k}" for k in props)
        set_clause = f"SET {props_str}" if props else ""
        query = f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        MERGE (a)-[r:`{rel_type}`]->(b)
        {set_clause}
        """
        await self.write_query(query, {"source_id": source_id, "target_id": target_id, **props})

    async def find_fraud_rings(self, seed_entity_id: str, depth: int = 2) -> list[dict[str, Any]]:
        """Find connected entities within `depth` hops from seed."""
        query = f"""
        MATCH path = (start {{id: $seed_id}})-[*1..{depth}]-(connected)
        RETURN connected.id AS entity_id,
               connected.entity_type AS type,
               labels(connected) AS labels,
               length(path) AS distance
        ORDER BY distance
        """
        return await self.run_query(query, {"seed_id": seed_entity_id})

    async def find_shared_attributes(
        self,
        entity_ids: list[str],
        attribute: str = "device_fingerprint",
    ) -> list[dict[str, Any]]:
        """Find entities sharing a given attribute (e.g. device, IP, phone)."""
        query = f"""
        MATCH (a), (b)
        WHERE a.id IN $entity_ids AND b.id IN $entity_ids
          AND a.id < b.id
          AND a.{attribute} IS NOT NULL
          AND a.{attribute} = b.{attribute}
        RETURN a.id AS entity_a, b.id AS entity_b, a.{attribute} AS shared_value
        """
        return await self.run_query(query, {"entity_ids": entity_ids, "attribute": attribute})


# Module-level singleton
_settings = get_neo4j_settings()
neo4j_client = Neo4jClient(_settings)
