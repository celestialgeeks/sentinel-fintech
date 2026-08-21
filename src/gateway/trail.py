"""Money trail engine for real-time fraud detection.

Analyzes transaction graphs using Neo4j to detect circular flows,
structuring, layering, and high-risk counterparty connections.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.gateway.schemas import (
    MoneyTrailNode,
    TrailAnalysis,
    TrailFlags,
)
from src.shared.graph_db import neo4j_client

logger = logging.getLogger(__name__)


class MoneyTrailEngine:
    """Analyzes money trails through graph traversal and pattern detection."""

    def __init__(self, max_depth: int = 5) -> None:
        self._max_depth = max_depth

    async def follow_trail(self, payment_id: str, depth: int | None = None) -> TrailAnalysis:
        """Traverse Neo4j graph to find connected transactions.

        Args:
            payment_id: The originating payment identifier
            depth: How many hops to traverse (default: max_depth)

        Returns:
            TrailAnalysis with nodes and risk flags
        """
        depth = depth or self._max_depth
        logger.info("Following money trail for payment %s (depth=%d)", payment_id, depth)

        # Query connected entities from Neo4j
        query = f"""
        MATCH path = (start {{id: $payment_id}})-[*1..{depth}]-(connected)
        RETURN connected.id AS entity_id,
               connected.entity_type AS type,
               labels(connected) AS labels,
               length(path) AS distance,
               connected.risk_score AS risk_score,
               connected.name AS name,
               connected.attributes AS attributes
        ORDER BY distance
        """
        results = await neo4j_client.run_query(query, {"payment_id": payment_id})

        nodes = [
            MoneyTrailNode(
                entity_id=r["entity_id"],
                entity_type=r.get("type", "unknown"),
                name=r.get("name", "Unknown"),
                risk_score=float(r.get("risk_score", 0.0)),
                attributes=r.get("attributes") or {},
                distance=int(r["distance"]),
            )
            for r in results
        ]

        # Detect risk patterns
        flags = await self._detect_patterns(payment_id, nodes)

        # Aggregate risk score
        aggregated_score = self._calculate_aggregated_risk(nodes, flags)

        return TrailAnalysis(
            payment_id=payment_id,
            trail_depth=depth,
            nodes=nodes,
            flags=flags,
            aggregated_risk_score=aggregated_score,
            analysis_timestamp=datetime.now(timezone.utc),
            summary=self._generate_summary(nodes, flags, aggregated_score),
        )

    async def detect_circular_flow(self, payment_id: str) -> bool:
        """Detect if money loops back to the original sender.

        A circular flow pattern: A → B → C → A indicates potential money laundering.
        """
        query = """
        MATCH path = (start {{id: $payment_id}})-[*2..5]-(start)
        WHERE length(path) > 1
        RETURN count(path) AS cycle_count
        """
        results = await neo4j_client.run_query(query, {"payment_id": payment_id})
        cycle_count = results[0]["cycle_count"] if results else 0
        is_circular = cycle_count > 0
        if is_circular:
            logger.warning("Circular flow detected for payment %s: %d cycles", payment_id, cycle_count)
        return is_circular

    async def detect_structuring(self, payment_id: str) -> bool:
        """Detect if a sender is splitting transactions to stay below thresholds.

        Structuring pattern: multiple small transactions from the same sender
        within a short time window, totaling a large amount.
        """
        query = """
        MATCH (sender)-[:SENT]->(t)
        WHERE sender.id = $payment_id OR t.sender_id = $payment_id
        RETURN count(t) AS txn_count, sum(t.amount) AS total_amount
        """
        results = await neo4j_client.run_query(query, {"payment_id": payment_id})
        if not results:
            return False
        count = results[0]["txn_count"]
        total = results[0]["total_amount"]
        # Flag if >5 transactions totaling >$10,000 in 24h window
        is_structured = count > 5 and total > 10000
        if is_structured:
            logger.warning("Structuring detected for payment %s: %d txns, $%.2f total", payment_id, count, total)
        return is_structured

    async def get_counterparty_risk(self, entity_id: str) -> dict[str, Any]:
        """Check entity risk from PostgreSQL + Neo4j."""
        # Check Neo4j for related fraud rings
        rings = await neo4j_client.find_fraud_rings(entity_id, depth=2)

        # Check if entity has shared attributes with known fraud entities
        shared_attrs = await neo4j_client.find_shared_attributes([entity_id], "device_fingerprint")

        return {
            "entity_id": entity_id,
            "fraud_ring_members": len(rings),
            "shared_device_fingerprints": len(shared_attrs),
            "risk_level": "HIGH" if (len(rings) > 0 or len(shared_attrs) > 0) else "LOW",
        }

    async def build_trail_context(self, payment_id: str) -> dict[str, Any]:
        """Assemble full context for the verification agent."""
        trail = await self.follow_trail(payment_id)
        circular = await self.detect_circular_flow(payment_id)
        structured = await self.detect_structuring(payment_id)

        return {
            "trail_analysis": trail.model_dump(),
            "circular_flow_detected": circular,
            "structuring_detected": structured,
            "risk_score": trail.aggregated_risk_score,
        }

    async def _detect_patterns(self, payment_id: str, nodes: list[MoneyTrailNode]) -> TrailFlags:
        """Detect risk patterns in the trail."""
        flags = TrailFlags()
        flags.circular_flow = await self.detect_circular_flow(payment_id)
        flags.structuring = await self.detect_structuring(payment_id)

        # Check for high-risk counterparties
        for node in nodes:
            if node.risk_score > 0.7:
                flags.high_risk_counterparties.append(node.entity_id)
            if node.entity_type in ("sanctioned_entity", "pep"):
                flags.sanctions_matches.append(node.name)

        return flags

    def _calculate_aggregated_risk(self, nodes: list[MoneyTrailNode], flags: TrailFlags) -> float:
        """Calculate overall risk score from 0.0 to 1.0."""
        if not nodes:
            return 0.0

        # Base score from node risk scores
        avg_node_risk = sum(n.risk_score for n in nodes) / len(nodes) if nodes else 0.0

        # Penalty for detected patterns
        pattern_penalty = 0.0
        if flags.circular_flow:
            pattern_penalty += 0.3
        if flags.structuring:
            pattern_penalty += 0.2
        if flags.sanctions_matches:
            pattern_penalty += 0.4
        if flags.high_risk_counterparties:
            pattern_penalty += 0.1 * min(len(flags.high_risk_counterparties), 3)

        # Clamp to [0, 1]
        return min(1.0, max(0.0, avg_node_risk + pattern_penalty))

    def _generate_summary(self, nodes: list[MoneyTrailNode], flags: TrailFlags, risk: float) -> str:
        """Generate human-readable summary of trail analysis."""
        parts = [f"Trail depth: {len(nodes)} nodes found"]
        if flags.circular_flow:
            parts.append("⚠ Circular flow detected")
        if flags.structuring:
            parts.append("⚠ Structuring pattern detected")
        if flags.sanctions_matches:
            parts.append(f"⚠ {len(flags.sanctions_matches)} sanctions matches")
        if flags.high_risk_counterparties:
            parts.append(f"⚠ {len(flags.high_risk_counterparties)} high-risk counterparties")
        parts.append(f"Aggregated risk score: {risk:.3f}")
        return ". ".join(parts) + "."


# Module-level singleton
_trail_engine = MoneyTrailEngine()
