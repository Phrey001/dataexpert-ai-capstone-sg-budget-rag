"""Typed contracts for MCP tool and search payloads."""

from typing import TypedDict


class MCPToolNames(TypedDict):
    retrieve: str
    rerank: str
    synthesize: str
    reflect: str
