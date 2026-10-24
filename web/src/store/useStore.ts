import { create } from "zustand"
import { toast } from "sonner"
import { ORIGEM_DADOS, PACIENTES, PACIENTE_POR_ID, carregarFila } from "@/data/fila"
import type { Classe, Paciente } from "@/data/tipos"
import { ErroApi, decidir, limparCacheDetalhe } from "@/lib/api"
import { reguladorAtual } from "@/lib/usuario"
import { FILTROS_VAZIOS, aplicarFiltros, type Decisao, type Filtros, type MotivoCodificado, type Pagina } from "@/lib/filtros"

type Zoom = [number, number] | null


export const decisoesDaApi = (): Record<string, Decisao> =>
  Object.fromEntries(
    PACIENTES.filter((p) => p.classe_status === "confirmada").map((p) => [
      p.id,
      { status: p.editado_manualmente ? "editado" : "aprovado", classeFinal: p.classe_vigente ?? p.classe } as Decisao,
    ])
  )

const mensagemErro = (e: unknown) => (e instanceof ErroApi ? `${e.codigo}: ${e.message}` : String(e))

type Estado = {
  pagina: Pagina
  destaqueSwalis: { classe: Classe; pacienteId: string; iniciais: string } | null
  abrirSwalis: (p: Paciente) => void
  limparDestaqueSwalis: () => void
  selecionadoId: string | null
  fichaId: string | null
  expandidoId: string | null
  sidebarAberta: boolean
  filtros: Filtros
  zoom: Zoom
  decisoes: Record<string, Decisao>
  rejeitando: boolean
  atalhosAbertos: boolean
  paletaAberta: boolean
  versaoDados: number
  enviando: boolean
  recarregar: () => Promise<void>
  marcados: string[]
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
  setPaleta: (v: boolean) => void
  alternarMarcado: (id: string) => void
  marcarVarios: (ids: string[], ligado: boolean) => void
  limparMarcados: () => void
  aprovarLote: (ids: string[]) => void
  mover: (direcao: 1 | -1) => void
  irParaPosicao: (posicao: number) => boolean
  aprovar: (id: string) => void
  editar: (id: string, classe: Classe, motivoCodificado: MotivoCodificado, motivo: string) => void
  desfazer: (id: string) => void
  navegarPendente: (direcao: 1 | -1) => void
  abrirNaFila: (id: string) => void
  abrirFicha: (id: string) => void
  fecharFicha: () => void
}

const inicialAberta = () => (typeof window === "undefined" ? true : window.innerWidth > 1100)

