"""Milvus vector database client wrapper for entity embeddings."""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

try:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility
except ImportError:  # pragma: no cover
    Collection = None  # type: ignore
    connections = None  # type: ignore
    utility = None  # type: ignore


class MilvusSettings(BaseSettings):
    uri: str = "http://localhost:19530"
    collection_name: str = "entities"
    dimension: int = 384
    index_type: str = "IVF_FLAT"
    metric_type: str = "IP"
    nlist: int = 128

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": False, "extra": "ignore"}


class MilvusClient:
    """Thin wrapper around PyMilvus for entity vector storage and retrieval."""

    def __init__(self, settings: MilvusSettings) -> None:
        self._settings = settings
        self._collection: Optional[Collection] = None
        self._connected = False

    def connect(self) -> None:
        connections.connect("default", uri=self._settings.uri)
        self._connected = True
        logger.info("Milvus connected at %s", self._settings.uri)

    def disconnect(self) -> None:
        if self._connected and connections.util._get_connection("default"):
            connections.disconnect("default")
            self._connected = False
            logger.info("Milvus disconnected")

    @property
    def collection(self) -> Optional[Collection]:
        if not self._connected or self._collection is None:
            return None
        return self._collection

    def ensure_collection(self) -> Collection:
        """Create or load the entity collection."""
        if self._collection is not None:
            return self._collection

        if not utility.has_collection(self._settings.collection_name):
            fields = [
                FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True),
                FieldSchema(name="entity_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self._settings.dimension),
                FieldSchema(name="metadata", dtype=DataType.JSON),
                FieldSchema(name="score", dtype=DataType.FLOAT),
            ]
            schema = CollectionSchema(fields, description="Sentinel entity embeddings")
            self._collection = Collection(self._settings.collection_name, schema)

            index_params = self._prepare_index()
            self._collection.create_index("embedding", index_params)
            self._collection.load()
            logger.info("Milvus collection '%s' created and indexed", self._settings.collection_name)
        else:
            self._collection = Collection(self._settings.collection_name)
            self._collection.load()

        return self._collection

    def _prepare_index(self) -> dict[str, Any]:
        return {
            "index_type": self._settings.index_type,
            "metric_type": self._settings.metric_type,
            "params": {"nlist": self._settings.nlist},
        }

    async def upsert(
        self,
        id: str,
        entity_type: str,
        name: str,
        embedding: list[float],
        metadata: Optional[dict[str, Any]] = None,
        score: Optional[float] = None,
    ) -> None:
        col = self.ensure_collection()
        col.insert([
            [id],
            [entity_type],
            [name],
            [embedding],
            [metadata or {}],
            [score or 0.0],
        ])
        col.flush()
        logger.debug("Upserted entity '%s' into Milvus", id)

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
        entity_type: Optional[str] = None,
        score_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        col = self.ensure_collection()
        expr = f"entity_type == '{entity_type}'" if entity_type else ""
        results = col.search(
            data=[query_embedding],
            anns_field="embedding",
            limit=limit,
            expr=expr,
            param={"metric_type": self._settings.metric_type, "params": {"nprobe": 16}},
        )
        hits: list[dict[str, Any]] = []
        for hit in results[0]:
            if hit.distance < score_threshold:
                continue
            entity = col.get_entities(entity_ids=[hit.id])
            hits.append(
                {
                    "id": hit.id,
                    "score": round(hit.distance, 4),
                    "entity_type": entity[0].get("entity_type"),
                    "name": entity[0].get("name"),
                    "metadata": entity[0].get("metadata"),
                }
            )
        return hits


# ── Module-level singleton ────────────────────────────────────────────────────

_milvus_settings = MilvusSettings()
milvus_client = MilvusClient(_milvus_settings)


async def ensure_collection() -> Collection:
    milvus_client.connect()
    return milvus_client.ensure_collection()
