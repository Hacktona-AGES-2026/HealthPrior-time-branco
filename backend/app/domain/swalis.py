"""Classificação SWALIS por pontos + regras. Função pura: mesma entrada, mesma classe.

1. PONTOS: critérios que alimentam os eixos, cada um com a evidência citada. Vêm de campos
   estruturados (CID, dor, limitação, eventos), de palavra-chave com negação e do Jev (LLM),
   que aponta a frase onde o ponto aparece.
2. DECISÃO: as regras cruzam os pontos na tabela SWALIS. Cada eixo é o MAIOR nível entre os
   pontos, então o Jev pode subir a classe, mas nunca baixar do que as regras dariam sozinhas.

O LLM aponta e cita; quem decide é a tabela, e a classe segue não confirmada até o regulador
(I-04, I-05). Cada motivo carrega a origem, então toda classe é rastreável até a frase/campo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from app.domain.cid import is_lesao_incerta, is_oncologico, normalizar_cid
from app.domain.enums import Classe
from app.domain.models import Evento
from app.domain.texto import buscar_termos, esta_negado, localizar_trecho
from app.domain.urgencia import tem_biopsia_positiva

VERSAO_REGRAS = "swalis-regras-2"

# SW-01: obstrução/instabilidade. SW-02: CID com complicação sintomática.
CID_PROGRESSAO_3 = frozenset({"K400", "K403", "K420", "K430", "N132", "I200"})
CID_SINTOMA_2 = frozenset({"I832", "K800"})


class CategoriaSinal(str, Enum):
    """Pontos que derivam o SWALIS. Cada um alimenta um eixo num nível (`NIVEL_DO_PONTO`)."""

    OBSTRUCAO = "obstrucao"  # obstrução, encarceramento, irredutibilidade
    RISCO_VIDA = "risco_vida"  # sangramento ativo, infecção grave, instabilidade cardiorrespiratória
    PERDA_FUNCAO = "perda_funcao"  # risco de perda de órgão ou função (visão, rim, nervo)
    CANCER_CONFIRMADO = "cancer_confirmado"  # neoplasia maligna confirmada no texto
    SUSPEITA_MALIGNIDADE = "suspeita_malignidade"  # provisório como progressão 1 (Q-SW1)
    DOR_INTENSA = "dor_intensa"  # dor intensa/incapacitante descrita no texto
    SINTOMA_GRAVE = "sintoma_grave"  # acamado, dependente, quedas, úlcera de pressão
    SINTOMA_MODERADO = "sintoma_moderado"  # dor ou limitação moderadas descritas no texto


# Ponto do Jev conta para a classe a partir desta confiança; entre REVISAR e CONTA só vai para
# o regulador revisar (provisório, ajustável; registrar no DECISOES.md ao mudar).
CONFIANCA_CONTA = 0.7
CONFIANCA_REVISAR = 0.4

PROGRESSAO, SINTOMA = "progressao", "sintoma"
NIVEL_DO_PONTO: dict[CategoriaSinal, tuple[str, int]] = {
    CategoriaSinal.OBSTRUCAO: (PROGRESSAO, 3),
    CategoriaSinal.RISCO_VIDA: (PROGRESSAO, 3),
    CategoriaSinal.PERDA_FUNCAO: (PROGRESSAO, 3),
    CategoriaSinal.CANCER_CONFIRMADO: (PROGRESSAO, 2),
    CategoriaSinal.SUSPEITA_MALIGNIDADE: (PROGRESSAO, 1),
    CategoriaSinal.DOR_INTENSA: (SINTOMA, 2),
    CategoriaSinal.SINTOMA_GRAVE: (SINTOMA, 2),
    CategoriaSinal.SINTOMA_MODERADO: (SINTOMA, 1),
}


# Termos do verificador oficial (urgencia._KW_ALARME) separados por eixo. Provisório (D-44):
# a separação é do time, não do SWALIS; ajuste aqui e registre no DECISOES.md.
TERMOS: dict[CategoriaSinal, re.Pattern[str]] = {
    CategoriaSinal.OBSTRUCAO: re.compile(r"encarcer|estrangul|suboclus"),
    CategoriaSinal.RISCO_VIDA: re.compile(
        r"colangite|icter|pancreatite|enterorragia|melena|hematemese|sepse|transfund|hemoptise|"
        r"retencao de co2|dessaturacao|angina em repouso|sincope|retencao urinaria aguda"
    ),
    CategoriaSinal.PERDA_FUNCAO: re.compile(
        r"hidronefrose|perda de funcao|glaucoma facomorfico|dano neurologico"
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
    origem: str = "regra"  # "regra" (palavra-chave) | "llm" (Jev)
    confianca: float = 1.0  # probabilidade do Jev; palavra-chave = 1.0


@dataclass
class Eixo:
    nivel: int
    motivos: list[str] = field(default_factory=list)


@dataclass
class ClassificacaoSwalis:
    classe: Classe
    progressao: Eixo
    sintoma: Eixo
    sinais: list[SinalTexto]  # pontos que contaram
    revisar: list[SinalTexto] = field(default_factory=list)  # pontos incertos, sem efeito na classe

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


def _citacao(s: SinalTexto) -> str:
    origem = "palavra-chave" if s.origem == "regra" else f"Jev p={s.confianca:.2f}"
    return f'"{s.trecho}" → {s.categoria.value} ({origem})'


def _no_maior_nivel(candidatos: list[tuple[int, str]], padrao: Eixo) -> Eixo:
    if not candidatos:
        return padrao
    nivel = max(n for n, _ in candidatos)
    return Eixo(nivel, list(dict.fromkeys(m for n, m in candidatos if n == nivel)))


def _pontos_do_eixo(sinais: list[SinalTexto], eixo: str) -> list[tuple[int, SinalTexto]]:
    return [(NIVEL_DO_PONTO[s.categoria][1], s) for s in sinais if NIVEL_DO_PONTO[s.categoria][0] == eixo]


def eixo_progressao(cid: str, eventos: list[Evento], sinais: list[SinalTexto]) -> Eixo:
    """SW-01. 3 obstrução/risco de vida; 2 câncer ou biópsia positiva; 1 lesão incerta/C44/suspeita."""
    c = normalizar_cid(cid)
    pele = c.startswith("C44")
    candidatos: list[tuple[int, str]] = []
    if c in CID_PROGRESSAO_3:
        candidatos.append((3, f"CID de obstrução/instabilidade {cid}"))
    if pele:
        candidatos.append((1, f"carcinoma de pele {cid}"))
    elif is_oncologico(c):
        candidatos.append((2, f"neoplasia maligna pelo CID {cid}"))
    # C44 (pele não melanoma) é B mesmo com biópsia/texto de câncer: só confirmam o próprio C44.
    if tem_biopsia_positiva(eventos) and not pele:
        candidatos.append((2, "biópsia positiva"))
    if is_lesao_incerta(c):
        candidatos.append((1, f"lesão de comportamento incerto {cid}"))
    for nivel, s in _pontos_do_eixo(sinais, PROGRESSAO):
        if pele and s.categoria == CategoriaSinal.CANCER_CONFIRMADO:
            nivel = 1
        candidatos.append((nivel, _citacao(s)))
    return _no_maior_nivel(candidatos, Eixo(0, ["nenhum risco de progressão registrado"]))


def eixo_sintoma(cid: str, dor: int | None, limitacao: str | None,
                 sinais: list[SinalTexto]) -> Eixo:
    """SW-02. 2 dor 7–10/limitação grave/CID complicado/texto; 1 dor 4–6/moderada/sem dado."""
    lim = (limitacao or "").strip().lower() or None
    candidatos: list[tuple[int, str]] = []
    if dor is not None and dor >= 7:
        candidatos.append((2, f"dor EVA {dor}"))
    elif dor is not None and dor >= 4:
        candidatos.append((1, f"dor EVA {dor}"))
    if lim == "grave":
        candidatos.append((2, "limitação funcional grave"))
    elif lim == "moderada":
        candidatos.append((1, "limitação funcional moderada"))
    if normalizar_cid(cid) in CID_SINTOMA_2:
        candidatos.append((2, f"CID com complicação {cid}"))
    # Nunca rebaixar por falta de dado: sem dor ou sem limitação, não dá para afirmar 0.
    if dor is None:
        candidatos.append((1, "dor não informada"))
    if lim is None:
        candidatos.append((1, "limitação não informada"))
    candidatos += [(nivel, _citacao(s)) for nivel, s in _pontos_do_eixo(sinais, SINTOMA)]
    return _no_maior_nivel(candidatos, Eixo(0, [f"dor EVA {dor}, limitação {lim}"]))


_SEM_PROGRESSAO = {0: Classe.D, 1: Classe.C, 2: Classe.B}
_POR_PROGRESSAO = {3: Classe.A1, 2: Classe.A2, 1: Classe.B}


def cruzar_eixos(progressao: int, sintoma: int) -> Classe:
    """SW-03. Progressão 3→A1, 2→A2, 1→B; progressão 0 → D, C ou B conforme o sintoma."""
    return _POR_PROGRESSAO.get(progressao) or _SEM_PROGRESSAO[sintoma]


def classificar(cid: str, dor: int | None, limitacao: str | None, eventos: list[Evento],
                sinais: list[SinalTexto]) -> ClassificacaoSwalis:
    contam = [s for s in sinais if s.confianca >= CONFIANCA_CONTA]
    revisar = [s for s in sinais if CONFIANCA_REVISAR <= s.confianca < CONFIANCA_CONTA]
    prog = eixo_progressao(cid, eventos, contam)
    sint = eixo_sintoma(cid, dor, limitacao, contam)
    return ClassificacaoSwalis(cruzar_eixos(prog.nivel, sint.nivel), prog, sint, contam, revisar)
