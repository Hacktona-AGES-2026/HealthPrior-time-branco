"""Importação de novas solicitações por CSV (uma linha ou várias)."""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response

from app.api import mocks, schemas
from app.api.deps import get_importar_solicitacoes
from app.application.importar_solicitacoes import ImportarSolicitacoes
from app.config import settings
from app.infrastructure.importacao_csv import modelo_csv

router = APIRouter(prefix="/importacao", tags=["importacao"])
LIMITE_BYTES = 2 * 1024 * 1024


@router.get("/modelo.csv")
def baixar_modelo():
    """Cabeçalho completo (as colunas de `fila_cirurgica.csv`) e uma linha de exemplo."""
    return Response(modelo_csv(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="modelo_solicitacoes.csv"'})


@router.post("/solicitacoes", response_model=schemas.ImportacaoOut,
             responses={422: {"model": schemas.ImportacaoOut}})
async def importar_solicitacoes(request: Request, publicar: bool = Query(default=True),
                                caso: ImportarSolicitacoes = Depends(get_importar_solicitacoes)):
    """Corpo `text/csv`: uma ou várias solicitações novas. Tudo ou nada: se houver erro (422), nada é gravado.

    As que já existem são ignoradas (nunca sobrescritas). Com `publicar=true` (padrão) a fila é republicada.
    """
    if settings.use_mocks:
        return mocks.IMPORTACAO
    bruto = await request.body()
    if len(bruto) > LIMITE_BYTES:
        return _resposta(422, schemas.ImportacaoOut(
            lidas=0, novas=0, ja_existentes=[], novas_ids=[], suspensas=0,
            erros=[schemas.ErroImportacaoOut(linha=1, mensagem="Arquivo maior que 2 MB: divida em partes.")]))
    try:
        texto = bruto.decode("utf-8-sig")
    except UnicodeDecodeError:
        texto = bruto.decode("latin-1")  # planilha salva pelo Excel em português
    r = caso.executar(texto, publicar)
    corpo = schemas.ImportacaoOut(
        lidas=r.lidas, novas=r.novas, ja_existentes=r.ja_existentes,
        erros=[schemas.ErroImportacaoOut(linha=e.linha, campo=e.campo, mensagem=e.mensagem) for e in r.erros],
        novas_ids=r.novas_ids, suspensas=r.suspensas, fila_publicada=r.fila_publicada, total_fila=r.total_fila)
    return _resposta(422 if r.erros else 200, corpo)


def _resposta(status: int, corpo: schemas.ImportacaoOut) -> JSONResponse:
    return JSONResponse(status_code=status, content=corpo.model_dump(mode="json"))
