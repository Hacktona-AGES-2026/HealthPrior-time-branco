import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "backend"))

from app.application.montar_fila import _texto_motivo, montar_fila
from app.config import settings
from app.domain.preprocessing.municipios import MUNICIPIOS_OFICIAIS
from app.domain.preprocessing.normalizacao import normalizar_municipio
from app.domain.urgencia import (
    SinaisUrgencia,
    evento_e_piora,
    motivos_sintomas,
    motivos_urgencia,
    tem_biopsia_positiva,
    tem_evento_de_piora_na_espera,
)
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.swalis_regras import criar_swalis

DESTINO = RAIZ / "web" / "src" / "data" / "dados.json"
RANK_PRIORIDADE = {"alta": 0, "media": 1, "baixa": 2}


def ler(caminho):
    with open(caminho, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def vazio(valor):
    return valor is None or str(valor).strip() == ""


def iniciais(nome):
    partes = [p for p in re.split(r"\s+", nome.strip()) if p and p.lower() not in {"de", "da", "do", "dos", "das", "e"}]
    return "".join(p[0].upper() + "." for p in partes[:3])


def main():
    dados = settings.data_dir
    bruto = {r["solicitacao_id"]: r for r in ler(dados / "fila_cirurgica.csv")}
    solicitacoes, eventos = carregar_do_csv(dados)
    scorer = criar_swalis()
    linhas = montar_fila(solicitacoes, eventos, scorer, settings.ref_date)
    por_id = {s.solicitacao_id: s for s in solicitacoes}

    ordem_atual = sorted(
        solicitacoes,
        key=lambda s: (RANK_PRIORIDADE.get(s.prioridade_norm or "", 3), s.data_entrada_fila, s.solicitacao_id),
    )
    posicao_atual = {s.solicitacao_id: i + 1 for i, s in enumerate(ordem_atual)}

    por_paciente = defaultdict(list)
    for l in linhas:
        por_paciente[por_id[l.solicitacao_id].paciente_id].append(l)

    saida = []
    for l in linhas:
        s = por_id[l.solicitacao_id]
        r = bruto[l.solicitacao_id]
        evs = eventos.get(s.solicitacao_id, [])
        validos = [e for e in evs if e.duplicado_de is None]
        sinais = SinaisUrgencia(
            cid_norm=s.cid_norm,
            intensidade_dor_eva=s.intensidade_dor_eva,
            limitacao_funcional=s.limitacao_funcional,
            tem_evento_de_piora=tem_evento_de_piora_na_espera(evs, s.data_entrada_fila),
            justificativa_clinica=s.justificativa_clinica,
            tem_biopsia_positiva=tem_biopsia_positiva(evs),
        )
        resultado = scorer.calcular(s, evs)
        classificacao = scorer.classificar(s, evs)
        sinais_texto = scorer.sinais(s)
        motivos = [_texto_motivo(m, s) for m in motivos_urgencia(sinais)]
        sintomas = [_texto_motivo(m, s) for m in motivos_sintomas(sinais)]

        hba1c_eventos = sorted((e for e in validos if e.tipo_evento == "hba1c" and e.valor_numerico is not None), key=lambda e: e.data_evento)
        hba1c = None
        if not vazio(r["hba1c_ultima"]):
            hba1c = {"valor": float(r["hba1c_ultima"]), "data": r["data_hba1c_ultima"] or None}
        hba1c_evento = hba1c_eventos[-1] if hba1c_eventos else None
        piora_nos_eventos = any(evento_e_piora(e.tipo_evento, e.resultado) and e.data_evento >= s.data_entrada_fila for e in validos)

        alertas = []
        if (r["flag_oncologico"] == "sim") != s.oncologico:
            alertas.append("Flag oncológica do cadastro diverge do CID")
        if (r["flag_piora_clinica"] == "sim") != piora_nos_eventos:
            alertas.append("Flag de piora do cadastro diverge dos eventos")
        if r["avaliacao_pre_anestesica"] == "vencida":
            alertas.append("Avaliação pré-anestésica vencida")
        ultima = hba1c_evento.valor_numerico if hba1c_evento else (hba1c["valor"] if hba1c else None)
        if ultima is not None and ultima > 8.5:
            alertas.append(f"HbA1c {str(ultima).replace('.', ',')}% acima de 8,5%")
        if tem_biopsia_positiva(evs) and not s.oncologico:
            alertas.append("Biópsia positiva com CID não oncológico: revisar CID")
        if any(vazio(r[c]) for c in ("asa", "intensidade_dor_eva", "limitacao_funcional")):
            alertas.append("Dados clínicos incompletos")
        outras = [o for o in por_paciente[s.paciente_id] if o.solicitacao_id != s.solicitacao_id]
        if outras:
            alertas.append("Paciente com outra solicitação na fila")

        saida.append({
            "id": s.solicitacao_id,
            "iniciais": iniciais(r["nome_paciente"]),
            "idade": int(float(r["idade"])),
            "sexo": r["sexo"],
            "municipio": normalizar_municipio(r["municipio"], MUNICIPIOS_OFICIAIS) or r["municipio"],
            "uf": r["uf"],
            "distancia_km": None if vazio(r["distancia_hospital_km"]) else int(float(r["distancia_hospital_km"])),
            "procedimento": s.procedimento,
            "especialidade": s.especialidade,
            "cid": s.cid_principal,
            "cid_norm": s.cid_norm,
            "cid_descricao": r["cid_descricao"],
            "cid_secundario": None if vazio(r["cid_secundario"]) else r["cid_secundario"],
            "asa": None if vazio(r["asa"]) else int(float(r["asa"])),
            "comorbidades": [] if vazio(r["comorbidades"]) or r["comorbidades"] == "nenhuma" else [c.strip() for c in r["comorbidades"].split(";")],
            "dor": s.intensidade_dor_eva,
            "limitacao": s.limitacao_funcional,
            "justificativa_clinica": s.justificativa_clinica,
            "observacoes": s.observacoes,
            "sinais_texto": [
                {"categoria": x.categoria.value, "termo": x.termo, "trecho": x.trecho, "fonte": x.fonte, "origem": x.origem}
                for x in sinais_texto
            ],
            "eixos": {
                "progressao": {"nivel": classificacao.progressao.nivel, "motivos": classificacao.progressao.motivos},
                "sintoma": {"nivel": classificacao.sintoma.nivel, "motivos": classificacao.sintoma.motivos},
            },
            "data_entrada": s.data_entrada_fila.isoformat(),
            "dias_em_fila": l.dias_em_fila,
            "prioridade_atual": s.prioridade_norm,
            "data_revisao_prioridade": r["data_ultima_revisao_prioridade"] or None,
            "oncologico": s.oncologico,
            "flag_diabetico": r["flag_diabetico"] == "sim",
            "hba1c": hba1c,
            "pre_anestesica": r["avaliacao_pre_anestesica"] or None,
            "exames_pre_op": r["exames_pre_op_validos"] == "sim",
            "posicao_atual": posicao_atual[s.solicitacao_id],
            "posicao": l.posicao,
            "camada": l.camada,
            "classe": l.classe,
            "pct": l.pct_prazo_consumido,
            "justificativa": l.justificativa,
            "versao_regras": l.versao_regras,
            "motivos": motivos,
            "sintomas": sintomas,
            "alertas": alertas,
            "eventos": [
                {
                    "id": e.evento_id,
                    "data": e.data_evento.isoformat(),
                    "tipo": e.tipo_evento,
                    "resultado": e.resultado,
                    "valor": e.valor_numerico,
                    "descricao": e.descricao,
                    "origem": e.origem,
                    "historico": e.historico,
                }
                for e in sorted(validos, key=lambda e: e.data_evento)
            ],
            "outras": [{"id": o.solicitacao_id, "procedimento": por_id[o.solicitacao_id].procedimento, "posicao": o.posicao} for o in outras],
        })

    saida.sort(key=lambda p: p["posicao"])
    swalis = [
        {"classe": r["classe"], "descricao": r["descricao"], "prazo": int(r["prazo_maximo_dias"]), "exemplos": r["exemplos"]}
        for r in ler(dados / "referencias" / "swalis.csv")
    ]
    meta = {"referencia": settings.ref_date.isoformat(), "versao_regras": linhas[0].versao_regras if linhas else "", "total": len(saida), "swalis": swalis}
    DESTINO.write_text(json.dumps({"meta": meta, "solicitacoes": saida}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(saida)} solicitações -> {DESTINO} ({DESTINO.stat().st_size // 1024} KB)")


main()
