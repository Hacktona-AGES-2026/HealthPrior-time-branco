import { create } from "zustand"
import type { CSSProperties } from "react"

export type DefinicaoColuna = { id: string; rotulo: string; padrao: number; min: number; max: number; flexivel?: boolean }

export const COLUNAS: DefinicaoColuna[] = [
  { id: "pos", rotulo: "Nova", padrao: 52, min: 44, max: 120 },
  { id: "antiga", rotulo: "Antiga", padrao: 84, min: 64, max: 180 },
  { id: "classe", rotulo: "Classe", padrao: 76, min: 56, max: 160 },
  { id: "prazo", rotulo: "Prazo", padrao: 130, min: 80, max: 320 },
  { id: "sinais", rotulo: "Sinais", padrao: 180, min: 70, max: 520, flexivel: true },
  { id: "justificativa", rotulo: "Justificativa", padrao: 240, min: 80, max: 900, flexivel: true },
  { id: "alerta", rotulo: "", padrao: 28, min: 28, max: 28 },
  { id: "status", rotulo: "Status", padrao: 92, min: 70, max: 200 },
]

const CHAVE = "healthprior-colunas"
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
    set({ larguras: padroes(), painel: PAINEL_PADRAO, alturaFaixa: ALTURA_FAIXA_PADRAO })
    salvar(padroes(), PAINEL_PADRAO, ALTURA_FAIXA_PADRAO)
  },
  setPainel: (valor) => {
    const painel = Math.round(Math.min(560, Math.max(280, valor)))
    set({ painel })
    salvar(get().larguras, painel, get().alturaFaixa)
  },
}))

export const estiloColuna = (id: string, larguras: Record<string, number>): CSSProperties => {
  const def = COLUNAS.find((c) => c.id === id)
  const w = larguras[id]
  if (def?.flexivel) return { flex: `1 1 ${w}px`, minWidth: 0 }
  return { width: w, flex: "none" }
}