export const useStore = create<Estado>((set, get) => {
  const proximoPendente = (partirDe: string | null, direcao: 1 | -1) => {
    const { filtros, decisoes } = get()
    const filtrada = aplicarFiltros(PACIENTES, { ...filtros, status: "todos" }, decisoes)
    const universo = filtrada.length > 0 ? filtrada : PACIENTES
    const n = universo.length
    const inicio = partirDe ? universo.findIndex((p) => p.id === partirDe) : -1
    for (let passo = 1; passo <= n; passo++) {
      const i = inicio === -1 ? (direcao === 1 ? passo - 1 : n - passo) : (((inicio + direcao * passo) % n) + n) % n
      const candidato = universo[i]
      if (!decisoes[candidato.id] && candidato.id !== partirDe) return candidato.id
    }
    return null
  }

  const enviarDecisao = async (id: string, corpo: Omit<Parameters<typeof decidir>[0], "solicitacao_id" | "regulador_id">, titulo: string) => {
    set({ enviando: true })
    try {
      const r = await decidir({ solicitacao_id: id, regulador_id: reguladorAtual(), ...corpo })
      await get().recarregar()
      const mov = r.posicao_anterior != null && r.posicao_nova != null ? `posição ${r.posicao_anterior} → ${r.posicao_nova}` : ""
      toast.success(titulo, { description: r.fila_publicada ? `${mov} · fila republicada (verificador OK)` : `${mov} · fila não publicada: verificador reprovou` })
      avancar(id)
    } catch (e) {
      toast.error("Decisão recusada", { description: mensagemErro(e) })
    } finally {
      set({ enviando: false, rejeitando: false })
    }
  }

  const desfazerERetornar = (id: string) =>
    set((s) => {
      const copia = { ...s.decisoes }
      delete copia[id]
      return { decisoes: copia, selecionadoId: id, expandidoId: id, rejeitando: false }
    })

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
    destaqueSwalis: null,
    abrirSwalis: (p) => set({ pagina: "swalis", destaqueSwalis: { classe: p.classe, pacienteId: p.id, iniciais: p.iniciais } }),
    limparDestaqueSwalis: () => set({ destaqueSwalis: null }),
    selecionadoId: null,
    fichaId: null,
    expandidoId: null,
    sidebarAberta: inicialAberta(),
    filtros: FILTROS_VAZIOS,
    zoom: null,
    decisoes: ORIGEM_DADOS === "api" ? decisoesDaApi() : {},
    rejeitando: false,
    atalhosAbertos: false,
    paletaAberta: false,
    versaoDados: 0,
    enviando: false,
    recarregar: async () => {
      limparCacheDetalhe()  // a ficha busca de novo: eventos e decisões novos aparecem
      await carregarFila()
      set((s) => ({ versaoDados: s.versaoDados + 1, decisoes: decisoesDaApi() }))
    },
    marcados: [],
    ir: (pagina) => set(pagina === "pacientes" ? { pagina, fichaId: null } : pagina === "swalis" ? { pagina, destaqueSwalis: null } : { pagina }),
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
    setPaleta: (v) => set({ paletaAberta: v }),
    alternarMarcado: (id) => set((s) => ({ marcados: s.marcados.includes(id) ? s.marcados.filter((m) => m !== id) : [...s.marcados, id] })),
    marcarVarios: (ids, ligado) =>
      set((s) => ({ marcados: ligado ? [...new Set([...s.marcados, ...ids])] : s.marcados.filter((m) => !ids.includes(m)) })),
    limparMarcados: () => set({ marcados: [] }),
    aprovarLote: (ids) => {
      const { decisoes } = get()
      const novos = ids.filter((id) => !decisoes[id] && (ORIGEM_DADOS !== "api" || PACIENTE_POR_ID[id]?.inbox))
      if (novos.length === 0) {
        toast.info("Nada a aprovar: todos já foram revisados")
        return
      }
      if (ORIGEM_DADOS === "api") {
        const LIMITE = 40
        const lote = novos.slice(0, LIMITE)
        set({ enviando: true, marcados: [] })
        void (async () => {
          let feitas = 0
          try {
            for (const id of lote) {
              await decidir({ solicitacao_id: id, regulador_id: reguladorAtual(), acao: "aprovar" })
              feitas++
            }
          } catch (e) {
            toast.error("Lote interrompido", { description: mensagemErro(e) })
          }
          await get().recarregar()
          set({ enviando: false })
          toast.success(`${feitas} solicitações aprovadas na API`, {
            description: novos.length > LIMITE ? `Limite de ${LIMITE} por lote: restam ${novos.length - feitas}` : "Fila republicada",
          })
        })()
        return
      }
      set((s) => {
        const copia = { ...s.decisoes }
        novos.forEach((id) => {
          copia[id] = { status: "aprovado", classeFinal: PACIENTE_POR_ID[id].classe }
        })
        return { decisoes: copia, marcados: [] }
      })
      toast.success(`${novos.length} solicitações aprovadas`, {
        description: "A classe sugerida foi confirmada em lote",
        action: {
          label: "Desfazer",
          onClick: () =>
            set((s) => {
              const copia = { ...s.decisoes }
              novos.forEach((id) => delete copia[id])
              return { decisoes: copia }
            }),
        },
      })
    },
    mover: (direcao) => {
      const { filtros, decisoes, selecionadoId } = get()
      const lista = aplicarFiltros(PACIENTES, filtros, decisoes)
      if (lista.length === 0) return
      const idx = lista.findIndex((p) => p.id === selecionadoId)
      const novo = idx === -1 ? (direcao === 1 ? 0 : lista.length - 1) : Math.min(lista.length - 1, Math.max(0, idx + direcao))
      set({ selecionadoId: lista[novo].id, expandidoId: lista[novo].id, rejeitando: false })
    },
    irParaPosicao: (posicao) => {
      const alvo = PACIENTES.find((p) => p.posicao === posicao)
      if (!alvo) return false
      const { filtros, decisoes } = get()
      if (!aplicarFiltros(PACIENTES, filtros, decisoes).some((p) => p.id === alvo.id)) set({ filtros: FILTROS_VAZIOS })
      set({ pagina: "fila", selecionadoId: alvo.id, expandidoId: alvo.id, rejeitando: false })
      return true
    },
    aprovar: (id) => {
      const p = PACIENTE_POR_ID[id]
      if (ORIGEM_DADOS === "api") {
        // A API só aprova o que está no inbox (409 SEM_PROPOSTA, D-94); fora dele, Rejeitar define a classe.
        if (!p.inbox) {
          toast.info("Sem proposta para aprovar", { description: "A classe sugerida já é a classe em vigor" })
          return
        }
        void enviarDecisao(id, { acao: "aprovar" }, `${id} aprovado · classe ${p.classe}`)
        return
      }
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "aprovado", classeFinal: p.classe } } }))
      toast.success(`${id} aprovado`, {
        description: `${p.iniciais} · classe ${p.classe} · posição ${p.posicao}`,
        action: { label: "Desfazer", onClick: () => desfazerERetornar(id) },
      })
      avancar(id)
    },
    editar: (id, classe, motivoCodificado, motivo) => {
      const p = PACIENTE_POR_ID[id]
      if (ORIGEM_DADOS === "api") {
        void enviarDecisao(id, { acao: "editar", classe, motivo_codificado: motivoCodificado, justificativa: motivo }, `${id}: classe definida como ${classe}`)
        return
      }
      set((s) => ({ decisoes: { ...s.decisoes, [id]: { status: "editado", classeFinal: classe, motivoCodificado, motivo } } }))
      toast.info(`${id}: classe editada para ${classe}`, {
        description: `${p.iniciais} · sugerida ${p.classe}`,
        action: { label: "Desfazer", onClick: () => desfazerERetornar(id) },
      })
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
    abrirFicha: (id) => set({ pagina: "pacientes", fichaId: id, selecionadoId: id, rejeitando: false }),
    fecharFicha: () => set({ fichaId: null }),
  }
})
