"""
Research agent: drives the Claude tool-use loop to research a company
and produce a sourcing memo backed by traced, confidence-scored claims.

Live search backend: Tavily (https://tavily.com). Get a free API key,
set TAVILY_API_KEY in your environment, and this runs end-to-end with
no further changes.
"""

import os
import sys
import json
import anthropic

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.config import RunConfig, CompanyTarget
from tools.tool_definitions import TOOL_SCHEMAS
from tracing.logger import RunTracer

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


SYSTEM_PROMPT = """You are a sourcing analyst at a growth equity firm, preparing a brief \
research memo on a potential portfolio company.

Your job:
1. Use web_search and fetch_page to research the company: what it does, growth signals \
(funding, hiring, product launches, customer traction), risks (competition, market headwinds, \
execution concerns), and any concrete metrics you can find.
2. For EVERY factual claim you plan to put in the memo, call log_claim. Do not state facts \
in your final summary that were not logged as claims first.
3. Assign confidence honestly. If you can't find a primary source for something, say so — \
mark it 'low' or 'unverified' rather than overstating certainty. This is the whole point: \
a memo that distinguishes what's verified from what's inferred is more useful than one \
that sounds confident but isn't.
4. Cover all five sections if possible: overview, growth_signals, risks, metrics, recommendation.
5. Budget your tool calls. Aim for 5-8 searches and 2-4 page fetches, then synthesize. \
You don't need to be exhaustive — a focused, honestly-scored memo beats an exhaustive but \
unverifiable one.

When you are done researching and have logged your claims, write a short final text summary \
(3-5 sentences) of your overall read on the company. Do not repeat the individual claims — \
those are already captured. Just give your top-line takeaway."""


class ResearchAgent:
    def __init__(self, config: RunConfig, api_key: str | None = None, tavily_api_key: str | None = None):
        self.config = config
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.tracer = RunTracer(config.company.name)
        self.search_calls = 0
        self.fetch_calls = 0

        tavily_key = tavily_api_key or os.environ.get("TAVILY_API_KEY")
        if TavilyClient is None:
            raise ImportError("tavily-python not installed. Run: pip install tavily-python")
        if not tavily_key:
            raise ValueError(
                "No Tavily API key found. Set TAVILY_API_KEY env var, or pass "
                "tavily_api_key= explicitly. Get a free key at https://tavily.com"
            )
        self.tavily = TavilyClient(api_key=tavily_key)

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "web_search":
            self.search_calls += 1
            query = tool_input["query"]
            # NOTE: in this harness, actual web_search execution is delegated to the
            # outer Claude orchestration (see run_pipeline.py docstring). This module
            # is designed to be called either with a live web_search client, or in
            # "trace replay" mode for the demo viewer.
            result = self._web_search_impl(query)
            self.tracer.log_search(query, num_results=len(result.get("results", [])))
            return json.dumps(result)

        elif tool_name == "fetch_page":
            self.fetch_calls += 1
            url = tool_input["url"]
            result = self._fetch_impl(url)
            self.tracer.log_fetch(url, success=result.get("success", False))
            return json.dumps(result)

        elif tool_name == "log_claim":
            self.tracer.log_claim(
                section=tool_input["section"],
                text=tool_input["text"],
                confidence=tool_input["confidence"],
                source_name=tool_input["source_name"],
                reasoning=tool_input["reasoning"],
                source_url=tool_input.get("source_url"),
            )
            return json.dumps({"status": "logged"})

        return json.dumps({"error": f"unknown tool {tool_name}"})

    def _web_search_impl(self, query: str) -> dict:
        try:
            resp = self.tavily.search(query=query, max_results=5, search_depth="basic")
            results = [
                {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "snippet": r.get("content", "")[:500],
                }
                for r in resp.get("results", [])
            ]
            return {"query": query, "results": results}
        except Exception as e:
            return {"query": query, "results": [], "error": str(e)}

    def _fetch_impl(self, url: str) -> dict:
        try:
            resp = self.tavily.extract(urls=[url])
            extracted = resp.get("results", [])
            if not extracted:
                return {"url": url, "success": False, "error": "no content extracted"}
            content = extracted[0].get("raw_content", "")[:4000]
            return {"url": url, "success": True, "content": content}
        except Exception as e:
            return {"url": url, "success": False, "error": str(e)}

    def run(self) -> dict:
        messages = [{
            "role": "user",
            "content": f"Research {self.config.company.name} ({self.config.company.domain or 'no domain given'}) "
                       f"and prepare a sourcing memo. Sector context: {self.config.company.sector or 'unknown'}."
        }]

        final_summary = ""
        max_turns = 20
        for _ in range(max_turns):
            if self.search_calls >= self.config.max_search_calls and self.fetch_calls >= self.config.max_fetch_calls:
                break

            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=2000,
                system=SYSTEM_PROMPT,
                tools=TOOL_SCHEMAS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                final_summary = "".join(
                    block.text for block in response.content if block.type == "text"
                )
                break

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result_text = self._execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_text,
                    })
            messages.append({"role": "user", "content": tool_results})

        return {
            "company": self.config.company.name,
            "final_summary": final_summary,
            "trace": self.tracer.to_dict(),
        }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run a live sourcing research agent on one company.")
    parser.add_argument("company", help="Company name to research")
    parser.add_argument("--sector", default=None, help="Optional sector context")
    parser.add_argument("--domain", default=None, help="Optional company domain")
    parser.add_argument("--out", default=None, help="Path to write trace JSON (default: runs/<company>.json)")
    args = parser.parse_args()

    config = RunConfig(
        company=CompanyTarget(name=args.company, sector=args.sector, domain=args.domain)
    )
    agent = ResearchAgent(config)
    print(f"Researching {args.company}...")
    result = agent.run()

    out_path = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "runs",
        f"{args.company.lower().replace(' ', '_')}.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result["trace"], f, indent=2)

    d = result["trace"]["diagnosis"]
    print(f"\nDone. {d.get('total_claims', 0)} claims logged. Status: {d.get('status')}")
    print(f"Summary: {result['final_summary']}")
    print(f"Trace written to {out_path}")


if __name__ == "__main__":
    main()
