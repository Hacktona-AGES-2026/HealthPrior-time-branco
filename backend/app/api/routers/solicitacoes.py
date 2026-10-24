"""US-21 · Detalhe e explicação do paciente."""
from fastapi import APIRouter

from app.api import mocks, schemas
from app.config import settings

router = APIRouter(prefix="/solicitacoes", tags=["solicitacoes"])


@router.get("/{solicitacao_id}", response_model=schemas.SolicitacaoDetalheOut,
            responses={404: {"model": schemas.Erro}})
def obter_solicitacao(solicitacao_id: str):
    if settings.use_mocks:
        return mocks.DETALHE.model_copy(update={"solicitacao_id": solicitacao_id})
    raise NotImplementedError("US-21: GET /solicitacoes/{id}")
