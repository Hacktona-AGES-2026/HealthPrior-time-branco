"""US-13/14 e US-15 com falsos em memória e solicitações reais do dataset (sem banco)."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import date, datetime, timezone

import pytest

from app.application.decidir import ComandoDecisao, DecidirClasse
from app.application.montar_fila import montar_fila
from app.application.registrar_evento import NovoEvento, RegistrarEvento
from app.config import settings
from app.domain.enums import AcaoDecisao, Classe, ClasseStatus, DesfechoEvento, MotivoCodificado
from app.domain.errors import EventoInvalidoError, NaoEncontradoError, OncologicoRebaixadoError
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.swalis_regras import SwalisRegras

AGORA = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
SCORER = SwalisRegras()  # sem LLM: determinístico


@pytest.fixture(scope="module")
def dataset():
    return carregar_do_csv(settings.data_dir)


class Repos:
    """Solicitações, eventos, decisões, pendências, fila e unidade de trabalho em memória."""

    def __init__(self, dataset):
        sols, eventos = dataset
        self.sols = {s.solicitacao_id: copy.deepcopy(s) for s in sols}
        self.eventos = {k: list(v) for k, v in eventos.items()}
        self.decisoes, self.pendencias, self.publicada, self.commits = [], [], [], 0

    # SolicitacaoRepository
    def obter(self, sid):
        return self.sols.get(sid)

    def salvar(self, s):
        self.sols[s.solicitacao_id] = s

    def atualizar_flags(self, ss):
        pass

    # EventoRepository
    def listar_por_solicitacao(self, sid):
        return list(self.eventos.get(sid, []))

    def adicionar(self, e):
        if hasattr(e, "tipo_evento"):
            self.eventos.setdefault(e.solicitacao_id, []).append(e)
        else:
            self.decisoes.append(e)

    # PendenciaRepository
    def salvar_pendencia(self, p):
        p.pendencia_id = f"PEN-{len(self.pendencias) + 1:04d}"
        self.pendencias.append(p)

    # FilaRepository / UoW
    def obter_publicada(self):
        return self.publicada

    def confirmar(self):
        self.commits += 1

    def publicar(self):
        self.publicada = montar_fila(list(self.sols.values()), self.eventos, SCORER, settings.ref_date)


class Pendencias:
    def __init__(self, r):
        self.r = r
        self.salvar = r.salvar_pendencia

    def listar_por_solicitacao(self, sid):
        return [p for p in self.r.pendencias if p.solicitacao_id == sid]


@dataclass
class Publicado:
    publicada: bool = True


class Publicador:
    def __init__(self, r, passa=True):
        self.r, self.passa = r, passa

    def executar(self):
        if self.passa:
            self.r.publicar()
        return Publicado(self.passa)


def _decidir(r, passa=True):
    return DecidirClasse(r, r, r, SCORER, r, Publicador(r, passa), r, lambda: AGORA,
                         settings.ref_date, lambda: "DEC-1")


def _registrar(r):
    return RegistrarEvento(r, r, SCORER, Pendencias(r), r, lambda: "EVT-N1")


def _pos(r, sid):
    return next(l.posicao for l in r.publicada if l.solicitacao_id == sid)


def test_aprovar_confirma_e_devolve_posicoes(dataset):
    r = Repos(dataset)
    r.publicar()
    antes = _pos(r, "SOL-2023-00060")
    res = _decidir(r).executar(ComandoDecisao("SOL-2023-00060", "REG-1", AcaoDecisao.APROVAR))
    s = r.sols["SOL-2023-00060"]
    assert s.classe_status is ClasseStatus.CONFIRMADA and s.classe_confirmada is Classe.D
    assert (res.decisao_id, res.posicao_anterior, res.fila_publicada) == ("DEC-1", antes, True)
    assert res.posicao_nova == _pos(r, "SOL-2023-00060")
    [d] = r.decisoes
    assert (d.acao, d.classe_sugerida, d.classe_decidida, d.regulador_id) == (
        AcaoDecisao.APROVAR, Classe.D, Classe.D, "REG-1")


def test_editar_classe_sobe_o_paciente(dataset):
    r = Repos(dataset)
    r.publicar()
    antes = _pos(r, "SOL-2023-00060")  # K80.2, D pelo SWALIS
    res = _decidir(r).executar(ComandoDecisao(
        "SOL-2023-00060", "REG-1", AcaoDecisao.EDITAR, classe=Classe.B,
        motivo_codificado=MotivoCodificado.PS_RECORRENTE, justificativa="2 PS por cólica biliar"))
    assert res.posicao_nova < antes
    linha = next(l for l in r.publicada if l.solicitacao_id == "SOL-2023-00060")
    assert linha.classe == "B" and linha.editado_manualmente


def test_oncologico_rebaixado_e_bloqueado_sem_gravar(dataset):
    r = Repos(dataset)
    with pytest.raises(OncologicoRebaixadoError):
        _decidir(r).executar(ComandoDecisao(
            "SOL-2025-00149", "REG-1", AcaoDecisao.EDITAR, classe=Classe.D,
            motivo_codificado=MotivoCodificado.OUTRO, justificativa="x"))
    assert r.decisoes == [] and r.commits == 0


def test_verificador_reprova_decisao_fica_e_posicao_nao_muda(dataset):
    r = Repos(dataset)
    r.publicar()
    antes = _pos(r, "SOL-2023-00060")
    res = _decidir(r, passa=False).executar(ComandoDecisao(
        "SOL-2023-00060", "R", AcaoDecisao.EDITAR, classe=Classe.A1,
        motivo_codificado=MotivoCodificado.OUTRO, justificativa="x"))
    assert (res.fila_publicada, res.posicao_nova, r.commits) == (False, antes, 1)


def test_decisao_de_solicitacao_inexistente(dataset):
    with pytest.raises(NaoEncontradoError):
        _decidir(Repos(dataset)).executar(ComandoDecisao("SOL-X", "R", AcaoDecisao.APROVAR))


def test_classe_confirmada_segura_evento_ate_nova_decisao(dataset):
    # C-08: depois de confirmada, a classe da fila só muda com nova decisão do regulador.
    r = Repos(dataset)
    _decidir(r).executar(ComandoDecisao("SOL-2026-00239", "R", AcaoDecisao.APROVAR))
    _registrar(r).executar(NovoEvento("SOL-2026-00239", date(2026, 10, 20), "biopsia", "positivo",
                                      descricao="AP: adenocarcinoma"))
    r.publicar()
    assert next(l for l in r.publicada if l.solicitacao_id == "SOL-2026-00239").classe == "C"


def test_evento_que_muda_a_classe_vai_ao_inbox_e_congela_a_classe(dataset):
    r = Repos(dataset)  # SOL-2026-00239: hérnia K40.9, classe C; biópsia positiva -> A2
    res = _registrar(r).executar(NovoEvento("SOL-2026-00239", date(2026, 10, 20), "biopsia",
                                            "positivo", descricao="AP: adenocarcinoma"))
    assert (res.classe_antes, res.classe_depois, res.desfecho) == (
        Classe.C, Classe.A2, DesfechoEvento.ENVIADO_INBOX)
    assert r.eventos["SOL-2026-00239"][-1].evento_id == "EVT-N1" and r.commits == 1
    # Sem aprovação de um profissional, a fila continua com a classe anterior (I-04).
    assert r.sols["SOL-2026-00239"].classe_vigente is Classe.C
    r.publicar()
    assert next(l for l in r.publicada if l.solicitacao_id == "SOL-2026-00239").classe == "C"
    # O regulador aprova: aí sim vale A2 e a classe deixa de estar congelada.
    _decidir(r).executar(ComandoDecisao("SOL-2026-00239", "REG-1", AcaoDecisao.APROVAR))
    assert next(l for l in r.publicada if l.solicitacao_id == "SOL-2026-00239").classe == "A2"
    assert r.sols["SOL-2026-00239"].classe_vigente is None


def test_mudanca_de_um_nivel_sem_confirmacao_tambem_vai_ao_inbox(dataset):
    # Sem congelamento, a regra do inbox (US-12) só pegaria divergência de 2+ níveis da
    # prioridade manual; com a classe congelada, qualquer mudança espera decisão.
    from app.domain.inbox import entra_no_inbox
    from app.domain.enums import ClasseStatus
    assert entra_no_inbox(Classe.B, ClasseStatus.SUGERIDA_NAO_CONFIRMADA, None, "media", Classe.C)
    assert not entra_no_inbox(Classe.C, ClasseStatus.SUGERIDA_NAO_CONFIRMADA, None, "media", Classe.C)


def test_score_editado_envelhece_a_partir_de_ref_e_nao_do_relogio(dataset):
    r = Repos(dataset)
    _decidir(r).executar(ComandoDecisao(
        "SOL-2023-00060", "R", AcaoDecisao.EDITAR, score=50.0,
        motivo_codificado=MotivoCodificado.OUTRO, justificativa="x"))
    s = r.sols["SOL-2023-00060"]
    assert s.editado_em.date() == settings.ref_date  # não o relógio (AGORA = 24/10)
    assert next(l for l in r.publicada if l.solicitacao_id == "SOL-2023-00060").score_efetivo == 50.0


def test_evento_sem_mudanca_de_classe_so_registra(dataset):
    r = Repos(dataset)
    res = _registrar(r).executar(NovoEvento("SOL-2023-00060", date(2026, 10, 20), "pronto_socorro",
                                            "atendido_liberado", descricao="Cólica biliar"))
    assert res.desfecho is DesfechoEvento.REGISTRADO and res.classe_antes == res.classe_depois


def test_evento_antes_da_entrada_e_historico(dataset):
    r = Repos(dataset)
    _registrar(r).executar(NovoEvento("SOL-2023-00060", date(2019, 1, 1), "pronto_socorro"))
    assert r.eventos["SOL-2023-00060"][-1].historico is True


@pytest.mark.parametrize("resultado,regra", [("desistiu", "PRE-23"),
                                             ("informou_cirurgia_outro_servico", "PRE-21")])
def test_contato_de_saida_abre_pendencia(dataset, resultado, regra):
    r = Repos(dataset)
    res = _registrar(r).executar(NovoEvento("SOL-2023-00060", date(2026, 10, 20),
                                            "contato_telefonico", resultado))
    assert res.desfecho is DesfechoEvento.PENDENCIA and res.pendencia_id == "PEN-0001"
    [p] = r.pendencias
    assert (p.regra, p.bloqueante, p.evidencias[0].ref) == (regra, True, "EVT-N1")
    assert r.sols["SOL-2023-00060"].status_fila.value == "ativa"  # nada sai sem humano (I-03)
    # Segundo contato igual (não duplicado) não abre outra pendência.
    r2 = _registrar(r)
    r2._gerar_id = lambda: "EVT-N2"
    res2 = r2.executar(NovoEvento("SOL-2023-00060", date(2026, 10, 21), "contato_telefonico", resultado))
    assert res2.desfecho is DesfechoEvento.REGISTRADO and len(r.pendencias) == 1


def test_tipo_de_evento_invalido(dataset):
    with pytest.raises(EventoInvalidoError):
        _registrar(Repos(dataset)).executar(NovoEvento("SOL-2023-00060", date(2026, 10, 20), "xpto"))
