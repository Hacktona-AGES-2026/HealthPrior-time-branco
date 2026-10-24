import { create } from "zustand"

type Preferencia = "light" | "dark" | "system"

const CHAVE = "healthprior-tema"

const lerPreferencia = (): Preferencia => {
  try {
    const salvo = localStorage.getItem(CHAVE)
    if (salvo === "light" || salvo === "dark" || salvo === "system") return salvo
  } catch {
    return "system"
  }
  return "system"
}

const sistemaEscuro = () => window.matchMedia("(prefers-color-scheme: dark)").matches

const resolver = (p: Preferencia) => (p === "system" ? (sistemaEscuro() ? "dark" : "light") : p)

const aplicar = (resolvido: "light" | "dark") => {
  document.documentElement.classList.toggle("dark", resolvido === "dark")
  document.documentElement.style.colorScheme = resolvido
}

type Estado = {
  preferencia: Preferencia
  resolvido: "light" | "dark"
  setTema: (p: Preferencia) => void
}

const inicial = lerPreferencia()

export const useTema = create<Estado>((set) => ({
  preferencia: inicial,
  resolvido: resolver(inicial),
  setTema: (p) => {
    try {
      localStorage.setItem(CHAVE, p)
    } catch {
      set({})
    }
    const resolvido = resolver(p)
    aplicar(resolvido)
    set({ preferencia: p, resolvido })
  },
}))

aplicar(useTema.getState().resolvido)

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  const { preferencia, setTema } = useTema.getState()
  if (preferencia === "system") setTema("system")
})
