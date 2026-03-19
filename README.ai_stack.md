# AI Stack Notes

## Key External AI Libraries

| Library / Tool | What it is | How it is used in this repo | Why it is used here |
|---|---|---|---|
| `langchain-openai` | LangChain integration for OpenAI chat models | Instantiates `ChatOpenAI` for the planner, synthesis, and reflection steps | Simple LLM wiring with a common wrapper |
| `langchain` | General LLM application framework | Used only in a light-touch way through the surrounding LangChain ecosystem rather than deep chains/agents abstractions | Practice with the LangChain ecosystem |
| `sentence-transformers` | Hugging Face embedding and reranking library | Loads the dense embedding model and the cross-encoder reranker | Standard embedding and rerank stack |
| `pymilvus` | Python client for Milvus vector DB | Connects to the Milvus collection for retrieval and ingestion | Real vector DB integration |
| `guardrails-ai` | Safety/validation library for LLM input and output | Wraps input/output toxicity-style checks in `src/agents/guardrails/service.py` | Basic safety layer around LLM calls |
| `langsmith` | Tracing and observability tooling for LLM apps | Adds `@traceable` instrumentation to planner, manager, and specialists | Run tracing and observability |

## Key AI Components in This Repo

| Component | What it is | How it is used in this repo | Why it is used here |
|---|---|---|---|
| BM25 sparse encoder artifact | Lexical retrieval component | Loads the prefit BM25 model from `artifacts/bm25_model.pkl` and runs sparse query encoding during hybrid retrieval | Hybrid retrieval with dense plus sparse search |
| API prompt-injection safeguards | Lightweight API boundary defense | Blocks obvious prompt-exfiltration and override patterns before orchestration | Basic application-layer security check |
| MCP-inspired seam (`src/agents/mcp/`) | Local tool naming/contracts layer inspired by Model Context Protocol patterns | Defines named tools, shared request/response contracts, and a client seam around retrieve/rerank/synthesize/reflect operations | Practice with MCP-style structure and seams |
| Planner LLM | Query rewrite and coherence-check step | Rewrites the raw user query and decides whether it is coherent enough to process | Query cleanup before retrieval |
| Synthesis LLM | Final answer generator | Produces the grounded answer from top retrieved evidence | Grounded answer generation |
| Reflection LLM | LLM-as-judge evaluation step | Produces confidence plus applicability and uncertainty notes | Confidence and caveat generation |

## Usage Notes

- The manager/orchestration layer is intentionally custom and deterministic to keep runtime behavior and control flow predictable.
- In this repo, "MCP-inspired" means the code separates tool names, contracts, and client calls into a dedicated `src/agents/mcp/` module. It does not mean the repo is running a full external MCP client/server integration.

## Example Comparison

`illustrative_pipeline.py`
- Pros: shortest flow, easiest to scan, closest to the minimum deterministic pipeline this repo needs.
- Cons: fewer structural seams if the system later grows in complexity.

`illustrative_pipeline_with_mcp_seam.py`
- Pros: clearer named tool boundaries, easier to imagine extension points for tool contracts or alternate backends.
- Cons: adds indirection quickly, and for this repo may recreate some of the extra structure that already makes the main implementation harder to scan.

For this repo's current scope, `illustrative_pipeline.py` is the better readability baseline.

## Current vs Alternative Orchestration

Current repo architecture:

- `src/api/service.py` calls the planner/manager/specialists stack indirectly.
- `src/agents/core/manager.py` is the main coordinator for the fixed pipeline.
- `src/agents/specialists/service.py` acts as a facade over retrieval, rerank, synthesis, and reflection.
- This structure favors subsystem boundaries and a separate orchestration layer over a flatter request path.

More canonical LangChain-style alternative:

- one explicit pipeline entrypoint would coordinate the planner, retrieval, rerank, synthesis, and reflection flow more directly
- LangChain would still mainly be used through `ChatOpenAI`, but the top-level execution path would be flatter and easier to trace
- MCP-inspired seams could still exist around tool naming or retrieval client boundaries
- Illustrative comparisons: [`examples/langchain/illustrative_pipeline.py`](examples/langchain/illustrative_pipeline.py) and [`examples/langchain/illustrative_pipeline_with_mcp_seam.py`](examples/langchain/illustrative_pipeline_with_mcp_seam.py). These examples are not used by the app runtime.

This would be an architecture change, not just a readability cleanup. The current repo keeps more custom layering and indirection; the alternative would simplify the main flow but also change the orchestration boundary.

## Why the Current Architecture Exists

- The current structure keeps subsystem boundaries explicit across API wiring, orchestration, and specialist implementations.
- The layering leaves room for future orchestration changes without forcing retrieval, rerank, synthesis, and reflection logic into one large module.
- It also provides a more natural place for state-aware flows, such as retries, replanning, or additional review/reflection passes if the system grows beyond the current fixed pipeline.

During development, other orchestration ideas were explored, including less deterministic flows such as extra reflection or review-style passes before finalizing an answer. The current architecture reflects the decision to settle on a simpler fixed pipeline after those experiments.
