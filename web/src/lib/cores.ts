import type { Classe } from "@/data/tipos"

export const CLASSES: Classe[] = ["A1", "A2", "B", "C", "D"]

export const PRAZO_MAX: Record<Classe, number> = { A1: 15, A2: 21, B: 60, C: 180, D: 360 }

export const DESCRICAO_CLASSE: Record<Classe, string> = {
  A1: "Risco de vida ou perda de órgão/função",
  A2: "Risco de agravamento ou incapacidade",
  B: "Dor, disfunção ou incapacidade importantes",
  C: "Dor ou disfunção moderadas",
  D: "Sem dor ou disfunção relevantes",
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
  rejeitado: "var(--desce)",
}

export const COR_ORIGEM: Record<string, string> = {
  cid: "var(--cls-c)",
  sintomas: "oklch(0.7 0.16 130)",
  eventos: "var(--cls-a2)",
  texto_llm: "oklch(0.62 0.15 300)",
  fragilidade: "oklch(0.62 0.12 185)",
  regra_ouro: "var(--ouro)",
}

export const ROTULO_ORIGEM: Record<string, string> = {
  cid: "CID",
  sintomas: "Sintomas",
  eventos: "Eventos",
  texto_llm: "Texto (LLM)",
  fragilidade: "Fragilidade",
  regra_ouro: "Regra de ouro",
}
