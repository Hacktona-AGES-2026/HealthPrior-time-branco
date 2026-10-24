import type { ItemFilaApi, ItemInboxApi } from "@/lib/api"
import { addDias, HOJE } from "@/lib/datas"
import type { Classe, Paciente } from "./tipos"

const LIMITACAO = ["nenhuma", "leve", "moderada", "grave"] as const

const humanizar = (codigo: string) => {
  const texto = codigo.replaceAll("_", " ")
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}

const unicos = (lista: string[]) => [...new Set(lista)]

export const sobrepor = (base: Paciente, i: ItemFilaApi, inbox?: ItemInboxApi): Paciente => ({
  ...base,
  posicao: i.posicao,
  posicao_atual: i.posicao_antes ?? base.posicao_atual,
  camada: i.camada,
  classe: inbox?.classe_sugerida ?? i.classe ?? base.classe,
  classe_vigente: inbox?.classe_atual ?? i.classe ?? null,
  pct: i.pct_prazo_consumido ?? base.pct,
  dias_em_fila: i.dias_em_fila,
  justificativa: i.resumo_justificativa || base.justificativa,
  alertas: unicos([...base.alertas, ...i.alertas.map(humanizar)]),
  classe_status: i.classe_status,
  editado_manualmente: i.editado_manualmente,
  inbox: inbox ? { motivos: inbox.motivos.map((m) => m.evidencia), gatilho: inbox.evento_gatilho } : undefined,
})

export const deApiMinimo = (i: ItemFilaApi, inbox?: ItemInboxApi): Paciente =>
  sobrepor(
    {
      id: i.solicitacao_id,
      iniciais: i.iniciais || "—",
      idade: i.idade ?? 0,
      sexo: i.sexo === "M" ? "M" : "F",
      municipio: i.municipio ?? "",
      uf: "RS",
      distancia_km: null,
      procedimento: i.procedimento,
      especialidade: i.especialidade,
      cid: i.cid,
      cid_norm: i.cid.replace(".", "").toUpperCase(),
      cid_descricao: i.cid_descricao ?? "",
      cid_secundario: null,
      asa: null,
      comorbidades: [],
      dor: i.intensidade_dor_eva,
      limitacao: (LIMITACAO as readonly string[]).includes(i.limitacao_funcional ?? "") ? (i.limitacao_funcional as Paciente["limitacao"]) : null,
      justificativa_clinica: "",
      observacoes: "",
      sinais_texto: [],
      eixos: { progressao: { nivel: 0, motivos: [] }, sintoma: { nivel: 0, motivos: [] } },
      data_entrada: addDias(HOJE, -i.dias_em_fila),
      dias_em_fila: i.dias_em_fila,
      prioridade_atual: null,
      data_revisao_prioridade: null,
      oncologico: i.oncologico,
      flag_diabetico: false,
      hba1c: null,
      pre_anestesica: null,
      exames_pre_op: false,
      posicao_atual: i.posicao_antes ?? i.posicao,
      posicao: i.posicao,
      camada: i.camada,
      classe: (i.classe ?? "D") as Classe,
      pct: i.pct_prazo_consumido ?? 0,
      justificativa: i.resumo_justificativa,
      versao_regras: "",
      motivos: [],
      sintomas: [],
      alertas: [],
      eventos: [],
      outras: [],
    },
    i,
    inbox
  )
