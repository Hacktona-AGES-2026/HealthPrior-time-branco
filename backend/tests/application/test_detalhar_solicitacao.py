"""US-21 · DetalharSolicitacao com repositórios e scorer falsos (sem banco)."""
from __future__ import annotations

from datetime import date

import pytest

from app.application.detalhar_solicitacao import DetalharSolicitacao
from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe, ClasseStatus, StatusFila, StatusPendencia
from app.domain.errors import NaoEncontradoError
from app.domain.models import Correcao, Evento, LinhaFila, Motivo, Pendencia, ResultadoScore, Solicitacao

REF = date(2026, 10, 23)


class SolicitacoesFalsas:
    def __init__(self, *itens):
        self._itens = {s.solicitacao_id: s for s in itens}

    def obter(self, solicitacao_id):
        return self._itens.get(solicitacao_id)


class EventosFalsos:
    def __init__(self, eventos=()):
        self._eventos = list(eventos)

    def listar_por_solicitacao(self, solicitacao_id):
        return [e for e in self._eventos if e.solicitacao_id == solicitacao_id]


class CorrecoesFalsas:
    def __init__(self, correcoes=()):
        self._correcoes = list(correcoes)

    def listar_por_solicitacao(self, solicitacao_id):
        return [c for c in self._correcoes if c.solicitacao_id == solicitacao_id]


class PendenciasFalsas:
    def __init__(self, pendencias=()):
        self._pendencias = list(pendencias)

    def listar_por_solicitacao(self, solicitacao_id):
        return [p for p in self._pendencias if p.solicitacao_id == solicitacao_id]


class FilaFalsa:
    def __init__(self, linhas=()):
        self._linhas = list(linhas)

    def obter_publicada(self):
        return list(self._linhas)


class ScorerFalso:
    versao_regras = "regras-teste"

    def __init__(self, classe=Classe.A2, prazo=21, pct=150.0, score=6276.2, motivos=()):
        self._res = ResultadoScore(classe, prazo, pct, score, list(motivos), self.versao_regras)

    def calcular(self, solicitacao, eventos):
        return self._res


def sol(sid="SOL-1", **kw):
    base = dict(solicitacao_id=sid, paciente_id="PAC-1", procedimento_id="P-1",
                cid_principal="C18.7", data_entrada_fila=date(2023, 1, 1),
                nome_paciente="(sintético)", procedimento="Colectomia", cid_descricao="Neoplasia",
                classe_status=ClasseStatus.SUGERIDA_NAO_CONFIRMADA)
    base.update(kw)
    return Solicitacao(**base)


def linha(sid="SOL-1", posicao=1, camada=1, justificativa="Camada 1: oncológico pelo CID C18.7."):
    return LinhaFila(solicitacao_id=sid, posicao=posicao, justificativa=justificativa, camada=camada,
                     classe="A2", pct_prazo_consumido=150.0, dias_em_fila=1024,
                     score_efetivo=6276.2, editado_manualmente=False, versao_regras="regras-teste")


def caso(solicitacoes, eventos=(), correcoes=(), pendencias=(), linhas=(), scorer=None):
    return DetalharSolicitacao(
        solicitacoes=SolicitacoesFalsas(*solicitacoes), eventos=EventosFalsos(eventos),
        correcoes=CorrecoesFalsas(correcoes), pendencias=PendenciasFalsas(pendencias),
        fila=FilaFalsa(linhas), scorer=scorer or ScorerFalso(), ref_date=REF)


def test_inexistente_levanta_nao_encontrado():
    with pytest.raises(NaoEncontradoError):
        caso([]).executar("SOL-X")


def test_publicado_traz_posicao_camada_e_motivo():
    d = caso([sol()], linhas=[linha()]).executar("SOL-1")
    assert d.posicao == 1
    assert d.camada == 1
    assert d.camada_motivo == "Oncológico pelo CID C18.7"
    assert "Posição 1" in d.explicacao and "C18.7" in d.explicacao


