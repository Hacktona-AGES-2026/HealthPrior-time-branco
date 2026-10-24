import { ORIGEM_DADOS, PACIENTE_POR_ID } from "@/data/fila"
import { FILTROS_VAZIOS, type Pagina } from "@/lib/filtros"
import { useStore } from "@/store/useStore"

const CHAVE = "healthprior-estado-v1"
const PAGINAS: Pagina[] = ["fila", "inbox", "pacientes", "analise", "swalis", "pendencias", "propostas", "notificacoes"]

const aplicarHash = () => {
  const [, pagina, id] = window.location.hash.split("/")
  if (!PAGINAS.includes(pagina as Pagina)) return
  const idValido = id && PACIENTE_POR_ID[id] ? id : null
  const s = useStore.getState()
  const fichaId = pagina === "pacientes" ? idValido : null
  if (s.pagina !== pagina || (idValido && s.selecionadoId !== idValido) || s.fichaId !== fichaId) {
    useStore.setState({
      pagina: pagina as Pagina,
      fichaId,
      selecionadoId: idValido ?? s.selecionadoId,
      expandidoId: s.expandidoId,
    })
  }
}

const escreverHash = () => {
  const { pagina, selecionadoId, fichaId } = useStore.getState()
  const idHash = pagina === "fila" ? selecionadoId : pagina === "pacientes" ? fichaId : null
  const alvo = `#/${pagina}${idHash ? `/${idHash}` : ""}`
  if (window.location.hash !== alvo) window.history.replaceState(null, "", alvo)
}

export const iniciarPersistencia = () => {
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE) ?? "{}")
    useStore.setState({
      decisoes: ORIGEM_DADOS === "api" ? useStore.getState().decisoes : (salvo.decisoes ?? {}),
      filtros: { ...FILTROS_VAZIOS, ...(salvo.filtros ?? {}) },
      pagina: PAGINAS.includes(salvo.pagina) ? salvo.pagina : "fila",
      selecionadoId: salvo.selecionadoId && PACIENTE_POR_ID[salvo.selecionadoId] ? salvo.selecionadoId : null,
      expandidoId: null,
    })
  } catch {
    localStorage.removeItem(CHAVE)
  }
  aplicarHash()
  escreverHash()
  useStore.subscribe((s) => {
    try {
      localStorage.setItem(
        CHAVE,
        JSON.stringify({ decisoes: ORIGEM_DADOS === "api" ? {} : s.decisoes, filtros: s.filtros, pagina: s.pagina, selecionadoId: s.selecionadoId, expandidoId: s.expandidoId })
      )
    } catch {
      return
    }
    escreverHash()
  })
  window.addEventListener("hashchange", aplicarHash)
}
