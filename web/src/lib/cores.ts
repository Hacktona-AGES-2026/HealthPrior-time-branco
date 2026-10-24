import { META } from "@/data/fila"
import type { Camada, Classe } from "@/data/tipos"

export const CLASSES: Classe[] = ["A1", "A2", "B", "C", "D"]

export const PRAZO_MAX = Object.fromEntries(META.swalis.map((c) => [c.classe, c.prazo])) as Record<Classe, number>

export const DESCRICAO_CLASSE = Object.fromEntries(META.swalis.map((c) => [c.classe, c.descricao])) as Record<Classe, string>

export const NOME_CAMADA: Record<Camada, string> = { 1: "Oncológico", 2: "Urgente", 3: "Demais" }

export const DESCRICAO_CAMADA: Record<Camada, string> = {
  1: "CID iniciado por C: nunca fica abaixo de quem não tem urgência",
  2: "Sinal clínico de urgência: complicação, piora na espera, biópsia positiva ou alarme no texto",
  3: "Sem sinais clínicos de urgência",
}

export const indiceClasse = (c: Classe) => CLASSES.indexOf(c)

export const corClasse = (c: Classe) => `var(--cls-${c.toLowerCase()})`
export const corTextoClasse = (c: Classe) => `var(--cls-${c.toLowerCase()}-fg)`

export const corPrazo = (pct: number) => {
  if (pct > 100) return "var(--prazo-vencido)"
  if (pct > 75) return "var(--prazo-limite)"
  if (pct > 50) return "var(--prazo-atencao)"
  return "var(--prazo-ok)"
}

export const rotuloPrazo = (pct: number) => {
  if (pct > 100) return "Vencido"
  if (pct > 75) return "No limite"
  if (pct > 50) return "Atenção"
  return "Dentro do prazo"
}

export const FAIXAS_PRAZO = [
  { de: 0, ate: 50, rotulo: "0–50% ideal", cor: "var(--prazo-ok)" },
  { de: 51, ate: 75, rotulo: "51–75% ótimo", cor: "var(--prazo-atencao)" },
  { de: 76, ate: 100, rotulo: "76–100% no limite", cor: "var(--prazo-limite)" },
  { de: 101, ate: Infinity, rotulo: ">100% vencido", cor: "var(--prazo-vencido)" },
]

export const COR_STATUS = {
  pendente: "var(--muted-foreground)",
  aprovado: "var(--sobe)",
  editado: "var(--cls-c)",
}
