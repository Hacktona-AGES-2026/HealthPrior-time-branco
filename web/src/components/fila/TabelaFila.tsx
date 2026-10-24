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
import { AlcaColuna } from "@/components/shared/AlcaColuna"
import { estiloColuna, useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

export const usarTabela = () => {
  const filtros = useStore((s) => s.filtros)
  const decisoes = useStore((s) => s.decisoes)
  const [sorting, setSorting] = useState<SortingState>([{ id: "pos", desc: false }])
  const dados = useMemo(() => aplicarFiltros(PACIENTES, filtros, decisoes), [filtros, decisoes])

  const colunas = useMemo<ColumnDef<Paciente>[]>(
    () => [
      { id: "pos", header: "Nova", accessorFn: (p) => p.posicao_nova },
      { id: "antiga", header: "Antiga", accessorFn: (p) => p.posicao_antiga - p.posicao_nova },
      { id: "classe", header: "Classe", accessorFn: (p) => indiceClasse(p.classe) },
      { id: "prazo", header: "Prazo", accessorFn: (p) => p.prazo_consumido_pct },
      { id: "sinais", header: "Sinais", enableSorting: false, accessorFn: (p) => p.sinais.length },
      { id: "justificativa", header: "Justificativa", enableSorting: false, accessorFn: (p) => p.justificativa },
      { id: "alerta", header: "", enableSorting: false, accessorFn: (p) => Number(p.divergencia || p.confianca < 0.6) },
      { id: "status", header: "Status", accessorFn: (p) => statusDe(decisoes, p.solicitacao_id) },
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
  return (
    <div className="@container">
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground" role="row">
        {table.getHeaderGroups()[0].headers.map((h) => {
          const ordenado = h.column.getIsSorted()
          const podeOrdenar = h.column.getCanSort()
          return (
            <div key={h.id} className="relative" style={estiloColuna(h.column.id, larguras)} role="columnheader" aria-sort={ordenado === "asc" ? "ascending" : ordenado === "desc" ? "descending" : "none"}>
              {podeOrdenar ? (
                <button type="button" onClick={() => h.column.toggleSorting(ordenado === "asc")} className="inline-flex items-center gap-1 rounded px-0.5 uppercase hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring">
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {ordenado === "asc" ? <ArrowUp className="size-3" /> : ordenado === "desc" ? <ArrowDown className="size-3" /> : <ArrowUpDown className="size-3 opacity-50" />}
                </button>
              ) : (
                flexRender(h.column.columnDef.header, h.getContext())
              )}
              {h.column.id !== "alerta" && <AlcaColuna id={h.column.id} />}
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
}

const LinhaPaciente = memo(function LinhaPaciente({ paciente: p, selecionado, expandido, decisao, aoAlternar }: LinhaProps) {
  return (
    <div className="@container" role="row" aria-selected={selecionado} aria-expanded={expandido}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => aoAlternar(p.solicitacao_id)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            aoAlternar(p.solicitacao_id)
          }
        }}
        className={cn(
          "relative flex h-11 cursor-pointer items-center gap-2 overflow-hidden border-b border-border/50 px-3 text-sm outline-none transition-colors hover:bg-muted/40 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
          selecionado && "bg-primary/5 shadow-[inset_2px_0_0_var(--primary)]"
        )}
      >
        <LinhaResumo paciente={p} decisao={decisao} selecionado={selecionado} />
      </div>
      {expandido && (
        <div className="fx-expand border-b border-border/50 px-1 pt-2 pb-5" onClick={(e) => e.stopPropagation()}>
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
    if (listaRef.current) setMargem(listaRef.current.offsetTop)
  }, [alturaFixa, linhas.length])

  const virtualizador = useVirtualizer({
    count: linhas.length,
    getScrollElement: () => rolagemRef.current,
    estimateSize: (i) => (linhas[i]?.original.solicitacao_id === expandidoId ? 1400 : 44),
    overscan: 8,
    scrollMargin: margem,
    scrollPaddingStart: alturaFixa + 4,
    getItemKey: (i) => linhas[i]?.original.solicitacao_id ?? i,
  })

  const aoAlternar = useCallback((id: string) => alternarExpandido(id), [alternarExpandido])

  useEffect(() => {
    if (!expandidoId) return
    const idx = linhas.findIndex((l) => l.original.solicitacao_id === expandidoId)
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
      <div className="flex flex-col items-center gap-2 py-16 text-center text-sm text-muted-foreground fx-fade-up">
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
            <LinhaPaciente paciente={p} selecionado={selecionadoId === p.solicitacao_id} expandido={expandidoId === p.solicitacao_id} decisao={decisoes[p.solicitacao_id]} aoAlternar={aoAlternar} />
          </div>
        )
      })}
    </div>
  )
}
