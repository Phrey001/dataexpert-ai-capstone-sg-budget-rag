"""Tool-name mapping helpers for MCP-backed specialists."""

from ..core.config import AgentConfig
from .contracts import MCPToolNames


def resolve_tool_names(config: AgentConfig) -> MCPToolNames:
    return {
        "retrieve": config.mcp_retrieve_tool,
        "rerank": config.mcp_rerank_tool,
        "synthesize": config.mcp_synthesize_tool,
        "reflect": config.mcp_reflect_tool,
    }


def missing_tool_names(tool_names: MCPToolNames) -> list[str]:
    return [name for name, value in tool_names.items() if not value.strip()]
