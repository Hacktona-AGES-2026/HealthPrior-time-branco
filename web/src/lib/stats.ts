import type { Classe, Paciente } from "@/data/tipos"
import { FANTASMAS, PACIENTES, TOTAL_FILA } from "@/data/fila"
import { CLASSES } from "./cores"

export const mediana = (valores: number[]) => {
  if (valores.length === 0) return 0
  const ordenado = [...valores].sort((a, b) => a - b)
  const meio = Math.floor(ordenado.length / 2)
  return ordenado.length % 2 ? ordenado[meio] : (ordenado[meio - 1] + ordenado[meio]) / 2
}

export const medianasDaClasse = (classe: Classe) => {
  const grupo = PACIENTES.filter((p) => p.classe === classe)
  return {
    dias: mediana(grupo.map((p) => p.dias_em_fila)),
    dor: mediana(grupo.map((p) => p.intensidade_dor_eva)),
    idade: mediana(grupo.map((p) => p.idade)),
    sinais: mediana(grupo.map((p) => p.sinais.length)),
    n: grupo.length,
  }
}

export const variacaoPosicao = (p: Paciente) => p.posicao_antiga - p.posicao_nova

export const contarPorClasse = (lista: { classe: Classe }[]) =>
  Object.fromEntries(CLASSES.map((c) => [c, lista.filter((x) => x.classe === c).length])) as Record<Classe, number>

export const metricasGlobais = (decisoes: Record<string, { status: string }>) => {
  const mudaramDetalhados = PACIENTES.filter((p) => p.posicao_antiga !== p.posicao_nova).length
  const mudaramFantasmas = FANTASMAS.filter((f) => f.classe !== f.classe_antiga).length
  const vencidos = PACIENTES.filter((p) => p.prazo_consumido_pct > 100).length + FANTASMAS.filter((f) => f.prazo_consumido_pct > 100).length
  const oncologicosCorrigidos = PACIENTES.filter((p) => p.cid.startsWith("C") && p.classe_antiga !== p.classe).length
  const revisar = PACIENTES.filter((p) => p.divergencia || p.confianca < 0.6).length
  const revisados = PACIENTES.filter((p) => decisoes[p.solicitacao_id]).length
  return {
    total: TOTAL_FILA,
    mudaram: mudaramDetalhados + mudaramFantasmas,
    oncologicosCorrigidos,
    vencidos,
    revisar,
    revisados,
    totalDetalhados: PACIENTES.length,
  }
}
