"""US-21 · Detalhe e explicação do paciente."""
from fastapi import APIRouter, Depends

from app.api import mocks, schemas
from app.api.deps import get_detalhar_solicitacao
from app.application.detalhar_solicitacao import DetalharSolicitacao, DetalheSolicitacao
from app.config import settings

router = APIRouter(prefix="/solicitacoes", tags=["solicitacoes"])


@router.get("/{solicitacao_id}", response_model=schemas.SolicitacaoDetalheOut,
            responses={404: {"model": schemas.Erro}})
def obter_solicitacao(solicitacao_id: str,
                      detalhar: DetalharSolicitacao = Depends(get_detalhar_solicitacao)):
    if settings.use_mocks:
        return mocks.DETALHE.model_copy(update={"solicitacao_id": solicitacao_id})
    return _para_schema(detalhar.executar(solicitacao_id))


def _para_schema(d: DetalheSolicitacao) -> schemas.SolicitacaoDetalheOut:
    s, sc = d.solicitacao, d.score
    return schemas.SolicitacaoDetalheOut(
        solicitacao_id=s.solicitacao_id, paciente_id=s.paciente_id, nome_paciente=s.nome_paciente,
        idade=s.idade, sexo=s.sexo, municipio=s.municipio, procedimento=s.procedimento or "",
        cid=s.cid_principal, cid_descricao=s.cid_descricao, status_fila=s.status_fila,
        posicao=d.posicao, camada=d.camada, camada_motivo=d.camada_motivo,
        score=schemas.ScoreOut(
            classe_sistema=sc.classe_sistema, score_sistema=sc.score_sistema,
            classe_medico=sc.classe_medico, score_medico=sc.score_medico,
            score_efetivo=sc.score_efetivo, prazo_dias=sc.prazo_dias,
            pct_prazo_consumido=sc.pct_prazo_consumido, classe_status=sc.classe_status,
            versao_regras=sc.versao_regras,
            motivos=[schemas.MotivoOut(sinal=m.sinal, evidencia=m.evidencia, fonte=m.fonte,
                                       ref=m.ref, data=m.data) for m in sc.motivos],
        ),
        explicacao=d.explicacao,
        eventos=[schemas.EventoOut(evento_id=e.evento_id, data_evento=e.data_evento,
                                   tipo_evento=e.tipo_evento, resultado=e.resultado,
                                   descricao=e.descricao, historico=e.historico,
                                   duplicado=e.duplicado) for e in d.eventos],
        decisoes=[schemas.DecisaoOut(decisao_id=x.decisao_id, data=x.data, regulador_id=x.regulador_id,
                                     acao=x.acao, classe_decidida=x.classe_decidida,
                                     motivo_codificado=x.motivo_codificado,
                                     justificativa=x.justificativa) for x in d.decisoes],
        pendencias=[schemas.PendenciaResumoOut(pendencia_id=p.pendencia_id, regra=p.regra,
                                               bloqueante=p.bloqueante, status=p.status)
                    for p in d.pendencias],
        alertas=list(s.alertas),
        correcoes=[schemas.CorrecaoOut(campo=c.campo, original=c.original, novo=c.novo,
                                       regra=c.regra) for c in d.correcoes],
    )
