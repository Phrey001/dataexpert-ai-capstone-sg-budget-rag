# LangChain Examples

This directory contains illustrative examples only.

- These files are not used by the application runtime.
- They are not part of the production request path.
- They exist to show what a simpler LangChain-informed orchestration style could look like for this repo's problem shape.

Current production orchestration lives in:

- `src/api/service.py`
- `src/agents/core/manager.py`
- `src/agents/planner/service.py`
- `src/agents/specialists/service.py`

The example here is for design comparison and practice only.

Files:

- `illustrative_pipeline.py`: the simpler deterministic baseline
- `illustrative_pipeline_with_mcp_seam.py`: the same baseline with a small MCP-inspired tool seam added
