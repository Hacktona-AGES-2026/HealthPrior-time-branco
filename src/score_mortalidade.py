# -*- coding: utf-8 -*-
"""
score_mortalidade.py
Deriva um score de risco de mortalidade por paciente a partir de CID (cid_principal /
cid_secundario) e da lista de comorbidades em texto livre, usando duas escalas
validadas na literatura:

  - Elixhauser Comorbidity Index, ponderado por van Walraven et al. (2009),
    "A Modification of the Elixhauser Comorbidity Measures into a Point System
    for Hospital Death Using Administrative Data", Med Care 47(6):626-33.
  - Charlson Comorbidity Index (Charlson et al. 1987) com ajuste por idade,
    convertido em probabilidade de sobrevida em 10 anos pela formula original:
        sobrevida_10a = 0.983 ^ exp(indice_ajustado_por_idade * 0.9)

As categorias Charlson/Elixhauser sao identificadas combinando:
  1. cid_principal / cid_secundario (CID-10), seguindo a logica dos algoritmos de
     Quan et al. (2005, Med Care 43(11):1130-9) para as categorias oncologicas
     (tumor solido, linfoma/leucemia, cancer metastatico) -- as unicas bem
     cobertas por CID neste dataset.
  2. Palavras-chave no campo `comorbidades` (texto livre) para as demais
     categorias (ICC, DPOC, DRC, fibrilacao atrial, HAS, obesidade, hipotireoidismo,
     depressao, cardiopatia isquemica) -- o dataset nao traz lista completa de
     diagnosticos codificados por internacao, so esse campo e o CID principal.

LIMITACOES (leia antes de usar o resultado como se fosse clinico):
  - Nao ha desfecho de obito real no dataset (e sintetico) para calibrar/validar
    o score localmente -- os pesos usados sao os publicados nos estudos originais,
    nao foram re-estimados aqui.
  - O mapeamento texto -> categoria e uma heuristica por palavra-chave, revisar
    com um clinico antes de usar em produto real.
  - Sexo nao entra como peso numerico: nao existe peso publicado universal para
    sexo dentro do Elixhauser/Charlson (Li et al. 2008 usaram sexo como covariavel
    separada em regressao logistica contra obito real, o que exige dados de
    desfecho que nao temos). Reportamos sexo como coluna informativa, nao como
    pontos somados ao score.

Uso: python src/score_mortalidade.py [fila_cirurgica.csv]
"""
import os
import re
import sys

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "data", "fila_cirurgica.csv")
SAIDA = os.path.join(RAIZ, "data", "processed", "score_mortalidade.csv")

# ---------------------------------------------------------------------------
# 1. Categorias detectadas por CID (oncologicas -- Quan et al. 2005)
# ---------------------------------------------------------------------------
METASTATICO = ("C77", "C78", "C79", "C80")
LINFOMA_LEUCEMIA = ("C81", "C82", "C83", "C84", "C85", "C88", "C90", "C91", "C92", "C93", "C94", "C95", "C96")


def categoria_oncologica(cid):
    if not isinstance(cid, str) or not cid.startswith("C"):
        return None
    if cid.startswith(METASTATICO):
        return "metastatico"
    if cid.startswith(LINFOMA_LEUCEMIA):
        return "linfoma_leucemia"
    return "tumor_solido"


# ---------------------------------------------------------------------------
# 2. Categorias detectadas por palavra-chave em `comorbidades` (texto livre)
#    chave -> (categoria_elixhauser, categoria_charlson ou None)
# ---------------------------------------------------------------------------
KEYWORDS = {
    "icc": ("insuficiencia_cardiaca", "insuficiencia_cardiaca"),
    "cardiopatia isquemica": (None, "infarto_miocardio"),
    "fibrilacao atrial": ("arritmia_cardiaca", None),
    "dpoc": ("doenca_pulmonar_cronica", "doenca_pulmonar_cronica"),
    "asma": ("doenca_pulmonar_cronica", "doenca_pulmonar_cronica"),
    "drc": ("insuficiencia_renal", "doenca_renal"),
    "dm2": ("diabetes_sem_complicacao", "diabetes_sem_complicacao"),
    "has": ("hipertensao_nao_complicada", None),
    "obesidade": ("obesidade", None),
    "hipotireoidismo": ("hipotireoidismo", None),
    "depressao": ("depressao", None),
    # sem categoria formal no Elixhauser/Charlson -- mantidos so como flag informativa
    "tabagismo": (None, None),
    "anticoagulacao oral": (None, None),
}

