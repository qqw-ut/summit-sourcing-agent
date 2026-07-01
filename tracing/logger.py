"""
Trace logger: records every tool call and claim as a structured event,
self-contained like the supply-chain project's event schema.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class TraceEvent:
    event_id: str
    timestamp: float
    event_type: str           # "search" | "fetch" | "claim" | "memo_complete"
    detail: dict[str, Any] = field(default_factory=dict)


class RunTracer:
    """Collects events for a single company research run."""

    def __init__(self, company_name: str):
        self.company_name = company_name
        self.events: list[TraceEvent] = []
        self._counter = 0

    def _next_id(self) -> str:
        self._counter += 1
        return f"{self.company_name.lower().replace(' ', '_')}_{self._counter:03d}"

    def log_search(self, query: str, num_results: int):
        self.events.append(TraceEvent(
            event_id=self._next_id(),
            timestamp=time.time(),
            event_type="search",
            detail={"query": query, "num_results": num_results},
        ))

    def log_fetch(self, url: str, success: bool):
        self.events.append(TraceEvent(
            event_id=self._next_id(),
            timestamp=time.time(),
            event_type="fetch",
            detail={"url": url, "success": success},
        ))

    def log_claim(self, section: str, text: str, confidence: str,
                   source_name: str, reasoning: str, source_url: Optional[str] = None):
        self.events.append(TraceEvent(
            event_id=self._next_id(),
            timestamp=time.time(),
            event_type="claim",
            detail={
                "section": section,
                "text": text,
                "confidence": confidence,
                "source_name": source_name,
                "source_url": source_url,
                "reasoning": reasoning,
            },
        ))

    def claims(self) -> list[dict]:
        return [e.detail for e in self.events if e.event_type == "claim"]

    def diagnosis(self) -> dict:
        """Summary diagnosis: confidence distribution, weakest sections, coverage gaps."""
        claims = self.claims()
        if not claims:
            return {"status": "no_claims", "message": "No claims were logged for this run."}

        confidence_counts = {"high": 0, "medium": 0, "low": 0, "unverified": 0}
        section_counts: dict[str, int] = {}
        weak_claims = []

        for c in claims:
            confidence_counts[c["confidence"]] = confidence_counts.get(c["confidence"], 0) + 1
            section_counts[c["section"]] = section_counts.get(c["section"], 0) + 1
            if c["confidence"] in ("low", "unverified"):
                weak_claims.append(c)

        total = len(claims)
        high_pct = confidence_counts["high"] / total if total else 0
        weak_pct = (confidence_counts["low"] + confidence_counts["unverified"]) / total if total else 0

        all_sections = ["overview", "growth_signals", "risks", "metrics", "recommendation"]
        missing_sections = [s for s in all_sections if section_counts.get(s, 0) == 0]

        if weak_pct > 0.4:
            overall = "low_confidence"
            recommendation = "More than 40% of claims are low-confidence or unverified. Recommend additional primary-source research before circulating this memo."
        elif missing_sections:
            overall = "incomplete_coverage"
            recommendation = f"Missing coverage in: {', '.join(missing_sections)}. Recommend targeted follow-up research."
        elif high_pct > 0.6:
            overall = "strong"
            recommendation = "Majority of claims are backed by primary sources. Memo is ready for internal review."
        else:
            overall = "moderate"
            recommendation = "Reasonable evidence base, but several claims rely on secondary sources. Spot-check before circulating."

        return {
            "status": overall,
            "total_claims": total,
            "confidence_distribution": confidence_counts,
            "section_coverage": section_counts,
            "missing_sections": missing_sections,
            "weak_claims": weak_claims,
            "recommendation": recommendation,
        }

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "events": [asdict(e) for e in self.events],
            "diagnosis": self.diagnosis(),
        }

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
