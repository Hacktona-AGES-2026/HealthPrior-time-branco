import type { Paciente } from "@/data/tipos"

/** Traduz os motivos internos para frases de consultório. Retorna [] para o que não ajuda a decidir. */
function traduzir(texto: string): string[] {
  const t = texto.trim()
  if (/^nenhum risco/i.test(t)) return []
  const frases: string[] = []
  const dor = t.match(/^dor EVA (\d+)/i)
  if (dor) {
    if (Number(dor[1]) > 0) frases.push(`Dor ${dor[1]}/10`)
    const lim = t.match(/limitação (leve|moderada|grave)/i)
    if (lim) frases.push(`Limitação ${lim[1].toLowerCase()}`)
    return frases
  }
  const lf = t.match(/^limitação funcional (\w+)/i)
  if (lf) return lf[1] === "nenhuma" ? [] : [`Limitação ${lf[1]}`]
  if (/piora durante a espera/i.test(t)) return ["Piorou na espera"]
  if (/sinal de alarme/i.test(t)) return ["Sinal de alarme"]
  if (/biópsia positiva com CID não oncológico/i.test(t)) return ["Biópsia positiva; conferir CID"]
  const neo = t.match(/neoplasia maligna pelo CID (\S+)/i)
  if (neo) return ["Câncer confirmado"]
  if (/^biópsia positiva/i.test(t)) return ["Biópsia positiva"]
  if (/dor não informada/i.test(t)) return ["Dor não informada"]
  return [t.charAt(0).toUpperCase() + t.slice(1)]
}

const FRASE_SINAL = {
  risco_vida: "Sinal de alarme",
  suspeita_malignidade: "Suspeita de malignidade no texto",
  sintoma_grave: "Sintoma grave descrito",
} as const

/** Motivos da prioridade em frases curtas, sem repetição. */
export function motivosClinicos(p: Paciente, max = 3): string[] {
  const todos = [...p.motivos, ...p.sintomas].flatMap(traduzir)
  const sinais = (p.sinais_texto ?? []).map((s) => FRASE_SINAL[s.categoria]).filter(Boolean)
  const lista = [...(p.oncologico && !todos.some((f) => f.startsWith("Câncer")) ? ["Oncológico"] : []), ...todos, ...sinais]
  return [...new Set(lista)].slice(0, max)
}
