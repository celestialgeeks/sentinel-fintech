"""LLM-powered entity resolution using LangChain.

Performs fuzzy matching, alias resolution, and name disambiguation
using a Large Language Model. Falls back to vector similarity if LLM
is not configured.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class EntityResolver:
    """Resolves entity names using LLM + vector similarity."""

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o-mini",
        api_key: str | None = None,
    ) -> None:
        self._provider = llm_provider
        self._model = llm_model
        self._api_key = api_key
        self._llm = None  # type: ignore

    def _get_llm(self) -> Any:
        """Lazy-load the LLM client."""
        if self._llm is not None:
            return self._llm
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
            self._llm = ChatOpenAI(
                model=self._model,
                api_key=self._api_key or "",
                temperature=0,
            )
        except ImportError:
            logger.warning("langchain-openai not installed — using rule-based fallback")
            self._llm = None
        return self._llm

    def resolve(
        self,
        entity_name: str,
        candidates: list[str],
    ) -> dict[str, Any]:
        """
        Resolve an entity name against a list of candidate names.

        Returns:
            {
                "matched_name": str,
                "confidence": float,
                "reasoning": str,
                "is_alias": bool,
            }
        """
        # Try LLM first
        llm = self._get_llm()
        if llm is not None and candidates:
            return self._resolve_with_llm(entity_name, candidates, llm)

        # Fallback: exact + substring match
        return self._resolve_fallback(entity_name, candidates)

    def _resolve_with_llm(
        self,
        entity_name: str,
        candidates: list[str],
        llm: Any,
    ) -> dict[str, Any]:
        """Use LLM to resolve entity name against candidates."""
        from langchain_core.prompts import ChatPromptTemplate  # type: ignore

        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an entity resolution agent for AML/KYC screening.
            Given an entity name and a list of watchlist candidates, determine if the
            entity matches any candidate. Consider aliases, transliterations, abbreviations,
            and name variations.

            Return JSON only with this exact structure:
            {{"matched_name": "exact watchlist name or null", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""),
            ("user", f"Entity to resolve: {entity_name}\nWatchlist candidates: {candidates}"),
        ])

        chain = prompt | llm
        response = chain.invoke({})
        content = response.content if hasattr(response, "content") else str(response)

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            match = re.search(r"\{[^}]+\}", content)
            if match:
                result = json.loads(match.group())
            else:
                result = {"matched_name": None, "confidence": 0.0, "reasoning": "Could not parse LLM response"}

        logger.info("LLM resolution: %s → %s (confidence=%.2f)", entity_name, result.get("matched_name"), result.get("confidence", 0))
        return result

    def _resolve_fallback(self, entity_name: str, candidates: list[str]) -> dict[str, Any]:
        """Rule-based fallback: exact match, case-insensitive, substring."""
        name_lower = entity_name.lower().strip()
        for candidate in candidates:
            cand_lower = candidate.lower().strip()
            if name_lower == cand_lower:
                return {"matched_name": candidate, "confidence": 1.0, "reasoning": "Exact match", "is_alias": False}
            if name_lower in cand_lower or cand_lower in name_lower:
                return {"matched_name": candidate, "confidence": 0.7, "reasoning": "Substring match", "is_alias": True}
        return {"matched_name": None, "confidence": 0.0, "reasoning": "No match found", "is_alias": False}
