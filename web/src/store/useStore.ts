import { create } from "zustand"
import { toast } from "sonner"
import { PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import type { Classe } from "@/data/tipos"
import { FILTROS_VAZIOS, aplicarFiltros, type Decisao, type Filtros, type Pagina } from "@/lib/filtros"

type Zoom = [number, number] | null

type Estado = {
  pagina: Pagina
  selecionadoId: string | null
  expandidoId: string | null
  sidebarAberta: boolean
  filtros: Filtros
  zoom: Zoom
  decisoes: Record<string, Decisao>
  rejeitando: boolean
  atalhosAbertos: boolean
  ir: (pagina: Pagina) => void
  selecionar: (id: string | null, expandir?: boolean) => void
  alternarExpandido: (id: string) => void
  recolher: () => void
  setSidebar: (aberta: boolean) => void
  setFiltros: (parcial: Partial<Filtros>) => void
  limparFiltros: () => void
  setZoom: (zoom: Zoom) => void
  setRejeitando: (v: boolean) => void
  setAtalhos: (v: boolean) => void
  aprovar: (id: string) => void
  rejeitar: (id: string, classe: Classe, motivo: string) => void
  desfazer: (id: string) => void
  navegarPendente: (direcao: 1 | -1) => void
  abrirNaFila: (id: string) => void
  abrirFicha: (id: string) => void
}

const inicialAberta = () => (typeof window === "undefined" ? true : window.innerWidth > 1100)

export const useStore = create<Estado>((set, get) => {
  const proximoPendente = (partirDe: string | null, direcao: 1 | -1) => {
    const { filtros, decisoes } = get()
    const filtrada = aplicarFiltros(PACIENTES, { ...filtros, status: "todos" }, decisoes)
    const universo = filtrada.length > 0 ? filtrada : PACIENTES
    const n = universo.length
    const inicio = partirDe ? universo.findIndex((p) => p.solicitacao_id === partirDe) : -1
    for (let passo = 1; passo <= n; passo++) {
      const i = inicio === -1 ? (direcao === 1 ? passo - 1 : n - passo) : (((inicio + direcao * passo) % n) + n) % n
      const candidato = universo[i]
      if (!decisoes[candidato.solicitacao_id] && candidato.solicitacao_id !== partirDe) return candidato.solicitacao_id
    }
    return null
  }

  const avancar = (idAtual: string) => {
    const proximo = proximoPendente(idAtual, 1)
    if (proximo) {
      set({ selecionadoId: proximo, expandidoId: proximo, rejeitando: false })
    } else {
      set({ rejeitando: false })
      toast.success("Todos os casos da lista foram revisados")
    }
  }

  return {
    pagina: "fila",
    selecionadoId: null,
    expandidoId: null,
    sidebarAberta: inicialAberta(),
    filtros: FILTROS_VAZIOS,
    zoom: null,
    decisoes: {},
    rejeitando: false,
    atalhosAbertos: false,
    ir: (pagina) => set({ pagina }),
    selecionar: (id, expandir = true) =>
      set({ selecionadoId: id, expandidoId: id && expandir ? id : null, rejeitando: false }),
    alternarExpandido: (id) =>
      set((s) =>
        s.expandidoId === id
          ? { expandidoId: null }
          : { selecionadoId: id, expandidoId: id, rejeitando: false }
      ),
    recolher: () => set({ expandidoId: null, rejeitando: false }),
    setSidebar: (aberta) => set({ sidebarAberta: aberta }),
    setFiltros: (parcial) => set((s) => ({ filtros: { ...s.filtros, ...parcial } })),
    limparFiltros: () => set({ filtros: FILTROS_VAZIOS }),
    setZoom: (zoom) => set({ zoom }),
    setRejeitando: (v) => set({ rejeitando: v }),
    setAtalhos: (v) => set({ atalhosAbertos: v }),
    aprovar: (id) => {
      const p = PACIENTE_POR_ID[id]
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "aprovado", classeFinal: p.classe } } }))
      toast.success(`${id} aprovado`, { description: `${p.iniciais} · classe ${p.classe} · posição ${p.posicao_nova}` })
      avancar(id)
    },
    rejeitar: (id, classe, motivo) => {
      const p = PACIENTE_POR_ID[id]
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "rejeitado", classeFinal: classe, motivo } } }))
      toast.error(`${id} rejeitado`, { description: `${p.iniciais} · classe final ${classe}` })
      avancar(id)
    },
    desfazer: (id) =>
      set((s) => {
        const copia = { ...s.decisoes }
        delete copia[id]
        return { decisoes: copia }
      }),
    navegarPendente: (direcao) => {
      const { selecionadoId } = get()
      const proximo = proximoPendente(selecionadoId, direcao)
      if (proximo) set({ selecionadoId: proximo, expandidoId: proximo, rejeitando: false })
      else toast.info("Nenhum caso pendente na lista")
    },
    abrirNaFila: (id) => set({ pagina: "fila", selecionadoId: id, expandidoId: id, rejeitando: false }),
    abrirFicha: (id) => set({ pagina: "pacientes", selecionadoId: id, rejeitando: false }),
  }
})
