import { memo, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type RefObject } from "react"
import { flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState, type Table } from "@tanstack/react-table"
import { useVirtualizer } from "@tanstack/react-virtual"
import { ArrowDown, ArrowUp, ArrowUpDown, SearchX } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { PACIENTES } from "@/data/fila"
import { indiceClasse } from "@/lib/cores"
import { aplicarFiltros, statusDe, type Decisao } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { LinhaResumo } from "@/components/shared/LinhaResumo"
import { PacienteDetalhe } from "@/components/shared/PacienteDetalhe"
import { estiloColuna, useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

export const usarTabela = () => {
  const filtros = useStore((s) => s.filtros)
  const decisoes = useStore((s) => s.decisoes)
  const [sorting, setSorting] = useState<SortingState>([{ id: "pos", desc: false }])
  const dados = useMemo(() => aplicarFiltros(PACIENTES, filtros, decisoes), [filtros, decisoes])

  const colunas = useMemo<ColumnDef<Paciente>[]>(
    () => [
      { id: "pos", header: "Posição", accessorFn: (p) => p.posicao },
      { id: "paciente", header: "Paciente", enableSorting: false, accessorFn: (p) => p.iniciais },
      { id: "classe", header: "Classe", accessorFn: (p) => indiceClasse(p.classe) },
      { id: "prazo", header: "Prazo", accessorFn: (p) => p.pct },
      { id: "porque", header: "Por que está na fila", enableSorting: false, accessorFn: (p) => p.motivos.length },
      { id: "status", header: "Situação", accessorFn: (p) => statusDe(decisoes, p.id) },
    ],
    [decisoes]
  )

  const table = useReactTable({
    data: dados,
    columns: colunas,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    enableSortingRemoval: false,
  })
  return { table, total: PACIENTES.length, visiveis: dados.length }
}

export function CabecalhoTabela({ table }: { table: Table<Paciente> }) {
  const larguras = useColunas((c) => c.larguras)
  const ocultas = useColunas((c) => c.ocultas)
  return (
    <div className="@container min-w-0">
      <div className="flex items-center gap-2 overflow-hidden border-b border-border px-3 py-1 text-xs font-medium text-muted-foreground" role="row">
        {table.getHeaderGroups()[0].headers.map((h) => {
          const ordenado = h.column.getIsSorted()
          const podeOrdenar = h.column.getCanSort()
          return (
            <div key={h.id} className="min-w-0" style={estiloColuna(h.column.id, larguras, ocultas)} role="columnheader" aria-sort={ordenado === "asc" ? "ascending" : ordenado === "desc" ? "descending" : "none"}>
              {podeOrdenar ? (
                <button type="button" onClick={() => h.column.toggleSorting(ordenado === "asc")} className="inline-flex min-h-9 items-center md:min-h-7 gap-1 rounded px-0.5 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {ordenado === "asc" ? <ArrowUp className="size-3" /> : ordenado === "desc" ? <ArrowDown className="size-3" /> : <ArrowUpDown className="size-3 opacity-50" />}
                </button>
              ) : (
                flexRender(h.column.columnDef.header, h.getContext())
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

type LinhaProps = {
  paciente: Paciente
  selecionado: boolean
  expandido: boolean
  decisao?: Decisao
  aoAlternar: (id: string) => void
  par: boolean
}

const LinhaPaciente = memo(function LinhaPaciente({ paciente: p, selecionado, expandido, decisao, aoAlternar, par }: LinhaProps) {
  return (
    <div className="@container" role="row" aria-selected={selecionado} aria-expanded={expandido}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => aoAlternar(p.id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            aoAlternar(p.id)
          }
        }}
        className={cn(
          "relative flex min-h-14 cursor-pointer items-center gap-2 overflow-hidden border-b border-border/50 px-3 py-1.5 text-sm outline-none hover:bg-muted/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
          par && "bg-muted/20",
          selecionado && "bg-primary/10 shadow-[inset_2px_0_0_var(--primary)] hover:bg-primary/10"
        )}
      >
        <LinhaResumo paciente={p} decisao={decisao} selecionado={selecionado} />
      </div>
      {expandido && (
        <div className="border-b border-border/50 px-1 pt-2 pb-5" onClick={(e) => e.stopPropagation()}>
          <PacienteDetalhe paciente={p} />
        </div>
      )}
    </div>
  )
})

type CorpoProps = {
  table: Table<Paciente>
  rolagemRef: RefObject<HTMLDivElement | null>
  alturaFixa: number
}

export function CorpoTabela({ table, rolagemRef, alturaFixa }: CorpoProps) {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const expandidoId = useStore((s) => s.expandidoId)
  const decisoes = useStore((s) => s.decisoes)
  const alternarExpandido = useStore((s) => s.alternarExpandido)
  const listaRef = useRef<HTMLDivElement>(null)
  const [margem, setMargem] = useState(0)
  const linhas = table.getRowModel().rows

  useLayoutEffect(() => {
    const medir = () => {
      if (listaRef.current) setMargem(listaRef.current.offsetTop)
    }
    medir()
    const conteudo = rolagemRef.current?.firstElementChild
    if (!conteudo) return
    const obs = new ResizeObserver(medir)
    obs.observe(conteudo)
    return () => obs.disconnect()
  }, [alturaFixa, linhas.length, rolagemRef])

  const virtualizador = useVirtualizer({
    count: linhas.length,
    getScrollElement: () => rolagemRef.current,
    estimateSize: (i) => (linhas[i]?.original.id === expandidoId ? 1400 : 56),
    overscan: 8,
    scrollMargin: margem,
    scrollPaddingStart: alturaFixa + 4,
    getItemKey: (i) => linhas[i]?.original.id ?? i,
  })

  const aoAlternar = useCallback((id: string) => alternarExpandido(id), [alternarExpandido])

  useEffect(() => {
    if (!expandidoId) return
    const idx = linhas.findIndex((l) => l.original.id === expandidoId)
    if (idx < 0) return
    const rolar = () => virtualizador.scrollToIndex(idx, { align: "start" })
    const t1 = setTimeout(rolar, 30)
    const t2 = setTimeout(rolar, 450)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [expandidoId])

  if (linhas.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 py-16 text-center text-sm text-muted-foreground">
        <SearchX className="size-8" aria-hidden />
        Nenhum caso corresponde aos filtros.
      </div>
    )
  }

  return (
    <div ref={listaRef} role="table" aria-rowcount={linhas.length} style={{ height: virtualizador.getTotalSize() - margem, position: "relative" }}>
      {virtualizador.getVirtualItems().map((item) => {
        const p = linhas[item.index].original
        return (
          <div
            key={item.key}
            data-index={item.index}
            ref={virtualizador.measureElement}
            style={{ position: "absolute", top: 0, left: 0, width: "100%", transform: `translateY(${item.start - margem}px)` }}
          >
            <LinhaPaciente paciente={p} selecionado={selecionadoId === p.id} par={item.index % 2 === 1} expandido={expandidoId === p.id} decisao={decisoes[p.id]} aoAlternar={aoAlternar} />
          </div>
        )
      })}
    </div>
  )
}
