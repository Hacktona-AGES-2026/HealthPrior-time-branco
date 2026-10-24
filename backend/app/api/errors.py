"""Converte DomainError no formato padrão {"erro", "mensagem"}."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.errors import DomainError


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_http,
                            content={"erro": exc.codigo, "mensagem": exc.mensagem})

    @app.exception_handler(NotImplementedError)
    async def _nao_implementado(_: Request, exc: NotImplementedError) -> JSONResponse:
        return JSONResponse(status_code=501,
                            content={"erro": "NAO_IMPLEMENTADO", "mensagem": str(exc)})
