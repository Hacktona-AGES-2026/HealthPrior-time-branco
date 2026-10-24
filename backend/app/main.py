from typing import Dict

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app import config
from app.db import get_engine
from app.loader import CargaError, carga

app = FastAPI(title="HealthPrior", version="0.1.0")


class TableResultOut(BaseModel):
    lido: int
    inseridos: int
    atualizados: int


@app.exception_handler(CargaError)
def carga_error_handler(_, exc: CargaError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"erro": "CARGA_INVALIDA", "mensagem": str(exc)})


@app.post("/admin/carga", response_model=Dict[str, TableResultOut])
def post_carga():
    """Carga inicial (US-01). Idempotente: repetir não duplica registros."""
    return carga(get_engine(), config.DATA_DIR)
