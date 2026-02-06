import argparse
import json
from typing import Optional, Sequence

from dotenv import load_dotenv

from .core.config import AgentConfig
from .core.manager import Manager
from .planner.service import PlannerAI
from .specialists.service import MCPReadinessError, Specialists
from .core.types import UserQuery


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run PlannerAI + Manager orchestration from CLI")
    parser.add_argument("--query", required=True, help="User query to orchestrate")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--top-n", type=int, default=None)
    return parser


def apply_cli_overrides(config: AgentConfig, args: argparse.Namespace) -> AgentConfig:
    if args.top_k is not None:
        config.top_k = args.top_k
    if args.top_n is not None:
        config.top_n = args.top_n
    return config


def main(argv: Optional[Sequence[str]] = None) -> int:
    load_dotenv()
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = apply_cli_overrides(AgentConfig.from_env(), args)
    planner = PlannerAI(config)
    manager = Manager(config)

    try:
        specialists = Specialists(config=config)
    except MCPReadinessError as exc:
        print(f"startup_error=MCP readiness failed: {exc}")
        return 2

    result = manager.run(
        user_query=UserQuery(query=args.query),
        planner=planner,
        specialists=specialists,
    )

    print("specialist_mode=real_mcp")
    print(f"confidence={result.confidence:.3f}")
    print(f"state_history={result.state_history}")
    print(f"final_reason={result.trace.get('final_reason')}")
    if result.trace.get("guardrail_event"):
        print(f"guardrail_event={result.trace['guardrail_event']}")
    print("answer:")
    print(result.answer)
    print("trace:")
    print(json.dumps(result.trace, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
