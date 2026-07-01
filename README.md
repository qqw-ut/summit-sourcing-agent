# Sourcing Memo Agent

A research agent that drafts growth-equity sourcing memos with **claim-level confidence tracing** — every factual statement is logged with its source, a confidence rating, and a one-line justification for that rating, rather than presenting a single block of undifferentiated prose.

Built as a companion piece to [prove-ai-supply-chain-simulation](https://github.com/qqw-ut/prove-ai-supply-chain-simulation), applying the same "legibility over polish" design philosophy to a different domain: instead of diagnosing *why a negotiation failed*, this diagnoses *how much you should trust this memo*.

## Why this, not just an LLM that writes a memo

Any LLM can write a fluent-sounding company summary. The harder problem — and the one that actually matters for a research analyst — is knowing **which parts of the memo are load-bearing and verified, versus which parts sound confident but rest on a single weak source or no source at all.**

This system forces that distinction structurally: the agent cannot write a claim into the memo without first calling `log_claim`, which requires it to commit to a confidence level (`high` / `medium` / `low` / `unverified`) and explain *why* that level was chosen. The viewer then runs a diagnosis pass that aggregates this into an honest read on the whole memo — including flagging when a company's public footprint is simply too thin to support a confident thesis (see the OnRobot run, intentionally included as a low-evidence case).

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Layer 1: Research Agent                                 │
│  Claude tool-use loop: web_search, fetch_page, log_claim  │
├──────────────────────────────────────────────────────────┤
│  Layer 2: Trace                                           │
│  Self-contained events: search/fetch/claim, each claim    │
│  carries confidence + reasoning + source                  │
├──────────────────────────────────────────────────────────┤
│  Layer 3: Legibility                                      │
│  Diagnosis-first viewer: confidence distribution,         │
│  missing-section detection, per-claim evidence trail      │
└──────────────────────────────────────────────────────────┘
```

## Project structure

```
sourcing-memo-agent/
├── tools/
│   ├── config.py              Enums, dataclasses (Evidence, Claim, RunConfig)
│   └── tool_definitions.py    Tool schemas: web_search, fetch_page, log_claim
├── agents/
│   └── research_agent.py      Claude tool-use loop (wire to a live search API to run end-to-end)
├── tracing/
│   └── logger.py              Event schema + diagnosis logic (confidence dist, coverage gaps)
├── viewer/
│   ├── index.html             Single-file legibility layer
│   └── data.js                Generated — embedded run data, no server needed
├── build_demo_runs.py         Builds runs.json + data.js from research evidence
└── runs/
    └── runs.json              3 example runs: Keeper Security, TradingHub, OnRobot
```

## Demo data — how it was made

`build_demo_runs.py` contains research findings gathered via live web search on three real Summit Partners portfolio companies, hand-logged through the same `RunTracer` class the live agent uses. This was a deliberate choice given the project timeline: rather than risk an unreliable live demo on stage, the trace data is real (every claim is backed by an actual source found via search) but was assembled through a manual research pass instead of an unattended agent loop.

**To run live** (this is wired up and tested — not a stub):

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
export TAVILY_API_KEY=tvly-...        # free at https://tavily.com, 1000 req/mo
python3 agents/research_agent.py "Klaviyo" --sector martech
```

This runs the full Claude tool-use loop: the model calls `web_search` (backed by Tavily search), `fetch_page` (backed by Tavily extract) and `log_claim` autonomously, with no pre-written evidence. Output is written to `runs/klaviyo.json` in the same trace schema the viewer already reads — point `viewer/data.js` at it (or re-run `build_demo_runs.py`-style packaging) to view it.

## The three demo companies, and why they're not all "wins"

| Company | Diagnosis | Why included |
|---|---|---|
| Keeper Security | `moderate` (9 claims, mostly high/medium confidence) | Strong public footprint — Gartner-cited growth figures, clear funding history. Shows the system at its best. |
| TradingHub | `incomplete_coverage` (5 claims, no metrics section) | A real B2B compliance vendor with thin public disclosure. System correctly flags the gap instead of inventing numbers. |
| OnRobot | `low_confidence` (5 claims, mostly low/unverified) | Deliberately the weakest case. Demonstrates the system declining to manufacture a confident thesis when the evidence isn't there — the entire point of the project. |

## How to view

Open `viewer/index.html` directly in a browser — no build step, no server. Data is embedded in `viewer/data.js` (regenerate both via `python3 build_demo_runs.py`).
