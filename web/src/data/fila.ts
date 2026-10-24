import dados from "./dados.json"
import { listarFila, listarInbox } from "@/lib/api"
import { deApiMinimo, sobrepor } from "./adaptador"
import type { ClasseSwalis, Paciente } from "./tipos"

export const META = dados.meta as unknown as { referencia: string; versao_regras: string; total: number; swalis: ClasseSwalis[] }

const BASE = dados.solicitacoes as unknown as Paciente[]

export let PACIENTES: Paciente[] = []
export let TOTAL_FILA = 0
export let PACIENTE_POR_ID: Record<string, Paciente> = {}
export let FILA: Paciente[] = []
export let ESPECIALIDADES: string[] = []
export let ORIGEM_DADOS: "api" | "csv" = "csv"
export let VERSAO_REGRAS = META.versao_regras

const aplicar = (lista: Paciente[]) => {
  PACIENTES = [...lista].sort((a, b) => a.posicao - b.posicao)
  FILA = PACIENTES
  TOTAL_FILA = PACIENTES.length
  PACIENTE_POR_ID = Object.fromEntries(PACIENTES.map((p) => [p.id, p]))
  ESPECIALIDADES = [...new Set(PACIENTES.map((p) => p.especialidade))].sort()
}

export const usarCsv = () => {
  aplicar(BASE)
  ORIGEM_DADOS = "csv"
  VERSAO_REGRAS = META.versao_regras
}

export const carregarFila = async () => {
  const [{ itens, versao_regras }, inbox] = await Promise.all([listarFila(), listarInbox()])
  const baseDeId = Object.fromEntries(BASE.map((p) => [p.id, p]))
  const inboxDeId = Object.fromEntries(inbox.itens.map((x) => [x.solicitacao_id, x]))
  aplicar(
    itens.map((i) => {
      const base = baseDeId[i.solicitacao_id]
      return base ? sobrepor(base, i, inboxDeId[i.solicitacao_id]) : deApiMinimo(i, inboxDeId[i.solicitacao_id])
    })
  )
  ORIGEM_DADOS = "api"
  VERSAO_REGRAS = versao_regras ?? META.versao_regras
}

usarCsv()
