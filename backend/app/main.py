"""Ponto de entrada da API. Rode: uvicorn app.main:app --reload (dentro de backend/)."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import registrar_handlers
from app.api.routers import admin, aprendizado, decisoes, eventos, fila, inbox, metricas, pendencias, solicitacoes
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="HealthPrior API",
        version="0.1.0",
        description="Priorização auditável da fila cirúrgica. Contrato: docs/user-stories.md §5.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    registrar_handlers(app)
    for r in (fila, solicitacoes, inbox, decisoes, eventos, pendencias, admin, metricas, aprendizado):
        app.include_router(r.router)

    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok", "mocks": settings.use_mocks, "ref_date": settings.ref_date}

    return app


app = create_app()
