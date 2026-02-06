# Demo Queries and Other Sample Queries

Canonical sample query set for local demos and manual checks.
Use these exact strings in docs/scripts to keep examples in sync.


## Smoke

- **Intent:** quick sanity check for end-to-end runtime.
- **Query:** `What are FY2025 productivity measures?`
- **Expected behavior:** normal

## Policy Comparison

- **Intent:** stress planning + retrieval depth on cross-sector comparison.
- **Query:** `I am a policy analyst preparing a decision memo. Compare FY2025 productivity-related measures across key sectors and ministries, explain implementation mechanisms and trade-offs, and conclude which measures are likely to deliver the strongest medium-term productivity impact based on available budget evidence.`
- **Expected behavior:** caveated or partial

## Long-Horizon Trend

- **Intent:** verify broad-horizon trend handling across years.
- **Query:** `I am a policy researcher. Show productivity-support trends since FY2020 and compare how measure design has shifted over time.`
- **Expected behavior:** caveated or partial

## Edge Case (Nonsense/Incoherent)

- **Intent:** validate incoherent/low-signal handling.
- **Query:** `blorb flarq 2025 ??? random grants potato economy??`
- **Expected behavior:** clarify

## Persona Framing

- **Intent:** natural-language persona framing with potentially emotional tone.
- **Query:** `I am an unhappy citizen and I feel FY2025 benefits are unfair. Explain which productivity-related measures target ordinary workers versus businesses, and what evidence shows the support is balanced.`
- **Expected behavior:** caveated or partial


# Other Sample Queries (Not In Demo)

## Asking for analysis on payout
- **Query:** `Someone earning 80k, no home ownership, staying in hdb (parents owned) - How much cash payout received over the years`

## Asking for analysis on payout, including multiple scenarios
- **Query:** `Someone earning 80k, no home ownership, staying in hdb (parents owned) - How much cash payout received over the years? how about 100k, 120k?`

## Why increase GST
- **Query:** `Why increase GST???`

## Middle income question
- **Query:** `How is middle income families being supported?`