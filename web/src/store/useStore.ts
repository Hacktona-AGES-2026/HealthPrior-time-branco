import { create } from "zustand"
import { toast } from "sonner"
import { ORIGEM_DADOS, PACIENTES, PACIENTE_POR_ID, carregarFila } from "@/data/fila"
import type { Classe } from "@/data/tipos"
import { ErroApi, decidir, type MotivoCodificado } from "@/lib/api"
import { FILTROS_VAZIOS, aplicarFiltros, type Decisao, type Filtros, type Pagina } from "@/lib/filtros"

type Zoom = [number, number] | null

// Sem login no hackathon: o seletor de persona (US-23) ainda não existe.
export const REGULADOR_ID = "REG-DEMO"

/** Decisões já gravadas na API (classe confirmada) viram o status do card. */
export const decisoesDaApi = (): Record<string, Decisao> =>
  Object.fromEntries(
    PACIENTES.filter((p) => p.classe_status === "confirmada").map((p) => [
      p.solicitacao_id,
      { status: p.editado_manualmente ? "rejeitado" : "aprovado", classeFinal: p.classe_antiga } as Decisao,
    ])
  )

const mensagemErro = (e: unknown) => (e instanceof ErroApi ? `${e.codigo}: ${e.message}` : String(e))

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
  versaoDados: number
  enviando: boolean
  recarregar: () => Promise<void>
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
  rejeitar: (id: string, classe: Classe, motivo: string, motivoCodificado?: MotivoCodificado) => void
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

  const enviarDecisao = async (id: string, corpo: Omit<Parameters<typeof decidir>[0], "solicitacao_id" | "regulador_id">, titulo: string) => {
    set({ enviando: true })
    try {
      const r = await decidir({ solicitacao_id: id, regulador_id: REGULADOR_ID, ...corpo })
      await get().recarregar()
      const mov = r.posicao_anterior != null && r.posicao_nova != null ? `posição ${r.posicao_anterior} → ${r.posicao_nova}` : ""
      toast.success(titulo, {
        description: r.fila_publicada ? `${mov} · fila republicada (verificador OK)` : `${mov} · fila não publicada: verificador reprovou`,
      })
      avancar(id)
    } catch (e) {
      toast.error("Decisão recusada", { description: mensagemErro(e) })
    } finally {
      set({ enviando: false, rejeitando: false })
    }
  }

  return {
    pagina: "fila",
    selecionadoId: null,
    expandidoId: null,
    sidebarAberta: inicialAberta(),
    filtros: FILTROS_VAZIOS,
    zoom: null,
    decisoes: decisoesDaApi(),
    rejeitando: false,
    atalhosAbertos: false,
    versaoDados: 0,
    enviando: false,
    recarregar: async () => {
      await carregarFila()
      set((s) => ({ versaoDados: s.versaoDados + 1, decisoes: decisoesDaApi() }))
    },
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
      if (ORIGEM_DADOS === "api") {
        void enviarDecisao(id, { acao: "aprovar" }, `${id} aprovado · classe ${p.classe}`)
        return
      }
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "aprovado", classeFinal: p.classe } } }))
      toast.success(`${id} aprovado`, { description: `${p.iniciais} · classe ${p.classe} · posição ${p.posicao_nova}` })
      avancar(id)
    },
    rejeitar: (id, classe, motivo, motivoCodificado = "outro") => {
      const p = PACIENTE_POR_ID[id]
      if (ORIGEM_DADOS === "api") {
        void enviarDecisao(
          id,
          { acao: "editar", classe, motivo_codificado: motivoCodificado, justificativa: motivo },
          `${id}: classe definida como ${classe}`
        )
        return
      }
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "rejeitado", classeFinal: classe, motivo } } }))
      toast.error(`${id} rejeitado`, { description: `${p.iniciais} · classe final ${classe}` })
      avancar(id)
    },
    desfazer: (id) => {
      if (ORIGEM_DADOS === "api") {
        toast.info("Decisão já registrada no log", { description: "Para mudar, edite a classe de novo com justificativa." })
        return
      }
      set((s) => {
        const copia = { ...s.decisoes }
        delete copia[id]
        return { decisoes: copia }
      })
    },
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
