from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.application.gerar_propostas import GerarPropostas
from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado
from app.domain.models import Decisao, Solicitacao

REF = datetime(2026, 10, 24, tzinfo=timezone.utc)
M = MotivoCodificado


class Fakes:
    def __init__(self, decisoes, sols, decididos=()):
        self.decs, self.sols, self.decididos = decisoes, sols, set(decididos)
        self.gravadas, self.commits = None, 0

    def listar_todas(self): return self.decs
    def listar(self, apenas_ativas=True): return self.sols
    def ids_decididos(self): return self.decididos
    def substituir_geradas(self, propostas, gerada_em): self.gravadas = propostas
    def confirmar(self): self.commits += 1


class Clf:
    def classificar(self, texto):
        return M.PIORA_FUNCIONAL if "piora" in texto else None


def _dec(i, motivo=M.PS_RECORRENTE, proc="PROC004", just="texto", acao=AcaoDecisao.EDITAR,
         de=Classe.C, para=Classe.B):
    return Decisao(f"D{i:03d}", f"S{i}", f"reg-0{i % 3 + 1}", acao, REF - timedelta(days=5), de, para,
                   motivo_codificado=motivo, justificativa=just, procedimento_id=proc)


def _sol(i, proc="PROC004", cid="K80.1"):
    return Solicitacao(f"S{i}", f"P{i}", proc, cid, REF.date(), cid_norm=cid)


def _uc(f, clf=None):
    return GerarPropostas(f, f, f, f, REF, classificador=clf, relogio=lambda: REF)


def test_gera_e_confirma():
    f = Fakes([_dec(i) for i in range(5)] + [_dec(9, acao=AcaoDecisao.APROVAR)], [])
    r = _uc(f).executar()
    assert (r.analisadas, r.consideradas, len(r.propostas), f.commits) == (6, 5, 1, 1)
    assert f.gravadas == r.propostas


def test_outro_reclassificado_e_sem_classificador():
    decs = [_dec(i, M.PIORA_FUNCIONAL) for i in range(4)] + [_dec(4, M.OUTRO, just="piora funcional"),
                                                           _dec(5, M.OUTRO, just="sei lá")]
    r = _uc(Fakes(decs, []), Clf()).executar()
    assert (r.outros_reclassificados, r.outros_sem_grupo, r.consideradas) == (1, 1, 5)
    assert len(r.propostas) == 1 and r.propostas[0].n_casos == 5
    r2 = _uc(Fakes(decs, [])).executar()
    assert (r2.outros_reclassificados, r2.outros_sem_grupo, r2.propostas) == (0, 2, [])


def test_ids_decididos_pulados():
    f = Fakes([_dec(i) for i in range(5)], [], decididos={"PROP-PROC004-ps_recorrente-C-B"})
    r = _uc(f).executar()
    assert r.propostas == [] and f.gravadas == []


def test_procedimento_vindo_da_solicitacao_e_descarte_onco():
    decs = [_dec(i, proc=None, de=Classe.B, para=Classe.C) for i in range(5)]
    sols = [_sol(i, "PROC018", "C54.1") for i in range(5)]
    r = _uc(Fakes(decs, sols)).executar()
    assert r.propostas == [] and len(r.descartadas) == 1
    assert r.descartadas[0].procedimento_id == "PROC018"
    assert r.descartadas[0].motivo_descarte
