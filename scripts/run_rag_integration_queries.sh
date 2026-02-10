#!/usr/bin/env bash
set -euo pipefail

API_URL=${API_URL:-"http://localhost:8000"}
OUT_DIR=${OUT_DIR:-"logs/integration"}

# NOTE: Requires a running API and a populated vector DB (Milvus) with ingested data.
# This is a smoke test for end-to-end wiring, not response quality.

mkdir -p "$OUT_DIR"

queries=(
  "What are FY2025 productivity measures?"
  "I am a policy researcher. Show productivity-support trends since FY2020 and compare how measure design has shifted over time."
  "Why increase GST???"
  "How are middle income families being supported?"
  "Someone earning 80k, no home ownership, staying in hdb (parents owned) - How much cash payout received over the years"
)

for i in "${!queries[@]}"; do
  q="${queries[$i]}"
  printf "\n==> %s\n" "$q"
  response=$(curl -sS -X POST "$API_URL/ask" \
    -H "Content-Type: application/json" \
    -d "{\"query\":\"${q//"/\\"}\"}")
  echo "$response" > "$OUT_DIR/$(printf '%02d' "$((i+1))").json"
  echo "$response" | head -c 2000
  printf "\n"
  sleep 0.2
 done