def test_camada_2_usa_primeira_frase_da_justificativa():
    just = "Camada 2: urgente (dor EVA 8). Sintomas: limitação funcional grave."
    d = caso([sol(cid_principal="I50")],
             linhas=[linha(camada=2, justificativa=just)]).executar("SOL-1")
    assert d.camada == 2
    assert d.camada_motivo == "Camada 2: urgente (dor EVA 8)"


def test_nao_publicado_sem_posicao_nem_camada():
    d = caso([sol()], linhas=[]).executar("SOL-1")
    assert d.posicao is None and d.camada is None and d.camada_motivo is None
    assert d.explicacao.startswith("Ainda não está na fila publicada.")


def test_score_efetivo_usa_score_medico_quando_existe():
    s = sol(classe_medico=Classe.B, score_medico=111.0, editado_manualmente=True, editado_por="Silas")
    d = caso([s], scorer=ScorerFalso(score=6276.2)).executar("SOL-1")
    assert d.score.score_sistema == 6276.2
    assert d.score.score_medico == 111.0
    assert d.score.score_efetivo == 111.0
    assert d.score.classe_medico == Classe.B
    assert d.score.prazo_dias == PRAZO_MAXIMO_DIAS[Classe.B]
    assert "editada manualmente por Silas" in d.explicacao


def test_score_efetivo_cai_no_sistema_sem_medico():
    d = caso([sol()], scorer=ScorerFalso(score=6276.2)).executar("SOL-1")
    assert d.score.score_efetivo == 6276.2
    assert d.score.classe_medico is None


def test_suspensa_entra_na_explicacao():
    s = sol(status_fila=StatusFila.SUSPENSA, motivo_status="operou pelo convênio")
    d = caso([s]).executar("SOL-1")
    assert "Solicitação suspensa: operou pelo convênio." in d.explicacao


def test_eventos_ordenados_com_historico_e_duplicado_marcados():
    eventos = [
        Evento("EVT-3", "SOL-1", "PAC-1", date(2025, 11, 27), "contato_telefonico"),
        Evento("EVT-1", "SOL-1", "PAC-1", date(2023, 1, 30), "biopsia", resultado="positivo",
               historico=True),
        Evento("EVT-2", "SOL-1", "PAC-1", date(2024, 9, 17), "exame_imagem", duplicado_de="EVT-9"),
    ]
    d = caso([sol()], eventos=eventos).executar("SOL-1")
    assert [e.evento_id for e in d.eventos] == ["EVT-1", "EVT-2", "EVT-3"]
    assert d.eventos[0].historico is True and d.eventos[0].duplicado is False
    assert d.eventos[1].duplicado is True and d.eventos[1].historico is False


def test_pendencias_e_correcoes_sao_repassadas():
    corr = [Correcao("SOL-1", "flag_oncologico", "nao", "sim", "PRE-05"),
            Correcao("SOL-2", "flag_oncologico", "nao", "sim", "PRE-05")]
    pend = [Pendencia("PEN-0001", "SOL-1", "PRE-25", "Fontes contraditórias", True,
                      [Motivo("ponto", "texto", "evento", ref="EVT-566")], "Ligar",
                      status=StatusPendencia.ABERTA, aberta_em=date(2026, 10, 24))]
    d = caso([sol()], correcoes=corr, pendencias=pend).executar("SOL-1")
    assert [c.regra for c in d.correcoes] == ["PRE-05"]
    assert [p.pendencia_id for p in d.pendencias] == ["PEN-0001"]


def test_detalhe_traz_decisoes_do_regulador():
    from datetime import datetime, timezone
    from app.domain.enums import AcaoDecisao
    from app.domain.models import Decisao

    class DecisoesFalsas:
        def listar_por_solicitacao(self, sid):
            return [Decisao("DEC-1", sid, "REG-1", AcaoDecisao.APROVAR,
                            datetime(2026, 10, 24, tzinfo=timezone.utc), Classe.B, Classe.B)]

    c = caso([sol()], linhas=[linha()])
    c._decisoes = DecisoesFalsas()
    [d] = c.executar("SOL-1").decisoes
    assert (d.decisao_id, d.acao) == ("DEC-1", AcaoDecisao.APROVAR)
