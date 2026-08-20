"""KYB (Know Your Business) document extraction pipeline.

Uses OCR + RAG for extracting business entities from uploaded documents.
Falls back to rule-based extraction when OCR/LLM is unavailable.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class RAGDocumentExtractor:
    """Extracts business information from merchant documents using RAG."""

    def __init__(self, use_ocr: bool = True, use_llm: bool = False) -> None:
        self._use_ocr = use_ocr
        self._use_llm = use_llm
        self._ocr_engine = None  # type: ignore
        self._llm = None  # type: ignore

    def extract(self, document_type: str, document_content: str) -> dict[str, Any]:
        """
        Extract structured fields from a document.

        Returns dict with keys: business_name, registration_number,
        address, directors, incorporation_date, risk_indicators.
        """
        # Try OCR if needed
        text = document_content
        if self._use_ocr and not text.strip():
            text = self._run_ocr(document_content)

        # Try LLM extraction
        if self._use_llm and text.strip():
            return self._llm_extract(text)

        # Fallback: rule-based extraction
        return self._rule_extract(text, document_type)

    def _run_ocr(self, image_data: bytes) -> str:
        """Run OCR on image data."""
        try:
            import easyocr  # type: ignore
            reader = easyocr.Reader(["en"], gpu=False)
            result = reader.readtext(image_data)
            return " ".join(text for _, text, _ in result)
        except ImportError:
            logger.warning("easyocr not available — using raw content")
            return ""

    def _llm_extract(self, text: str) -> dict[str, Any]:
        """Use LLM to extract structured data from document text."""
        try:
            from langchain_core.prompts import ChatPromptTemplate  # type: ignore
            from langchain_openai import ChatOpenAI  # type: ignore

            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            prompt = ChatPromptTemplate.from_messages([
                ("system", """Extract business information from the document text.
                Return JSON with: business_name, registration_number, address,
                directors (list), incorporation_date, risk_indicators (list).
                If a field is not found, omit it."""),
                ("user", text[:4000]),
            ])
            chain = prompt | llm
            response = chain.invoke({})
            content = response.content if hasattr(response, "content") else str(response)
            return json.loads(content)
        except Exception as e:
            logger.warning("LLM extraction failed: %s — falling back to rules", e)
            return self._rule_extract(text, "unknown")

    def _rule_extract(self, text: str, doc_type: str) -> dict[str, Any]:
        """Rule-based extraction from document text."""
        result: dict[str, Any] = {"document_type": doc_type, "extraction_method": "rule-based"}

        # Business name
        patterns = [
            r"(?:company|corporation|limited|llc|pvt|inc)\s+[:\-]?\s*([A-Z][A-Za-z0-9\s,]{2,99})",
            r"registered\s+name\s*[:\-]?\s*([A-Z][A-Za-z0-9\s,]{2,99})",
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                result["business_name"] = m.group(1).strip()
                break

        # Registration number
        m = re.search(r"(?:cin|registration|reg\s*no|udyog|udyam)\s*[:\-]?\s*([A-Z0-9\-]{6,20})", text, re.IGNORECASE)
        if m:
            result["registration_number"] = m.group(1).strip()

        # Address
        m = re.search(r"(?:address|registered\s+address)\s*[:\-]?\s*([\d\s\w,\-\.]{10,200})", text, re.IGNORECASE)
        if m:
            result["address"] = m.group(1).strip()

        # Incorporation date
        m = re.search(r"(?:incorporated|dated|established)\s+[:\-]?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", text)
        if m:
            result["incorporation_date"] = m.group(1)

        # Risk indicators
        risk_keywords = ["sanction", "pep", "adverse", "fraud", "shelter", "cash intensive"]
        result["risk_indicators"] = [
            kw for kw in risk_keywords if kw in text.lower()
        ]

        return result


class KYBVerifier:
    """Verifies KYB document extraction results against known rules."""

    HIGH_RISK_INDUSTRIES = {
        "crypto", "cryptocurrency", "gambling", "casino", "adult",
        "money service business", "remittance", "precious metals",
    }

    def verify(self, extracted: dict[str, Any], merchant_country: str) -> dict[str, Any]:
        """Verify extracted data and return verification result."""
        issues: list[str] = []
        score = 1.0

        # Check for missing critical fields
        if not extracted.get("business_name"):
            issues.append("Missing business name")
            score -= 0.3
        if not extracted.get("registration_number"):
            issues.append("Missing registration number")
            score -= 0.2

        # Check risk indicators
        risks = extracted.get("risk_indicators", [])
        if risks:
            score -= 0.1 * len(risks)
            issues.extend(risks)

        # Check industry risk
        industry = extracted.get("industry", "").lower()
        if any(hri in industry for hri in self.HIGH_RISK_INDUSTRIES):
            score -= 0.2
            issues.append(f"High-risk industry: {industry}")

        return {
            "verified": score > 0.3 and not issues,
            "verification_score": max(score, 0.0),
            "issues": issues,
            "risk_level": "HIGH" if score < 0.5 else "MEDIUM" if score < 0.8 else "LOW",
        }
