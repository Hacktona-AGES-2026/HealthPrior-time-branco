import type { ItemFilaApi, ItemInboxApi } from "@/lib/api"
import { addDias } from "@/lib/datas"
import type { Classe, Paciente } from "./tipos"

// Data de referência do dataset (backend: settings.ref_date).
const REF = "2026-10-23"

/** Paciente veio da API? Campos que ela não expõe (confiança, ASA, HbA1c, pré-op, IA) não são exibidos. */
export const daApi = (p: Paciente) => p.camada !== undefined

const LIMITACAO: Record<string, Paciente["limitacao_funcional"]> = {
  nenhuma: "nenhuma",
  leve: "leve",
  moderada: "moderada",
  grave: "grave",
}

const ROTULO_CAMADA = { 1: "Camada 1 · oncológico (regra de ouro)", 2: "Camada 2 · urgente", 3: "Camada 3 · demais" }

/** Frases "SWALIS: progressão N: ...; sintoma N: ..." da justificativa viram sinais curtos. */
const sinaisDaJustificativa = (j: string) => {
  const swalis = j.split("SWALIS:")[1]?.split(". Classe")[0] ?? ""
  return swalis
    .split(/;\s*(?=(?:progressão|sintoma) \d)/)
    .map((t) => t.trim())
    .filter(Boolean)
    .slice(0, 4)
}

/**
 * Item da fila publicada (+ item do inbox, se houver) -> Paciente do front.
 * `classe` é a proposta do sistema; `classe_antiga` é a classe em vigor. Sem item no inbox, as duas são
 * a classe da fila. Campos que a API ainda não expõe (gráficos da IA, histórico) ficam vazios.
 */
export const deApi = (i: ItemFilaApi, inbox?: ItemInboxApi): Paciente => {
  const classeFila = (i.classe ?? "D") as Classe
  const proposta = inbox?.classe_sugerida ?? classeFila
  const vigente = (inbox?.classe_atual ?? classeFila) as Classe
  const motivos = inbox?.motivos ?? []
  return {
    camada: i.camada,
    classe_status: i.classe_status,
    editado_manualmente: i.editado_manualmente,
    solicitacao_id: i.solicitacao_id,
    iniciais: i.iniciais || "—",
    cns_mascarado: "",
    idade: i.idade ?? 0,
    sexo: i.sexo === "M" ? "M" : "F",
    municipio: i.municipio ?? "",
    distancia_hospital_km: 0,
    procedimento: i.procedimento,
    especialidade: i.especialidade,
    cid: i.cid.replace(".", "").toUpperCase(),
    cid_descricao: i.cid_descricao ?? "",
    data_entrada_fila: addDias(REF, -i.dias_em_fila),
    dias_em_fila: i.dias_em_fila,
    posicao_antiga: i.posicao_antes ?? i.posicao,
    posicao_nova: i.posicao,
    classe_antiga: vigente,
    classe: proposta,
    prazo_consumido_pct: i.pct_prazo_consumido ?? 0,
    divergencia: Boolean(inbox),
    comorbidades: [],
    asa: 1,
    intensidade_dor_eva: i.intensidade_dor_eva ?? 0,
    limitacao_funcional: LIMITACAO[i.limitacao_funcional ?? ""] ?? "nenhuma",
    avaliacao_pre_anestesica: false,
    exames_pre_op_validos: false,
    justificativa_clinica: "",
    observacoes: "",
    confianca: 1,
    sinais: [...i.alertas, ...sinaisDaJustificativa(i.resumo_justificativa)],
    justificativa: i.resumo_justificativa,
    evidencias: motivos.map((m) => ({ fonte: m.fonte === "evento" ? "evento" : m.fonte === "cid" ? "cid" : "texto", trecho: m.evidencia, data: m.data ?? undefined })),
    parametros_ia: {
      modelo: "SWALIS por pontos + regras (Jev 1.14)",
      versao_regras: "",
      classe_base_cid: proposta,
      contribuicoes: [],
      sinais_texto: [],
      confianca_detalhe: [],
      regras_acionadas: [ROTULO_CAMADA[i.camada]],
      contrafactual: "",
    },
    falta_para_subir: "",
    eventos: [],
    // Dois pontos reais: entrada (0% do prazo) e hoje. O histórico de classes ainda não vem da API.
    evolucao: [
      { data: addDias(REF, -i.dias_em_fila), classe: vigente, prazo_consumido_pct: 0, motivo: "Entrada na fila" },
      { data: REF, classe: classeFila, prazo_consumido_pct: i.pct_prazo_consumido ?? 0, motivo: "Situação atual (fila publicada)" },
    ],
    historico: [],
  }
}