# ---------------------------------------------------------------------------
# 3. Pesos publicados
# ---------------------------------------------------------------------------
PESOS_ELIXHAUSER_VANWALRAVEN = {
    "insuficiencia_cardiaca": 7,
    "arritmia_cardiaca": 5,
    "doenca_pulmonar_cronica": 3,
    "insuficiencia_renal": 5,
    "diabetes_sem_complicacao": 0,
    "hipertensao_nao_complicada": 0,
    "obesidade": -4,
    "hipotireoidismo": 0,
    "depressao": -3,
    "tumor_solido": 4,
    "linfoma_leucemia": 9,
    "metastatico": 12,
}

PESOS_CHARLSON = {
    "infarto_miocardio": 1,
    "insuficiencia_cardiaca": 1,
    "doenca_pulmonar_cronica": 1,
    "diabetes_sem_complicacao": 1,
    "doenca_renal": 2,
    "tumor_solido": 2,
    "linfoma_leucemia": 2,
    "metastatico": 6,
}


def pontos_idade_charlson(idade):
    """Ajuste de idade do Charlson original (Charlson et al. 1987)."""
    if idade < 50:
        return 0
    if idade < 60:
        return 1
    if idade < 70:
        return 2
    if idade < 80:
        return 3
    return 4


def extrair_categorias(row):
    cats = set()
    for cid in (row.cid_principal, row.cid_secundario):
        cid_norm = str(cid).upper().replace(".", "") if pd.notna(cid) else ""
        cat = categoria_oncologica(cid_norm)
        if cat:
            cats.add(("onco", cat))

    texto = str(row.comorbidades).lower() if pd.notna(row.comorbidades) else ""
    for termo in re.split(r";\s*", texto):
        termo = termo.strip()
        if termo in KEYWORDS:
            cat_elix, cat_charl = KEYWORDS[termo]
            if cat_elix:
                cats.add(("elix", cat_elix))
            if cat_charl:
                cats.add(("charl", cat_charl))
    return cats


def main():
    fila = pd.read_csv(ARQ)

    linhas = []
    for _, row in fila.iterrows():
        cats = extrair_categorias(row)
        cats_elix = {c for origem, c in cats if origem in ("elix",)} | {c for origem, c in cats if origem == "onco"}
        cats_charl = {c for origem, c in cats if origem in ("charl",)} | {c for origem, c in cats if origem == "onco"}

        score_elix = sum(PESOS_ELIXHAUSER_VANWALRAVEN.get(c, 0) for c in cats_elix)
        score_charl = sum(PESOS_CHARLSON.get(c, 0) for c in cats_charl)
        idade_pts = pontos_idade_charlson(row.idade)
        charlson_idade = score_charl + idade_pts
        sobrevida_10a = 0.983 ** (2.718281828 ** (charlson_idade * 0.9))

        linhas.append({
            "solicitacao_id": row.solicitacao_id,
            "idade": row.idade,
            "sexo": row.sexo,
            "categorias_detectadas": ", ".join(sorted(cats_elix | cats_charl)) or "nenhuma",
            "elixhauser_vanwalraven": score_elix,
            "charlson": score_charl,
            "charlson_ajustado_idade": charlson_idade,
            "sobrevida_estimada_10a": round(sobrevida_10a, 3),
        })

    out = pd.DataFrame(linhas)
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    out.to_csv(SAIDA, index=False)

    print(f"Processado: {len(out)} solicitacoes -> {os.path.relpath(SAIDA, RAIZ)}\n")

    print("=" * 78)
    print("ELIXHAUSER (van Walraven) -- maior = maior risco de obito intra-hospitalar")
    print("=" * 78)
    print(out.elixhauser_vanwalraven.describe().round(2))
    print("\nTop 10 maior risco (Elixhauser):")
    print(out.sort_values("elixhauser_vanwalraven", ascending=False)
          [["solicitacao_id", "idade", "sexo", "elixhauser_vanwalraven", "categorias_detectadas"]]
          .head(10).to_string(index=False))

    print("\n" + "=" * 78)
    print("CHARLSON ajustado por idade -- sobrevida estimada em 10 anos")
    print("=" * 78)
    print(out.charlson_ajustado_idade.describe().round(2))
    print("\nTop 10 menor sobrevida estimada (Charlson + idade):")
    print(out.sort_values("sobrevida_estimada_10a")
          [["solicitacao_id", "idade", "sexo", "charlson_ajustado_idade", "sobrevida_estimada_10a", "categorias_detectadas"]]
          .head(10).to_string(index=False))

    print("\n" + "=" * 78)
    print("SEXO -- reportado, nao somado ao score (sem peso publicado universal)")
    print("=" * 78)
    print(out.groupby("sexo")[["elixhauser_vanwalraven", "charlson_ajustado_idade"]].mean().round(2))


if __name__ == "__main__":
    main()
