#!/usr/bin/env python3
import json
import os
import time
import urllib.request

API_URL = os.getenv("API_URL", "http://localhost:8000")
OUT_DIR = os.getenv("OUT_DIR", "logs/integration")

# NOTE: Requires a running API and a populated vector DB (Milvus) with ingested data.
# This is a smoke test for end-to-end wiring, not response quality.

QUERIES = [
    # Normal success: direct, in-scope query
    "What are FY2025 productivity measures?",
    # Caveated/partial: cross-year comparison with likely gaps
    "How did healthcare priorities change before vs after COVID?",
    # Clarify/incoherent: low-signal input
    "blorb flarq 2025 ???",
    # Persona/emotional tone: stress tone handling
    "I am an unhappy citizen and I feel FY2025 benefits are unfair. Explain which productivity-related measures target ordinary workers versus businesses.",
    # Scenario-specific eligibility: tests evidence limits
    "Someone earning 80k, no home ownership, staying in hdb (parents owned) - How much cash payout received over the years",
]


def post_json(url: str, payload: dict) -> str:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)

    for idx, query in enumerate(QUERIES, start=1):
        print(f"\n==> {query}")
        response = post_json(f"{API_URL}/ask", {"query": query})
        out_path = os.path.join(OUT_DIR, f"{idx:02d}.json")  # format filename to 2dp
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(response)
        print(response[:2000])
        time.sleep(0.2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
