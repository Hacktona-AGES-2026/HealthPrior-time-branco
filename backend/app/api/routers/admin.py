"""US-01, US-16 · Operações administrativas (disparo manual para a demo)."""
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/carga")
def carga():
    raise NotImplementedError("US-01: POST /admin/carga (use também: python -m app.cli carga)")


@router.post("/atualizacao-diaria")
def atualizacao_diaria():
    raise NotImplementedError("US-16: POST /admin/atualizacao-diaria")
