import type { Classe, Paciente } from "@/data/tipos"
import { MOTIVOS_CODIFICADOS, type MotivoCodificado } from "@/lib/api"

export type Pagina = "fila" | "inbox" | "pacientes" | "analise" | "swalis" | "pendencias" | "propostas" | "notificacoes"

export type { MotivoCodificado }

export const ROTULO_MOTIVO = MOTIVOS_CODIFICADOS

export type Decisao = {
  status: "aprovado" | "editado"
  classeFinal: Classe
  motivoCodificado?: MotivoCodificado
  motivo?: string
}

export type StatusFiltro = "todos" | "pendentes" | "revisados" | "aprovados" | "editados"

export type Filtros = {
  busca: string
  especialidade: string
  classe: string
  camada: string
  oncologicos: boolean
  vencidos: boolean
  alertas: boolean
  subiu: boolean
  status: StatusFiltro
}

export const FILTROS_VAZIOS: Filtros = {
  busca: "",
  especialidade: "todas",
  classe: "todas",
  camada: "todas",
  oncologicos: false,
  vencidos: false,
  alertas: false,
  subiu: false,
  status: "todos",
}

export const normalizar = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()

export const filtrosAtivos = (f: Filtros) => JSON.stringify(f) !== JSON.stringify(FILTROS_VAZIOS)

export const precisaRevisar = (p: Paciente) => p.alertas.length > 0

export const subiuNaFila = (p: Paciente) => p.posicao < p.posicao_atual

export const statusDe = (decisoes: Record<string, Decisao>, id: string): "pendente" | Decisao["status"] =>
  decisoes[id]?.status ?? "pendente"

export const aplicarFiltros = (pacientes: Paciente[], f: Filtros, decisoes: Record<string, Decisao>) => {
  const termo = normalizar(f.busca.trim())
  return pacientes.filter((p) => {
    if (termo) {
      const alvo = normalizar([p.id, p.cid, p.cid_norm, p.procedimento, p.iniciais, p.cid_descricao, p.municipio].join(" "))
      if (!alvo.includes(termo)) return false
    }
    if (f.especialidade !== "todas" && p.especialidade !== f.especialidade) return false
    if (f.classe !== "todas" && p.classe !== f.classe) return false
    if (f.camada !== "todas" && String(p.camada) !== f.camada) return false
    if (f.oncologicos && !p.oncologico) return false
    if (f.vencidos && p.pct <= 100) return false
    if (f.alertas && !precisaRevisar(p)) return false
    if (f.subiu && !subiuNaFila(p)) return false
    if (f.status !== "todos") {
      const st = statusDe(decisoes, p.id)
      if (f.status === "pendentes" && st !== "pendente") return false
      if (f.status === "revisados" && st === "pendente") return false
      if (f.status === "aprovados" && st !== "aprovado") return false
      if (f.status === "editados" && st !== "editado") return false
    }
    return true
  })
}
