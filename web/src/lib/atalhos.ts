import { useEffect } from "react"
import { toast } from "sonner"
import { useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

const ehCampoDeTexto = (alvo: EventTarget | null) => {
  if (!(alvo instanceof HTMLElement)) return false
  return alvo.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(alvo.tagName)
}

export const useAtalhos = (alternarMenu: () => void) => {
  useEffect(() => {
    const aoPressionar = (e: KeyboardEvent) => {
      const s = useStore.getState()
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        s.setPaleta(!s.paletaAberta)
        return
      }
      if (e.metaKey || e.ctrlKey || e.altKey) return
      if (e.key === "Escape") {
        if (s.rejeitando) s.setRejeitando(false)
        else if (s.expandidoId) s.recolher()
        return
      }
      if (ehCampoDeTexto(e.target)) return
      if (document.querySelector('[role="dialog"]')) return
      const tecla = e.key.toLowerCase()
      if (tecla === "[") {
        e.preventDefault()
        alternarMenu()
        return
      }
      if (e.key === "/") {
        e.preventDefault()
        if (s.pagina !== "fila") s.ir("fila")
        setTimeout(() => document.getElementById("busca-fila")?.focus(), 60)
        return
      }
      if (s.pagina === "fila" && (e.key === "ArrowDown" || e.key === "ArrowUp")) {
        e.preventDefault()
        s.mover(e.key === "ArrowDown" ? 1 : -1)
        return
      }
      if (s.pagina === "fila" && e.key === "Enter" && s.selecionadoId && document.activeElement === document.body) {
        s.alternarExpandido(s.selecionadoId)
        return
      }
      if (tecla === "]") {
        const c = useColunas.getState()
        c.setPainelOculto(!c.painelOculto)
        return
      }
      if (e.key === "?") {
        s.setAtalhos(true)
        return
      }
      if (s.pagina !== "fila" && s.pagina !== "pacientes") return
      if (tecla === "j") s.navegarPendente(1)
      else if (tecla === "k") s.navegarPendente(-1)
      else if (tecla === "a" || tecla === "r") {
        if (!s.selecionadoId) {
          toast.info("Selecione um caso primeiro")
          return
        }
        if (s.decisoes[s.selecionadoId]) {
          toast.info("Este caso já foi revisado", { description: "Use Desfazer no painel para revisar de novo" })
          return
        }
        if (tecla === "a") s.aprovar(s.selecionadoId)
        else s.setRejeitando(true)
      }
    }
    window.addEventListener("keydown", aoPressionar)
    return () => window.removeEventListener("keydown", aoPressionar)
  }, [alternarMenu])
}
