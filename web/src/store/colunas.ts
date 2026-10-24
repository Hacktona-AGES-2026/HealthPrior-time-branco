import { create } from "zustand"
import type { CSSProperties } from "react"

export type DefinicaoColuna = { id: string; rotulo: string; padrao: number; min: number; max: number; flexivel?: boolean; minVw?: number }

export const COLUNAS: DefinicaoColuna[] = [
  { id: "pos", rotulo: "Posição", padrao: 72, min: 56, max: 140 },
  { id: "paciente", rotulo: "Paciente", padrao: 240, min: 120, max: 600, flexivel: true },
  { id: "classe", rotulo: "Classe", padrao: 100, min: 56, max: 160 }, // cabe "B → A2" (em vigor → proposta)
  { id: "prazo", rotulo: "Prazo", padrao: 150, min: 100, max: 320, minVw: 768 },
  { id: "status", rotulo: "Situação", padrao: 112, min: 90, max: 200 },
]

const CHAVE = "healthprior-colunas-v6"
const PAINEL_PADRAO = 340
export const ALTURA_FAIXA_PADRAO = 192
export const ALTURA_FAIXA_MIN = 140
export const ALTURA_FAIXA_MAX = 340

const padroes = () => Object.fromEntries(COLUNAS.map((c) => [c.id, c.padrao])) as Record<string, number>

const ler = (): { larguras: Record<string, number>; painel: number; alturaFaixa: number } => {
  try {
    const bruto = localStorage.getItem(CHAVE)
    if (bruto) {
      const dado = JSON.parse(bruto)
      return { larguras: { ...padroes(), ...dado.larguras }, painel: dado.painel ?? PAINEL_PADRAO, alturaFaixa: dado.alturaFaixa ?? ALTURA_FAIXA_PADRAO }
    }
  } catch {
    return { larguras: padroes(), painel: PAINEL_PADRAO, alturaFaixa: ALTURA_FAIXA_PADRAO }
  }
  return { larguras: padroes(), painel: PAINEL_PADRAO, alturaFaixa: ALTURA_FAIXA_PADRAO }
}

const salvar = (larguras: Record<string, number>, painel: number, alturaFaixa: number) => {
  try {
    localStorage.setItem(CHAVE, JSON.stringify({ larguras, painel, alturaFaixa }))
  } catch {
    return
  }
}

type Estado = {
  larguras: Record<string, number>
  painel: number
  alturaFaixa: number
  faixaOculta: boolean
  painelOculto: boolean
  ocultas: Record<string, boolean>
  alternarColuna: (id: string) => void
  setPainelOculto: (v: boolean) => void
  setFaixaOculta: (v: boolean) => void
  setAlturaFaixa: (valor: number) => void
  setLargura: (id: string, valor: number) => void
  resetar: (id: string) => void
  resetarTudo: () => void
  setPainel: (valor: number) => void
}

const lerOculta = () => {
  try {
    return localStorage.getItem("healthprior-faixa-oculta") === "1"
  } catch {
    return false
  }
}

const lerOcultas = (): Record<string, boolean> => {
  try {
    return JSON.parse(localStorage.getItem("healthprior-colunas-ocultas") ?? "{}")
  } catch {
    return {}
  }
}

const inicial = ler()

export const useColunas = create<Estado>((set, get) => ({
  larguras: inicial.larguras,
  painel: inicial.painel,
  alturaFaixa: inicial.alturaFaixa,
  painelOculto: (() => {
    try {
      return localStorage.getItem("healthprior-painel-oculto") === "1"
    } catch {
      return false
    }
  })(),
  setPainelOculto: (v) => {
    try {
      localStorage.setItem("healthprior-painel-oculto", v ? "1" : "0")
    } catch {
      set({})
    }
    set({ painelOculto: v })
  },
  ocultas: lerOcultas(),
  alternarColuna: (id) => {
    const ocultas = { ...get().ocultas, [id]: !get().ocultas[id] }
    try {
      localStorage.setItem("healthprior-colunas-ocultas", JSON.stringify(ocultas))
    } catch {
      set({})
    }
    set({ ocultas })
  },
  faixaOculta: lerOculta(),
  setFaixaOculta: (v) => {
    try {
      localStorage.setItem("healthprior-faixa-oculta", v ? "1" : "0")
    } catch {
      set({})
    }
    set({ faixaOculta: v })
  },
  setAlturaFaixa: (valor) => {
    const alturaFaixa = Math.round(Math.min(ALTURA_FAIXA_MAX, Math.max(ALTURA_FAIXA_MIN, valor)))
    set({ alturaFaixa })
    salvar(get().larguras, get().painel, alturaFaixa)
  },
  setLargura: (id, valor) => {
    const def = COLUNAS.find((c) => c.id === id)
    if (!def) return
    const larguras = { ...get().larguras, [id]: Math.round(Math.min(def.max, Math.max(def.min, valor))) }
    set({ larguras })
    salvar(larguras, get().painel, get().alturaFaixa)
  },
  resetar: (id) => {
    const def = COLUNAS.find((c) => c.id === id)
    if (def) get().setLargura(id, def.padrao)
  },
  resetarTudo: () => {
    try {
      localStorage.removeItem("healthprior-colunas-ocultas")
    } catch {
      set({})
    }
    set({ larguras: padroes(), painel: PAINEL_PADRAO, alturaFaixa: ALTURA_FAIXA_PADRAO, ocultas: {} })
    salvar(padroes(), PAINEL_PADRAO, ALTURA_FAIXA_PADRAO)
  },
  setPainel: (valor) => {
    const painel = Math.round(Math.min(560, Math.max(280, valor)))
    set({ painel })
    salvar(get().larguras, painel, get().alturaFaixa)
  },
}))

const vw = () => (typeof window === "undefined" ? 1920 : window.innerWidth)

if (typeof window !== "undefined" && typeof window.matchMedia === "function") {
  for (const px of [640, 768, 1024, 1280, 1536]) {
    window.matchMedia(`(min-width: ${px}px)`).addEventListener("change", () => useColunas.setState((s) => ({ larguras: { ...s.larguras } })))
  }
}

export const estiloColuna = (id: string, larguras: Record<string, number>, ocultas: Record<string, boolean> = {}): CSSProperties => {
  const def = COLUNAS.find((c) => c.id === id)
  if (ocultas[id] || (def?.minVw && vw() < def.minVw)) return { display: "none" }
  const w = larguras[id] ?? def?.padrao ?? 100
  if (def?.flexivel) return { flex: `1 1 ${w}px`, minWidth: 0 }
  return { width: w, flex: "none" }
}
