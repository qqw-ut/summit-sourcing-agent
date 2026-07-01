"""
Tool definitions for the sourcing research agent.
Each tool the agent can call, plus the Anthropic tool-schema for each.
"""

from typing import Any


TOOL_SCHEMAS = [
    {
        "name": "web_search",
        "description": (
            "Search the web for information about the target company. "
            "Use specific, narrow queries — company name + topic (e.g. "
            "'Keeper Security funding round 2025') rather than broad terms."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query, 2-6 words"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_page",
        "description": (
            "Fetch the full text content of a specific URL returned by web_search. "
            "Use this when a search snippet is too short to extract a reliable claim."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "log_claim",
        "description": (
            "Record a single factual claim for the memo, along with its evidence and "
            "a confidence level. Call this once per discrete claim — do not bundle "
            "multiple facts into one claim. You MUST call this for every factual "
            "statement that will appear in the final memo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "section": {
                    "type": "string",
                    "enum": ["overview", "growth_signals", "risks", "metrics", "recommendation"],
                },
                "text": {
                    "type": "string",
                    "description": "The claim itself, in plain English, 1-2 sentences",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["high", "medium", "low", "unverified"],
                    "description": (
                        "high = primary source (company site, SEC, press release) with direct figure. "
                        "medium = reputable secondary source (TechCrunch, Crunchbase) or reasonable inference from a primary source. "
                        "low = single weak source or indirect inference. "
                        "unverified = no source found, flagging as an assumption."
                    ),
                },
                "source_name": {"type": "string", "description": "e.g. 'TechCrunch', 'company website', 'Crunchbase'"},
                "source_url": {"type": "string", "description": "URL if available"},
                "reasoning": {
                    "type": "string",
                    "description": "One sentence on why this confidence level was assigned",
                },
            },
            "required": ["section", "text", "confidence", "source_name", "reasoning"],
        },
    },
]


def tool_schema_names() -> list[str]:
    return [t["name"] for t in TOOL_SCHEMAS]
