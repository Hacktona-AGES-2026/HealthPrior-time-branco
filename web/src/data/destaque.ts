import { HOJE, addDias } from "@/lib/datas"
import type { Paciente } from "./tipos"

export const ID_DESTAQUE = "SOL-2026-00412"

export const enriquecerDestaque = (base: Paciente): Paciente => {
  const entrada = base.data_entrada_fila
  const ps1 = addDias(entrada, -36)
  const ps2 = addDias(entrada, -11)
  const ubs = addDias(entrada, -62)
  const eventos = base.eventos.filter((e) => e.tipo !== "hba1c").map((e) =>
    e.tipo === "entrada" ? { ...e, descricao: "Entrada na fila cirúrgica com prioridade baixa (hérnia redutível)" } : e
  )
  eventos.push({ data: addDias(entrada, 94), tipo: "hba1c", descricao: "HbA1c 8,6%: acima da meta para cirurgia eletiva" })
  eventos.sort((a, b) => a.data.localeCompare(b.data))

  return {
    ...base,
    solicitacao_id: ID_DESTAQUE,
    iniciais: "C.A.",
    cns_mascarado: "700 •••• •••• 4127",
    distancia_hospital_km: 18,
    comorbidades: ["HAS", "DM2", "obesidade grau II", "tabagismo"],
    hba1c: { valor: 8.6, data: addDias(HOJE, -62) },
    avaliacao_pre_anestesica: true,
    exames_pre_op_validos: false,
    observacoes: "Paciente relata por telefone vômitos recorrentes e piora do abaulamento; irredutível há 3 dias.",
    sinais: ["obstrução", "PS x2", "irredutível", "dor 9/10", "frágil", "diabética"],
    justificativa:
      "Hérnia incisional com obstrução (K43.0) e duas idas ao pronto-socorro por suboclusão antes da entrada na fila. Hoje irredutível, com dor 9/10 e paciente frágil: risco de estrangulamento. Proposta: C → A1.",
    evidencias: [
      { fonte: "texto", trecho: "suboclusão intestinal" },
      { fonte: "texto", trecho: "duas vezes no último mês" },
      { fonte: "texto", trecho: "Hérnia irredutível" },
      { fonte: "texto", trecho: "dor 9/10" },
      { fonte: "cid", trecho: "K43.0 · Hérnia incisional com obstrução, sem gangrena" },
      { fonte: "evento", trecho: "PS por dor abdominal e vômitos: suboclusão, manejo conservador", data: ps1 },
      { fonte: "evento", trecho: "PS por recidiva da suboclusão, hérnia irredutível à palpação", data: ps2 },
      { fonte: "evento", trecho: "TC de abdome: alça de delgado encarcerada no saco herniário", data: addDias(entrada, Math.round(0.85 * base.dias_em_fila)) },
      { fonte: "regra", trecho: "R03 · Pronto-socorro recorrente sobe 1 degrau" },
    ],
    parametros_ia: {
      ...base.parametros_ia,
      classe_base_cid: "B",
      contribuicoes: [
        { fator: "Sintomas: dor 9/10, limitação grave", delta_degraus: 0, origem: "sintomas", detalhe: "Dor intensa coerente com a classe, sem elevação adicional isolada" },
        { fator: "Texto: suboclusão e irredutibilidade", delta_degraus: 1, origem: "texto_llm", detalhe: "\"suboclusão intestinal\" e \"Hérnia irredutível\" indicam obstrução com risco de estrangulamento" },
        { fator: "Eventos: PS x2 antes da entrada", delta_degraus: 1, origem: "eventos", detalhe: "Duas idas ao pronto-socorro em 25 dias por suboclusão (regra R03)" },
        { fator: "Fragilidade (idade e ASA)", delta_degraus: 0, origem: "fragilidade", detalhe: "Idade 71, ASA 3 e DM2 descompensado: a fragilidade só sobe a classe, nunca desce" },
      ],
      regras_acionadas: [
        "R02 · O LLM propõe, as regras decidem",
        "R03 · Pronto-socorro recorrente sobe 1 degrau",
        "R05 · Fragilidade só sobe a classe, nunca desce",
        "R06 · Idade apenas como modificador",
        "R09 · Obstrução com risco de estrangulamento resulta em A1",
      ],
      contrafactual:
        "Sem as duas idas ao pronto-socorro (+1 degrau) e sem o relato de irredutibilidade (+1), a classe seria B, mantida a base do CID.",
    },
    eventos,
    historico: [
      { data: ps2, tipo: "consulta", descricao: "Atendimento no pronto-socorro: recidiva de suboclusão, hérnia irredutível à palpação, alta com orientações", origem: "Hospital São Lucas" },
      { data: ps1, tipo: "consulta", descricao: "Atendimento no pronto-socorro: dor abdominal e vômitos, suboclusão intestinal resolvida com tratamento conservador", origem: "Hospital São Lucas" },
      { data: ubs, tipo: "consulta", descricao: "Consulta na atenção básica: hérnia incisional dolorosa; encaminhada ao ambulatório de cirurgia", origem: "UBS Centro" },
      { data: addDias(entrada, -240), tipo: "solicitacao_anterior", descricao: "Solicitação anterior de herniorrafia incisional cancelada: HbA1c 10,2%", origem: "Central de Regulação" },
      { data: addDias(entrada, 55), tipo: "alteracao_prioridade", descricao: "Prioridade revisada pela regulação e mantida como baixa", origem: "Regulação" },
      { data: addDias(HOJE, -2190), tipo: "cirurgia_previa", descricao: "Laparotomia exploradora por abdome agudo obstrutivo", origem: "Hospital Conceição" },
      { data: addDias(HOJE, -2600), tipo: "alergia", descricao: "Dipirona (urticária)", origem: "Cadastro CNS" },
      { data: addDias(HOJE, -1500), tipo: "medicacao_continua", descricao: "Metformina 850 mg 2x/dia", origem: "UBS Centro" },
    ],
  }
}
