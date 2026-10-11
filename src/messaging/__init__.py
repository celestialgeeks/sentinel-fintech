"""Event-stream consumers for the Sentinel real-time pipeline.

Named ``messaging`` rather than ``kafka`` on purpose: a top-level package called
``kafka`` shadows the ``kafka-python`` distribution whenever ``src`` is on
``sys.path``, which turns a third-party import into a silent local one. The
transport itself lives in :mod:`src.core.kafka_client`; this package holds the
handlers that consume payment events.
"""

from __future__ import annotations

from src.messaging.consumer import get_pending_status, setup_consumer

__all__ = ["setup_consumer", "get_pending_status"]
