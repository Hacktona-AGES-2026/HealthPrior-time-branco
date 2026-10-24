"""Fatores contextuais do score: comorbidade (Charlson) e idade/mortalidade (IRR). Funções puras.

O score da fila é o % do prazo consumido (SWALIS). Os fatores multiplicam esse score para
diferenciar pacientes da mesma classe com o mesmo tempo de espera:

    score = % do prazo × fator_comorbidade × fator_idade

Cada fator fica entre 1,00 e 1,15. Como 1,15 × 1,15 = 1,3225 < 21/15 = 1,40 (a menor razão entre
prazos de classes vizinhas), com o mesmo tempo de espera nenhum fator faz uma classe menos urgente
passar uma mais urgente. Nenhum fator reduz o score (ausência de evidência não é menor risco).
Camadas e regra de ouro não dependem disto (I-01). Base de cada valor: docs/score-e-literatura.md.
Portado de score/apply_comorbidity_multiplier.py e score/apply_idade_mortality_multiplier.py.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from app.domain.cid import normalizar_cid

TETO_FATOR = 1.15
# CDC/NCHS: taxa com menos de 20 óbitos não é confiável (erro padrão relativo >= 23%).
MIN_OBITOS_IRR = 20

# Charlson (1987): pesos das categorias que o dataset permite identificar.
PESOS_CHARLSON: dict[str, int] = {
    "infarto_miocardio": 1,
    "insuficiencia_cardiaca": 1,
    "doenca_pulmonar_cronica": 1,
    "diabetes_sem_complicacao": 1,
    "doenca_renal": 2,
    "tumor_solido": 2,
    "linfoma_leucemia": 2,
    "metastatico": 6,
}

TEXTO_PARA_CHARLSON: dict[str, str] = {
    "icc": "insuficiencia_cardiaca",
    "insuficiencia cardiaca": "insuficiencia_cardiaca",
    "cardiopatia isquemica": "infarto_miocardio",
    "infarto": "infarto_miocardio",
    "dpoc": "doenca_pulmonar_cronica",
    "asma": "doenca_pulmonar_cronica",
    "drc": "doenca_renal",
    "doenca renal cronica": "doenca_renal",
    "dm2": "diabetes_sem_complicacao",
    "diabetes": "diabetes_sem_complicacao",
}

_METASTATICO = ("C77", "C78", "C79", "C80")
_LINFOMA_LEUCEMIA = ("C81", "C82", "C83", "C84", "C85", "C88", "C90", "C91", "C92", "C93",
                     "C94", "C95", "C96")

# Faixas de 3–4 e >= 5 são as do Charlson original; 1 e 2 separadas para graduar.
_FATOR_POR_CHARLSON = ((0, 1.00), (1, 1.03), (2, 1.06), (4, 1.10))

FAIXAS_IDADE = (("0-17", 17), ("18-39", 39), ("40-49", 49), ("50-59", 59), ("60-69", 69),
                ("70-79", 79))


@dataclass(frozen=True)
class CelulaIrr:
    """Uma célula da tabela nacional SIM/IBGE (CID-3 × faixa etária)."""

    irr: float | None
    obitos: int


@dataclass
class Fator:
    valor: float
    regra: str
    descricao: str


@dataclass
class FatoresContexto:
    comorbidade: Fator
    idade: Fator
    categorias_charlson: list[str] = field(default_factory=list)

    @property
    def valor(self) -> float:
        return self.comorbidade.valor * self.idade.valor


def _num(valor: float, casas: int = 2) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _cid3(valor: str | None) -> str | None:
    m = re.match(r"^([A-Z][0-9]{2})", re.sub(r"[^A-Z0-9]", "", (valor or "").upper()))
    return m.group(1) if m else None


def _categoria_do_cid_secundario(valor: str) -> str | None:
    cid = _cid3(valor)
    if cid is None:
        return None
    if cid in _METASTATICO:
        return "metastatico"
    if cid in _LINFOMA_LEUCEMIA:
        return "linfoma_leucemia"
    if cid.startswith("C"):
        return "tumor_solido"
    if cid == "I50":
        return "insuficiencia_cardiaca"
    if cid in ("I21", "I22", "I25"):
        return "infarto_miocardio"
    if cid in ("J44", "J45"):
        return "doenca_pulmonar_cronica"
    if cid == "N18":
        return "doenca_renal"
    if cid[0] == "E" and 10 <= int(cid[1:3]) <= 14:
        return "diabetes_sem_complicacao"
    return None


def categorias_charlson(comorbidades: str | None, cid_secundario: str | None) -> dict[str, str]:
    """Categoria Charlson -> fonte ("texto:dm2", "cid_secundario:I50"). O CID principal não entra:
    é a doença da cirurgia, já considerada na classe. Cada categoria conta uma vez."""
    achadas: dict[str, str] = {}
    for termo in (t.strip().lower() for t in (comorbidades or "").split(";")):
        categoria = TEXTO_PARA_CHARLSON.get(termo)
        if categoria:
            achadas.setdefault(categoria, f"texto:{termo}")
    for bruto in re.split(r"[;,\s]+", cid_secundario or ""):
        categoria = _categoria_do_cid_secundario(bruto)
        if categoria:
            achadas.setdefault(categoria, f"cid_secundario:{normalizar_cid(bruto)}")
    # Hierarquia do Charlson: metástase substitui o tumor sólido (não somam).
    if "metastatico" in achadas:
        achadas.pop("tumor_solido", None)
    return achadas


def fator_comorbidade(comorbidades: str | None, cid_secundario: str | None) -> tuple[Fator, list[str]]:
    achadas = categorias_charlson(comorbidades, cid_secundario)
    pontos = sum(PESOS_CHARLSON[c] for c in achadas)
    valor = next((v for limite, v in _FATOR_POR_CHARLSON if pontos <= limite), TETO_FATOR)
    fontes = ", ".join(achadas.values()) or "nenhuma comorbidade Charlson encontrada"
    return (Fator(valor, f"charlson_{pontos}", f"Charlson {pontos} ({fontes}) → ×{_num(valor)}"),
            sorted(achadas))


def faixa_idade(idade: int | None) -> str | None:
    if idade is None or idade < 0:
        return None
    return next((nome for nome, limite in FAIXAS_IDADE if idade <= limite), "80+")


def fator_idade(cid_principal: str | None, idade: int | None, celula: CelulaIrr | None) -> Fator:
    """IRR > 1 sobe o fator em 0,075 por duplicação do risco, até IRR 4 (teto 1,15).
    IRR ausente, <= 1 ou de célula com menos de 20 óbitos: fator neutro 1,00."""
    alvo = f"{_cid3(cid_principal)} {faixa_idade(idade)}"
    if celula is None or celula.irr is None or not math.isfinite(celula.irr):
        return Fator(1.0, "neutro_irr_indisponivel", f"{alvo}: sem IRR de referência → ×1,00")
    if celula.obitos < MIN_OBITOS_IRR:
        return Fator(1.0, "neutro_poucos_obitos",
                     f"{alvo}: {celula.obitos} óbitos (< {MIN_OBITOS_IRR}), taxa instável → ×1,00")
    if celula.irr <= 1:
        return Fator(1.0, "neutro_irr_ate_1", f"{alvo}: IRR {_num(celula.irr)} → ×1,00")
    valor = min(TETO_FATOR, 1 + 0.075 * min(math.log2(celula.irr), 2))
    return Fator(round(valor, 4), "ajuste_log2_irr",
                 f"{alvo}: IRR {_num(celula.irr)} ({celula.obitos} óbitos) → ×{_num(valor, 3)}")


def calcular_fatores(cid_principal: str | None, idade: int | None, comorbidades: str | None,
                     cid_secundario: str | None, celula: CelulaIrr | None) -> FatoresContexto:
    comorb, categorias = fator_comorbidade(comorbidades, cid_secundario)
    return FatoresContexto(comorb, fator_idade(cid_principal, idade, celula), categorias)


def chave_irr(cid_principal: str | None, idade: int | None) -> tuple[str, str] | None:
    cid, faixa = _cid3(cid_principal), faixa_idade(idade)
    return (cid, faixa) if cid and faixa else None
