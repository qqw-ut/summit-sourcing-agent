"""
Config: enums and dataclasses for the sourcing memo pipeline.
Mirrors the structure of the supply-chain negotiation project's tools/config.py
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "high"          # direct quote / hard number from primary source (company site, SEC, press release)
    MEDIUM = "medium"      # reputable secondary source (TechCrunch, Crunchbase) or inferred from primary
    LOW = "low"            # single weak source, or model inference without direct evidence
    UNVERIFIED = "unverified"  # model guess, no source found


class SourceType(str, Enum):
    COMPANY_SITE = "company_site"
    PRESS_RELEASE = "press_release"
    NEWS = "news"
    DATABASE = "database"      # crunchbase, pitchbook, etc.
    SEC_FILING = "sec_filing"
    NONE = "none"


class MemoSection(str, Enum):
    OVERVIEW = "overview"
    GROWTH_SIGNALS = "growth_signals"
    RISKS = "risks"
    METRICS = "metrics"
    RECOMMENDATION = "recommendation"


@dataclass
class Evidence:
    """A single piece of supporting evidence for a claim."""
    source_type: SourceType
    source_name: str           # e.g. "TechCrunch", "company website"
    source_url: Optional[str] = None
    snippet: Optional[str] = None   # short paraphrase, never verbatim long quotes
    retrieved_at: Optional[str] = None


@dataclass
class Claim:
    """A single factual claim made in the memo, with its evidence trail."""
    claim_id: str
    section: MemoSection
    text: str
    confidence: ConfidenceLevel
    evidence: list[Evidence] = field(default_factory=list)
    reasoning: Optional[str] = None   # why this confidence level was assigned


@dataclass
class CompanyTarget:
    name: str
    domain: Optional[str] = None
    sector: Optional[str] = None
    known_investor: Optional[str] = None  # e.g. "Summit Partners" — for context, not bias


@dataclass
class RunConfig:
    company: CompanyTarget
    max_search_calls: int = 8
    max_fetch_calls: int = 4
    model: str = "claude-sonnet-4-6"
