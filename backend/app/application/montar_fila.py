"""Caso de uso: montar a fila priorizada (camadas + score) a partir das solicitações."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Protocol

from app.domain.cid import is_oncologico
from app.domain.enums import PRAZO_MAXIMO_DIAS, Classe, ClasseStatus, StatusFila
from app.domain.models import Evento, ItemRanking, LinhaFila, ResultadoScore, Solicitacao
from app.domain.ranking import ordenar_fila
from app.domain.urgencia import (
    SinaisUrgencia,
    is_urgente,
    motivos_sintomas,
    motivos_urgencia,
    tem_biopsia_positiva,
    tem_evento_de_piora_na_espera,
)

__all__ = ["LinhaFila", "Scorer", "linhas_para_dicts", "montar_fila", "montar_justificativa"]


class Scorer(Protocol):
    versao_regras: str

    def calcular(self, solicitacao: Solicitacao, eventos: list[Evento]) -> ResultadoScore: ...


def _texto_motivo(codigo: str, sol: Solicitacao) -> str:
    textos = {
        "cid_complicacao": f"CID de complicação {sol.cid_principal}",
        "evento_piora": "evento de piora durante a espera",
        "biopsia_positiva": "biópsia positiva com CID não oncológico — revisar CID",
        "sinal_alarme": "sinal de alarme na justificativa clínica",
        "dor": f"dor EVA {sol.intensidade_dor_eva}",
        "limitacao": f"limitação funcional {sol.limitacao_funcional}",
    }
    return textos[codigo]


def montar_justificativa(
    camada: int,
    solicitacao: Solicitacao,
    motivos: list[str],
    classe: str,
    prazo_dias: int,
    versao_regras: str,
    dias_em_fila: int,
    pct_prazo: float,
    editado_manualmente: bool = False,
    sintomas: list[str] | None = None,
    eixos: list[str] | None = None,
    fatores: list[str] | None = None,
    score: float | None = None,
    sem_relacao: list[str] | None = None,
) -> str:
    """Gera a justificativa legível em português para uma linha da fila."""
    if camada == 1:
        base = f"Camada 1: oncológico pelo CID {solicitacao.cid_principal}."
    elif camada == 2:
        lista = "; ".join(_texto_motivo(m, solicitacao) for m in motivos)
        base = f"Camada 2: urgente ({lista})."
    else:
        base = "Camada 3: sem sinais clínicos de urgência."
    if sintomas:
        base += " Sintomas: " + "; ".join(_texto_motivo(s, solicitacao) for s in sintomas) + "."
    if eixos:
        base += " SWALIS: " + "; ".join(eixos) + "."
    texto = (f"{base} Classe {classe} (prazo {prazo_dias} dias, regras {versao_regras}); "
             f"{dias_em_fila} dias em fila, {pct_prazo:g}% do prazo.")
    if sem_relacao:
        texto += " Não contam como piora (sem relação com a cirurgia): " + "; ".join(sem_relacao) + "."
    if fatores and score is not None and score != pct_prazo:
        texto += f" Fatores: {'; '.join(fatores)}; score {score:g}."
    if editado_manualmente:
        texto += " Editado manualmente pelo regulador."
    return texto


def classe_e_score_efetivos(sol: Solicitacao, res: ResultadoScore,
                            ref_date: date) -> tuple[Classe, float, float]:
    """(classe, score, % do prazo) usados na ordenação (C-10).

    Classe: a do regulador (editar/manter); senão a confirmada (aprovar); senão a vigente
    congelada por evento; senão a do SWALIS (só vale até a primeira mudança, carga = D-01).
    Assim nenhuma classe sugerida depois da carga vale sem decisão humana (I-04, C-08).
    O % do prazo segue o prazo da classe efetiva; score editado continua envelhecendo a partir
    da edição, no ritmo do prazo da classe.
    """
    confirmada = sol.classe_confirmada if sol.classe_status == ClasseStatus.CONFIRMADA else None
    classe = sol.classe_medico or confirmada or sol.classe_vigente or res.classe_sistema
    prazo = PRAZO_MAXIMO_DIAS[classe]
    dias = (ref_date - sol.data_entrada_fila).days
    if classe == res.classe_sistema:
        pct = res.pct_prazo_consumido
        if sol.score_medico is None:
            return classe, res.score_sistema, pct
    else:
        pct = round(100 * dias / prazo, 1)
    if sol.score_medico is None:
        # Os fatores de comorbidade e idade são do paciente, não da classe: valem também aqui.
        return classe, round(pct * res.fator_contexto, 1), pct
    desde = max(0, (ref_date - sol.editado_em.date()).days) if sol.editado_em else 0
    return classe, round(sol.score_medico + 100 * desde / prazo, 1), pct


def montar_fila(
    solicitacoes: list[Solicitacao],
    eventos_por_solicitacao: dict[str, list[Evento]],
    scorer: Scorer,
    ref_date: date,
) -> list[LinhaFila]:
    """Calcula score, camada e posição de cada solicitação ativa."""
    contexto: dict[str, tuple[Solicitacao, ResultadoScore, list[str], list[str], float, Classe, float]] = {}
    itens: list[ItemRanking] = []
    for sol in solicitacoes:
        if sol.status_fila != StatusFila.ATIVA:
            continue
        eventos = eventos_por_solicitacao.get(sol.solicitacao_id, [])
        # O scorer anota os eventos (ex.: PS sem relação com a cirurgia) antes da urgência abaixo,
        # que lê os mesmos objetos: a camada e a classe usam a mesma leitura dos eventos.
        res = scorer.calcular(sol, eventos)
        classe, score, pct = classe_e_score_efetivos(sol, res, ref_date)
        sinais = SinaisUrgencia(
            cid_norm=sol.cid_norm,
            intensidade_dor_eva=sol.intensidade_dor_eva,
            limitacao_funcional=sol.limitacao_funcional,
            tem_evento_de_piora=tem_evento_de_piora_na_espera(eventos, sol.data_entrada_fila),
            justificativa_clinica=sol.justificativa_clinica,
            tem_biopsia_positiva=tem_biopsia_positiva(eventos),
        )
        # I-09: o CID manda. Se o `oncologico` gravado estiver desatualizado (flags não
        # recalculadas), um câncer não pode cair fora da camada 1.
        oncologico = sol.oncologico or is_oncologico(sol.cid_principal)
        itens.append(ItemRanking(sol.solicitacao_id, oncologico, is_urgente(sinais),
                                 score, sol.data_entrada_fila))
        contexto[sol.solicitacao_id] = (sol, res, motivos_urgencia(sinais),
                                        motivos_sintomas(sinais), score, classe, pct)

    linhas: list[LinhaFila] = []
    for item in ordenar_fila(itens):
        sol, res, motivos, sintomas, score, classe, pct = contexto[item.solicitacao_id]
        classe_txt = classe.value
        prazo = PRAZO_MAXIMO_DIAS[classe]
        dias = (ref_date - sol.data_entrada_fila).days
        camada = int(item.camada)
        linhas.append(LinhaFila(
            solicitacao_id=sol.solicitacao_id,
            posicao=item.posicao,
            justificativa=montar_justificativa(camada, sol, motivos, classe_txt, prazo,
                                               res.versao_regras, dias,
                                               pct, sol.editado_manualmente,
                                               sintomas=sintomas,
                                               eixos=[m.evidencia for m in res.motivos
                                                      if m.sinal.startswith("eixo_")],
                                               fatores=[m.evidencia for m in res.motivos
                                                        if m.sinal.startswith("fator_")
                                                        and float(m.ref or 1) != 1.0],
                                               score=score,
                                               sem_relacao=[f"{m.evidencia} ({m.ref})" for m in res.motivos
                                                            if m.sinal == "evento_sem_relacao"]),
            camada=camada,
            classe=classe_txt,
            pct_prazo_consumido=pct,
            dias_em_fila=dias,
            score_efetivo=score,
            editado_manualmente=sol.editado_manualmente,
            versao_regras=res.versao_regras,
        ))
    return linhas


def linhas_para_dicts(linhas: list[LinhaFila]) -> list[dict]:
    """Converte as linhas para dicts na ordem de colunas esperada pelo exportador."""
    return [asdict(l) for l in linhas]
