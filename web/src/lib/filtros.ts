import type { Classe, Paciente } from "@/data/tipos"

export type Pagina = "fila" | "pacientes" | "analise" | "swalis"

export type Decisao = {
  status: "aprovado" | "rejeitado"
  classeFinal: Classe
  motivo?: string
}

export type StatusFiltro = "todos" | "pendentes" | "revisados" | "aprovados" | "rejeitados"

export type Filtros = {
  busca: string
  especialidade: string
  classe: string
  oncologicos: boolean
  vencidos: boolean
  mudou: boolean
  divergencia: boolean
  status: StatusFiltro
}

export const FILTROS_VAZIOS: Filtros = {
  busca: "",
  especialidade: "todas",
  classe: "todas",
  oncologicos: false,
  vencidos: false,
  mudou: false,
  divergencia: false,
  status: "todos",
}

export const normalizar = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()

export const ehOncologico = (p: Paciente) => p.cid.startsWith("C")

export const precisaRevisar = (p: Paciente) => p.divergencia || p.confianca < 0.6

export const mudouPosicao = (p: Paciente) => p.posicao_antiga !== p.posicao_nova

export const statusDe = (decisoes: Record<string, Decisao>, id: string): "pendente" | Decisao["status"] =>
  decisoes[id]?.status ?? "pendente"

export const aplicarFiltros = (pacientes: Paciente[], f: Filtros, decisoes: Record<string, Decisao>) => {
  const termo = normalizar(f.busca.trim())
  return pacientes.filter((p) => {
    if (termo) {
      const alvo = normalizar([p.solicitacao_id, p.cid, p.procedimento, p.iniciais, p.cid_descricao].join(" "))
      if (!alvo.includes(termo)) return false
    }
    if (f.especialidade !== "todas" && p.especialidade !== f.especialidade) return false
    if (f.classe !== "todas" && p.classe !== f.classe) return false
    if (f.oncologicos && !ehOncologico(p)) return false
    if (f.vencidos && p.prazo_consumido_pct <= 100) return false
    if (f.mudou && !mudouPosicao(p)) return false
    if (f.divergencia && !precisaRevisar(p)) return false
    if (f.status !== "todos") {
      const st = statusDe(decisoes, p.solicitacao_id)
      if (f.status === "pendentes" && st !== "pendente") return false
      if (f.status === "revisados" && st === "pendente") return false
      if (f.status === "aprovados" && st !== "aprovado") return false
      if (f.status === "rejeitados" && st !== "rejeitado") return false
    }
    return true
  })
}
