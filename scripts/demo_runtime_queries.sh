#!/usr/bin/env bash
set -euo pipefail
# Local working copy: scripts/demo_queries.md

if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "warning: OPENAI_API_KEY is not set; runtime may fail if your setup requires it."
fi

if [[ -z "${MILVUS_URI:-}" || -z "${MILVUS_TOKEN:-}" ]]; then
  echo "warning: MILVUS_URI or MILVUS_TOKEN is not set; runtime may fail readiness checks."
fi

run_demo() {
  local label="$1"
  local query="$2"

  echo
  echo "============================================================"
  echo "Demo: ${label}"
  echo "============================================================"
  echo "Command:"
  echo "python -m src.agents.runtime --query \"$query\""
  python -m src.agents.runtime --query "$query"
}

run_demo \
  "Short query smoke check" \
  "What are FY2025 productivity measures?"

run_demo \
  "Long query policy comparison" \
  "I am a policy analyst preparing a decision memo. Compare FY2025 productivity-related measures across key sectors and ministries, explain implementation mechanisms and trade-offs, and conclude which measures are likely to deliver the strongest medium-term productivity impact based on available budget evidence."

run_demo \
  "Edge-case nonsense query" \
  "blorb flarq 2025 ??? random grants potato economy??"

run_demo \
  "Persona: unhappy citizen" \
  "I am an unhappy citizen and I feel FY2025 benefits are unfair. Explain which productivity-related measures target ordinary workers versus businesses, and what evidence shows the support is balanced."

run_demo \
  "Long-horizon trend analysis" \
  "I am a policy researcher. Show productivity-support trends since FY2020 and compare how measure design has shifted over time."
