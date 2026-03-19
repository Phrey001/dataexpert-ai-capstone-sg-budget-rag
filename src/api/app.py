"""FastAPI app exposing orchestration endpoints."""

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.agents.specialists.service import MCPReadinessError

from .schemas import AskRequest, AskResponse, HealthResponse
from .service import AgentAPIService

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


def create_app(service: AgentAPIService | None = None) -> FastAPI:
    app = FastAPI(title="SG Budget Agent API", version="0.1.0")
    app.state.agent_service = service
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    def get_service() -> AgentAPIService:
        if app.state.agent_service is None:
            app.state.agent_service = AgentAPIService()
        return app.state.agent_service

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(str(FRONTEND_DIR / "index.html"))

    @app.get("/health", response_model=HealthResponse)
    def health(agent_service: AgentAPIService = Depends(get_service)) -> HealthResponse:
        return agent_service.health()

    @app.post("/ask", response_model=AskResponse)
    def ask(
        payload: AskRequest,
        agent_service: AgentAPIService = Depends(get_service),
    ) -> AskResponse:
        try:
            return agent_service.ask(payload)
        except MCPReadinessError as exc:
            raise HTTPException(status_code=503, detail=f"MCP readiness failed: {exc}") from exc
        except Exception as exc:
            # Avoid leaking internal error details to clients.
            raise HTTPException(status_code=500, detail="Internal server error.") from exc

    return app


app = create_app()
