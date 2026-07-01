# Summit Sourcing Intelligence

An AI-powered deal flow research agent for growth equity analysts. Built as a submission for the [Summit Partners Base Camp AI Builder-in-Residence program](https://www.summitpartners.com).

---

## What it does

Most teams now use LLMs to write market summaries. The problem: you have no idea which sentences are grounded in real data and which ones the model made up.

This system solves a different problem than "write me an analysis." It solves **how do I know whether to trust this analysis.**

Every factual claim the agent makes must be submitted through a `log_claim` tool call — which requires a confidence level (`high` / `medium` / `low` / `unverified`), a named source, and a one-sentence justification. The agent cannot state a fact without making this commitment. That constraint is structural, not a prompt instruction that can be ignored.

The result is a sourcing memo where every sentence is traceable, and where the system honestly reports when evidence is thin rather than filling gaps with plausible-sounding inference.

---

## Two modes

### Discover
Analyst inputs structured filters (sector, stage, geography, ARR range) plus optional free-text thesis description. The agent searches, screens, and returns the top 5 candidate companies — each scored across four dimensions with evidence backing.

### Analyze
Analyst names a specific company. The agent runs a full research pass and produces a sourcing memo with claim-level confidence scoring, a four-dimension scorecard, and an overall diagnosis of how much the memo can be trusted.

---

## Four scoring dimensions

Each analyzed company receives scores across four dimensions, each with a visible methodology:

| Dimension | What it measures | Scoring logic |
|---|---|---|
| **Data quality** | How well-sourced is this memo overall? | Weighted average: high-confidence claims × 100, medium × 60, low × 25, divided by total claim count |
| **Stage fit** | Does the financial profile match a growth equity window? | Baseline 55; rises to 82 if at least one core metric (revenue/ARR/growth) is confirmed from a primary source |
| **Market clarity** | Is the competitive landscape well-characterized? | 45 if fewer than 2 risk signals found; 74 if 2 or more substantiated risk claims are logged |
| **Investability** | Can a PE firm actually get in? | Maps to overall diagnosis status — filters out public companies, subsidiaries, and companies with insufficient evidence |

Click any dimension card in the viewer to see the full methodology and how this company's specific numbers flow through the formula.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Layer 1: Research Agent                                 │
│  Claude tool-use loop                                    │
│  Tools: web_search · fetch_page · log_claim             │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Trace                                          │
│  Every search, fetch, and claim logged as a structured   │
│  event. Each claim carries confidence + source +        │
│  one-line reasoning.                                     │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Legibility                                     │
│  Diagnosis-first viewer: four-dimension scorecard,       │
│  confidence distribution, per-claim evidence trail,      │
│  clickable methodology popovers.                         │
└─────────────────────────────────────────────────────────┘
```

```
sourcing-memo-agent/
├── agents/
│   └── research_agent.py       Core agent — Claude tool-use loop + CLI entry point
├── tools/
│   ├── config.py               Data models: ConfidenceLevel, Evidence, Claim, RunConfig
│   └── tool_definitions.py     Tool schemas: web_search, fetch_page, log_claim
├── tracing/
│   └── logger.py               Event logger + diagnosis logic
├── viewer/
│   ├── index.html              Single-file viewer (no build step, no server)
│   └── data.js                 Pre-generated run data (auto-updated by build script)
├── runs/                       Raw trace JSON for each analyzed company
├── build_demo_runs.py          Regenerates viewer/data.js from runs/
└── requirements.txt
```

---

## Demo companies

Five real companies included in the viewer — three pre-loaded, two discovered through the product's own workflow:

| Company | How it appears | Diagnosis | Why included |
|---|---|---|---|
| Klaviyo (NYSE: KVYO) | Pre-loaded | Strong | Agent surfaced 21 claims including public market status — correctly flagged as not a PE target, pivoted to white-space analysis |
| TradingHub | Pre-loaded | Incomplete coverage | Real Summit portfolio company; thin public disclosure — system correctly identifies evidence ceiling |
| OnRobot | Pre-loaded | Low confidence | Deliberately included as a low-evidence case; system declines to fabricate metrics |
| Bloomreach | Discovered via Discover mode | Moderate | Agent surfaced the 2022 $2.2B valuation vs. 2024 implied $484M secondary markdown — not a pre-written finding |
| Keeper Security | Discovered via Analyze search | Moderate | Real Summit portfolio company; Gartner-cited 53% YoY growth vs. 15.5% market average |

---

## Running the agent

**Requirements**
```bash
pip install -r requirements.txt
# anthropic>=0.40.0
# tavily-python>=0.5.0
```

**Environment**
```bash
export ANTHROPIC_API_KEY=sk-ant-...     # console.anthropic.com
export TAVILY_API_KEY=tvly-...          # tavily.com — free tier, 1000 req/mo
```

**Analyze a company**
```bash
python3 agents/research_agent.py "Attentive" --sector martech
# Output: runs/attentive.json
```

**Rebuild viewer data**
```bash
python3 build_demo_runs.py
# Regenerates viewer/data.js from all runs in runs/
```

**Open viewer**

Double-click `viewer/index.html` — no server required, no API key needed. All run data is embedded in `viewer/data.js`.

---

## Design decisions

**Why `log_claim` is a required tool call, not a prompt instruction**

A system prompt that says "please cite your sources" is easy for a model to partially comply with or ignore under token pressure. A tool call that must be invoked before any claim is written into the memo cannot be bypassed — the agent physically cannot produce output without making a structured commitment about what it knows and how it knows it. This is the core architectural choice.

**Why OnRobot is included with a low-confidence diagnosis**

Showing only well-researched companies would misrepresent the system. OnRobot is a private industrial manufacturer with minimal public disclosure. The correct output for a company like this is not a confident-sounding memo — it is an honest statement that public sources are exhausted and a data room request is the appropriate next step. That behavior is more useful to an analyst than a fabricated thesis.

**Why investability is a scored dimension rather than a filter**

Hard-filtering public companies before showing results would hide the reasoning. Klaviyo and Braze appear in Discover results with low investability scores because PE analysts benefit from seeing *why* a company is not actionable, not just that it has been removed. The score makes the system's reasoning visible rather than opaque.

---

## Scalability note

The internal sourcing use case is the proof of concept. The same framework — same trace schema, same confidence architecture, same viewer — can be deployed directly to portfolio companies: a BD team screening potential partners, a procurement team evaluating suppliers, a portfolio company's own sourcing function. The system prompt changes. The tool schema doesn't.

---

## Built for

[Summit Partners Base Camp AI Builder-in-Residence](https://job-boards.greenhouse.io/summitpartnerslp/jobs/8586211002) — July 2026
