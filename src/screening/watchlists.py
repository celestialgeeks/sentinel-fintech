"""Synthetic sanctions watchlists for development and testing.

In production, replace these with live OFAC, UN, EU sanctions data
downloaded from official sources or via a commercial provider
(e.g. sanctions.io, Dow Jones, Refinitiv).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WatchlistEntry:
    """A single entry from a sanctions/PEP/watchlist source."""

    entity_id: str
    name: str
    aliases: list[str]
    list_source: str  # e.g. "OFAC", "UN", "EU"
    country: str | None
    risk_weight: float = 1.0  # 0.0-1.0, higher = more risky match


# ─── OFAC SDN (Specially Designated Nationals) — sample ───────────────────────

OFAC_SDN: list[WatchlistEntry] = [
    WatchlistEntry(
        entity_id="ofac_001",
        name="AHMAD, Mohammed",
        aliases=["M. Ahmad", "Mohammed Ahmed", "Ahmed, M."],
        list_source="OFAC",
        country="IR",
        risk_weight=1.0,
    ),
    WatchlistEntry(
        entity_id="ofac_002",
        name="GLOBAL TRADE CORP",
        aliases=["Global Trade Corporation", "GTC International"],
        list_source="OFAC",
        country="SY",
        risk_weight=0.95,
    ),
    WatchlistEntry(
        entity_id="ofac_003",
        name="PETROCHEM EXPORTS LLC",
        aliases=["Petrochem Exports"],
        list_source="OFAC",
        country="RU",
        risk_weight=0.9,
    ),
]

# ─── UN Consolidated List — sample ────────────────────────────────────────────

UN_LIST: list[WatchlistEntry] = [
    WatchlistEntry(
        entity_id="un_001",
        name="AL-RASHID, Khalid",
        aliases=["K. Rashid", "Khalid Al-Rashid"],
        list_source="UN",
        country="YE",
        risk_weight=0.95,
    ),
    WatchlistEntry(
        entity_id="un_002",
        name="NORTH STAR TRADING",
        aliases=["North Star Ltd"],
        list_source="UN",
        country="KP",
        risk_weight=1.0,
    ),
]

# ─── EU Sanctions List — sample ───────────────────────────────────────────────

EU_LIST: list[WatchlistEntry] = [
    WatchlistEntry(
        entity_id="eu_001",
        name="VOLKOV, Dmitry",
        aliases=["D. Volkov", "Dmitry Volkov"],
        list_source="EU",
        country="RU",
        risk_weight=0.85,
    ),
    WatchlistEntry(
        entity_id="eu_002",
        name="TECH IMPORTS LLC",
        aliases=["Tech Imports"],
        list_source="EU",
        country="BY",
        risk_weight=0.8,
    ),
]

# ─── High-risk jurisdictions (FATF grey/black list) ──────────────────────────

HIGH_RISK_JURISDICTIONS: set[str] = {
    "IR",  # Iran
    "KP",  # North Korea
    "SY",  # Syria
    "CU",  # Cuba
    "MM",  # Myanmar
    "VE",  # Venezuela
    "BY",  # Belarus
    "RU",  # Russia (sanctioned entities)
}

# ─── Combined lookup ──────────────────────────────────────────────────────────

_ALL_WATCHLISTS: list[WatchlistEntry] = OFAC_SDN + UN_LIST + EU_LIST


def get_all_entries() -> list[WatchlistEntry]:
    """Return all watchlist entries (for embedding generation)."""
    return _ALL_WATCHLISTS


def search_by_name(name: str, limit: int = 5) -> list[WatchlistEntry]:
    """Exact-match search across all watchlists (pre-embedding fallback)."""
    name_lower = name.lower().strip()
    results: list[WatchlistEntry] = []
    for entry in _ALL_WATCHLISTS:
        if name_lower == entry.name.lower().strip():
            results.append(entry)
            continue
        for alias in entry.aliases:
            if name_lower == alias.lower().strip():
                results.append(entry)
                break
        if results:
            break
    return results[:limit]
