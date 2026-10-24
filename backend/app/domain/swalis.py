"""Classificação SWALIS por regras (SW-01..SW-04). Função pura: mesma entrada, mesma classe.

Dois eixos cruzados numa tabela:
- Progressão (0..3): a doença piora se o paciente esperar?
- Sintoma (0..2): quanto o paciente sofre hoje?

Só sinais por palavra-chave (com negação) mudam a classe. Sinais que só o LLM achou viram
alerta para o regulador, sem efeito na classe: a categoria vem do LLM e decidir a classe por ela
seria o LLM decidindo (I-05).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.domain.cid import is_lesao_incerta, is_oncologico, normalizar_cid
from app.domain.enums import Classe
from app.domain.models import Evento
from app.domain.texto import buscar_termos, esta_negado, localizar_trecho, normalizar_texto
from app.domain.urgencia import tem_biopsia_positiva

VERSAO_REGRAS = "swalis-regras-1"

# SW-01: obstrução/instabilidade. SW-02: CID com complicação sintomática.
CID_PROGRESSAO_3 = frozenset({"K400", "K403", "K420", "K430", "N132", "I200"})
CID_SINTOMA_2 = frozenset({"I832", "K800"})


class CategoriaSinal(str, Enum):
    RISCO_VIDA = "risco_vida"  # progressão 3
    SUSPEITA_MALIGNIDADE = "suspeita_malignidade"  # progressão 1 (provisório, Q-SW1)
    SINTOMA_GRAVE = "sintoma_grave"  # sintoma 2


# Termos do verificador oficial (urgencia._KW_ALARME) separados por eixo. Provisório (D-28):
# a separação é do time, não do SWALIS; ajuste aqui e registre no DECISOES.md.
TERMOS: dict[CategoriaSinal, re.Pattern[str]] = {
    CategoriaSinal.RISCO_VIDA: re.compile(
        r"encarcer|estrangul|suboclus|colangite|icter|pancreatite|enterorragia|melena|hematemese|"
        r"sepse|hidronefrose|perda de funcao|transfund|hemoptise|glaucoma facomorfico|"
        r"retencao de co2|dano neurologico|dessaturacao|angina em repouso|sincope|"
        r"retencao urinaria aguda"
    ),
    CategoriaSinal.SUSPEITA_MALIGNIDADE: re.compile(
        r"perda ponderal|disfagia|rouquidao|linfonodo.*(?:fixo|palpavel)|sangramento espontaneo|"
        r"crescimento rapido|psa em elevacao|massa anexial|ca-125"
    ),
    CategoriaSinal.SINTOMA_GRAVE: re.compile(r"acamad|ulcera de pressao|quedas de repeticao"),
}


@dataclass(frozen=True)
class SinalTexto:
    categoria: CategoriaSinal
    termo: str
    trecho: str  # citação literal do texto
    fonte: str  # "justificativa_clinica" | "observacoes"
    origem: str = "regra"  # "regra" (palavra-chave, muda a classe) | "llm" (só alerta)


@dataclass
class Eixo:
    nivel: int
    motivos: list[str] = field(default_factory=list)


@dataclass
class ClassificacaoSwalis:
    classe: Classe
    progressao: Eixo
    sintoma: Eixo
    sinais: list[SinalTexto]

    def justificativa(self) -> str:
        return (f"SWALIS {self.classe.value}: progressão {self.progressao.nivel} "
                f"({'; '.join(self.progressao.motivos)}), sintoma {self.sintoma.nivel} "
                f"({'; '.join(self.sintoma.motivos)})")


def sinais_por_palavra_chave(texto: str | None, fonte: str) -> list[SinalTexto]:
    """Sinais de alarme por palavra-chave, já descartando os negados (SW-04)."""
    sinais = []
    for categoria, padrao in TERMOS.items():
        for oc in buscar_termos(texto, padrao):
            if not oc.negado:
                sinais.append(SinalTexto(categoria, oc.termo, oc.trecho, fonte))
    return sinais


def validar_sinal_llm(sinal: SinalTexto, texto: str | None) -> bool:
    """Aceita o sinal do LLM só se o trecho existe literalmente no texto e não está negado."""
    span = localizar_trecho(texto, sinal.trecho)
    # Negação medida no fim do trecho: pega "sem" antes dele e dentro dele ("Sem sinais de…").
    return span is not None and not esta_negado(texto or "", span[1])


def coberto_por_palavra_chave(sinal: SinalTexto) -> bool:
    """O trecho do LLM já contém um termo da categoria (a palavra-chave já pegou)."""
    return bool(TERMOS[sinal.categoria].search(normalizar_texto(sinal.trecho)))


def alerta_redundante(sinal: SinalTexto, cid: str) -> bool:
    """Suspeita de malignidade em quem já tem câncer pelo CID não acrescenta nada (já é A2/B)."""
    return sinal.categoria == CategoriaSinal.SUSPEITA_MALIGNIDADE and is_oncologico(cid)


def _cite(sinais: list[SinalTexto], categoria: CategoriaSinal) -> list[str]:
    return [f'"{s.trecho}" ({s.origem})' for s in sinais if s.categoria == categoria]


def eixo_progressao(cid: str, eventos: list[Evento], sinais: list[SinalTexto]) -> Eixo:
    """SW-01. 3 obstrução/risco de vida; 2 câncer ou biópsia positiva; 1 lesão incerta ou C44."""
    c = normalizar_cid(cid)
    motivos: list[str] = []
    if c in CID_PROGRESSAO_3:
        motivos.append(f"CID de obstrução/instabilidade {cid}")
    motivos += _cite(sinais, CategoriaSinal.RISCO_VIDA)
    if motivos:
        return Eixo(3, motivos)
    # C44 (pele não melanoma) é B mesmo com biópsia: a biópsia só confirma o próprio C44.
    if c.startswith("C44"):
        return Eixo(1, [f"carcinoma de pele {cid}"])
    if is_oncologico(c):
        return Eixo(2, [f"neoplasia maligna pelo CID {cid}"])
    if tem_biopsia_positiva(eventos):
        return Eixo(2, ["biópsia positiva"])
    if is_lesao_incerta(c):
        motivos.append(f"lesão de comportamento incerto {cid}")
    motivos += _cite(sinais, CategoriaSinal.SUSPEITA_MALIGNIDADE)
    if motivos:
        return Eixo(1, motivos)
    return Eixo(0, ["nenhum risco de progressão registrado"])


def eixo_sintoma(cid: str, dor: int | None, limitacao: str | None,
                 sinais: list[SinalTexto]) -> Eixo:
    """SW-02. 2 dor 7–10/limitação grave/CID complicado/alarme; 1 dor 4–6/moderada/sem dado."""
    lim = (limitacao or "").strip().lower() or None
    motivos: list[str] = []
    if dor is not None and dor >= 7:
        motivos.append(f"dor EVA {dor}")
    if lim == "grave":
        motivos.append("limitação funcional grave")
    if normalizar_cid(cid) in CID_SINTOMA_2:
        motivos.append(f"CID com complicação {cid}")
    motivos += _cite(sinais, CategoriaSinal.SINTOMA_GRAVE)
    if motivos:
        return Eixo(2, motivos)
    if dor is not None and dor >= 4:
        motivos.append(f"dor EVA {dor}")
    if lim == "moderada":
        motivos.append("limitação funcional moderada")
    # Nunca rebaixar por falta de dado: sem dor ou sem limitação, não dá para afirmar 0.
    if dor is None:
        motivos.append("dor não informada")
    if lim is None:
        motivos.append("limitação não informada")
    if motivos:
        return Eixo(1, motivos)
    return Eixo(0, [f"dor EVA {dor}, limitação {lim}"])


_SEM_PROGRESSAO = {0: Classe.D, 1: Classe.C, 2: Classe.B}
_POR_PROGRESSAO = {3: Classe.A1, 2: Classe.A2, 1: Classe.B}


def cruzar_eixos(progressao: int, sintoma: int) -> Classe:
    """SW-03. Progressão 3→A1, 2→A2, 1→B; progressão 0 → D, C ou B conforme o sintoma."""
    return _POR_PROGRESSAO.get(progressao) or _SEM_PROGRESSAO[sintoma]


def classificar(cid: str, dor: int | None, limitacao: str | None, eventos: list[Evento],
                sinais: list[SinalTexto]) -> ClassificacaoSwalis:
    sinais = [s for s in sinais if s.origem == "regra"]  # I-05: LLM não move a classe
    prog = eixo_progressao(cid, eventos, sinais)
    sint = eixo_sintoma(cid, dor, limitacao, sinais)
    return ClassificacaoSwalis(cruzar_eixos(prog.nivel, sint.nivel), prog, sint, sinais)
