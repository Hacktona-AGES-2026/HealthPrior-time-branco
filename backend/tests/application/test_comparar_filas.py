from datetime import date

from app.application.comparar_filas import CompararFilas
from app.domain.models import Evento, LinhaFila, Solicitacao


class SolRepo:
    def __init__(self, itens):
        self.itens = itens

    def listar(self, apenas_ativas=True):
        return self.itens


class EvRepo:
    def __init__(self, itens):
        self.itens = itens

    def listar_todos(self):
        return self.itens


class FilaRepo:
    def __init__(self, linhas):
        self.linhas = linhas

    def obter_publicada(self):
        return self.linhas


def sol(sid, prio, onco=False, cid="K409", dor=None):
    return Solicitacao(solicitacao_id=sid, paciente_id="P", procedimento_id="X", cid_principal=cid,
                       data_entrada_fila=date(2026, 1, 1), cid_norm=cid, oncologico=onco,
                       prioridade_norm=prio, intensidade_dor_eva=dor)


def linha(sid, pos, camada):
    return LinhaFila(solicitacao_id=sid, posicao=pos, justificativa="x", camada=camada,
                     classe="C", pct_prazo_consumido=0.0, dias_em_fila=0, score_efetivo=0.0,
                     editado_manualmente=False, versao_regras="v")


SOLS = [sol("A", "alta"), sol("B", "media"), sol("C", "baixa", onco=True, cid="C61")]


def caso(linhas):
    return CompararFilas(SolRepo(SOLS), EvRepo([]), FilaRepo(linhas), date(2026, 10, 23),
                         ["C", "A", "NAO-EXISTE"])


def test_sem_publicacao():
    r = caso([]).executar()
    assert r.publicada is False and r.depois is None
    assert r.antes.total == 3
    assert r.antes.violacoes_regra_ouro == 1  # C (onco) vem depois de A e B sem urgência
    assert [(d.solicitacao_id, d.posicao_antes, d.posicao_depois) for d in r.destaques] == [
        ("C", 3, None), ("A", 1, None), ("NAO-EXISTE", None, None)]


def test_com_publicacao():
    r = caso([linha("C", 1, 1), linha("A", 2, 3), linha("B", 3, 3)]).executar()
    assert r.publicada is True
    assert r.depois.total == 3 and r.depois.violacoes_regra_ouro == 0
    assert r.depois.posicao_mediana_oncologicos == 1.0
    d = {x.solicitacao_id: x for x in r.destaques}
    assert (d["C"].posicao_antes, d["C"].posicao_depois, d["C"].camada_depois) == (3, 1, 1)
    assert (d["A"].posicao_antes, d["A"].posicao_depois, d["A"].camada_depois) == (1, 2, 3)
    assert d["NAO-EXISTE"].posicao_depois is None
