"""Vendor integration layer for the Sentinel P2P taint guard."""

from src.vendors.aggregator import VendorAggregator, build_registry, get_aggregator
from src.vendors.base import (
    AddressSubject,
    BankSubject,
    NameSubject,
    ProviderError,
    ProviderUnavailable,
    ScreeningProvider,
    SubjectKind,
)

__all__ = [
    "VendorAggregator",
    "build_registry",
    "get_aggregator",
    "ScreeningProvider",
    "SubjectKind",
    "AddressSubject",
    "BankSubject",
    "NameSubject",
    "ProviderError",
    "ProviderUnavailable",
]
