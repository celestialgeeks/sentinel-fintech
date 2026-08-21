"""Kafka consumer package for Sentinel real-time pipeline."""

from __future__ import annotations

from src.kafka.consumer import setup_consumer, get_pending_status

__all__ = ["setup_consumer", "get_pending_status"]
