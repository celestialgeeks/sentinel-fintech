"""Enumerations shared by the ORM, the API schemas, and the portal read layer.

All are ``(str, Enum)`` so they round-trip through JSON as their plain value.
"""


from __future__ import annotations

import enum


class RecommendationEnum(str, enum.Enum):
    """Screening result recommendation."""

    APPROVE = "APPROVE"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


class SeverityEnum(str, enum.Enum):
    """Fraud alert severity level."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatusEnum(str, enum.Enum):
    """Fraud alert lifecycle status."""

    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class TransactionStatusEnum(str, enum.Enum):
    """Transaction lifecycle status."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DECLINED = "DECLINED"


class MerchantStatusEnum(str, enum.Enum):
    """Merchant onboarding status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW = "REVIEW"


class KYBStatusEnum(str, enum.Enum):
    """Know-Your-Business verification status."""

    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class KYCStatusEnum(str, enum.Enum):
    """Know-Your-Customer verification status."""

    NOT_STARTED = "NOT_STARTED"
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
