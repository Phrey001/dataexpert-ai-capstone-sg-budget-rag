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
- For an illustrative comparison, see [`examples/langchain/explicit_pipeline.py`](examples/langchain/explicit_pipeline.py), which shows a simpler alternative that keeps the deterministic pipeline but collapses some wrapper layers. This example is not used by the app runtime.
