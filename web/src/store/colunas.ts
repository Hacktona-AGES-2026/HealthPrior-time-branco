import { create } from "zustand"
import type { CSSProperties } from "react"

export type DefinicaoColuna = { id: string; rotulo: string; padrao: number; min: number; max: number; flexivel?: boolean; minVw?: number; compacto?: number }

export const COLUNAS: DefinicaoColuna[] = [
  { id: "pos", rotulo: "Proposta", padrao: 76, min: 52, max: 140 },
  { id: "antiga", rotulo: "Atual", padrao: 96, min: 70, max: 180, minVw: 768 },
  { id: "classe", rotulo: "Classe", padrao: 84, min: 56, max: 160, compacto: 64 },
  { id: "camada", rotulo: "Camada", padrao: 82, min: 56, max: 160, minVw: 1024 },
  { id: "prazo", rotulo: "Prazo", padrao: 130, min: 80, max: 320, compacto: 96 },
  { id: "sinais", rotulo: "Motivos", padrao: 180, min: 70, max: 520, flexivel: true, minVw: 1280 },
  { id: "justificativa", rotulo: "Justificativa", padrao: 240, min: 80, max: 900, flexivel: true, minVw: 1536 },
  { id: "alerta", rotulo: "", padrao: 28, min: 28, max: 28, minVw: 768 },
  { id: "status", rotulo: "Status", padrao: 92, min: 70, max: 200, compacto: 80 },
]

const CHAVE = "healthprior-colunas-v4"
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
  const largura = vw()
  const w = def?.compacto && largura < 640 ? Math.min(larguras[id], def.compacto) : larguras[id]
  if (ocultas[id] || (def?.minVw && largura < def.minVw)) return { display: "none" }
  if (def?.flexivel) return { flex: `1 1 ${w}px`, minWidth: 0 }
  return { width: w, flex: "none" }
}
