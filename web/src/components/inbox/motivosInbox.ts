import type { ItemInbox } from "@/api/cliente"

const FRASE_CATEGORIA: Record<string, string> = {
  risco_vida: "Risco de vida no texto",
  cancer_confirmado: "Câncer confirmado",
  suspeita_malignidade: "Suspeita de câncer no texto",
  obstrucao: "Obstrução descrita",
  perda_funcao: "Perda de função",
  dor_intensa: "Dor intensa",
  sintoma_grave: "Sintoma grave",
  sintoma_moderado: "Sintoma moderado",
}

/** Ordem de importância clínica para escolher o que aparece primeiro. */
const ORDEM = Object.values(FRASE_CATEGORIA)

export type MotivosInbox = { frases: string[]; trecho: string | null }

/** Traduz os motivos brutos da API em até `max` frases curtas, sem códigos, probabilidades ou nomes internos. */
export function motivosDoInbox(item: ItemInbox, max = 3): MotivosInbox {
  const achados = new Set<string>()
  let trecho: string | null = null

  for (const m of item.motivos) {
    const partes = m.sinal.split(":")
    if ((partes[0] === "ponto" || partes[0] === "revisar") && FRASE_CATEGORIA[partes[1] ?? ""]) {
      achados.add(FRASE_CATEGORIA[partes[1]])
      if (!trecho && m.evidencia && partes[0] === "ponto") trecho = m.evidencia
      continue
    }
    if (partes[0] === "eixo_progressao" || partes[0] === "eixo_sintoma") {
      const t = m.evidencia
      for (const c of t.matchAll(/→ (\w+)/g)) if (FRASE_CATEGORIA[c[1]]) achados.add(FRASE_CATEGORIA[c[1]])
      if (/neoplasia maligna/i.test(t)) achados.add("Câncer confirmado")
      if (/biópsia positiva/i.test(t)) achados.add("Biópsia positiva")
      if (/CID de obstrução/i.test(t)) achados.add("Obstrução registrada")
      if (/piora na espera/i.test(t)) achados.add("Piorou na espera")
      const dor = t.match(/dor EVA (\d+)/i)
      if (dor && Number(dor[1]) >= 4) achados.add(`Dor ${dor[1]}/10`)
      const lim = t.match(/limitação(?: funcional)? (moderada|grave)/i)
      if (lim) achados.add(`Limitação ${lim[1].toLowerCase()}`)
    }
  }

  const rank = (f: string) => {
    const i = ORDEM.indexOf(f)
    return i === -1 ? ORDEM.length : i
  }
  const frases = [...achados].sort((a, b) => rank(a) - rank(b)).slice(0, max)
  return { frases, trecho }
}

/** Prazo em linguagem simples; evita "8.747%". */
export function frasePrazo(pct: number): string {
  if (pct < 100) return `${Math.round(pct)}% do prazo`
  if (pct < 300) return `prazo ultrapassado (${Math.round(pct)}%)`
  return "prazo muito ultrapassado"
}
