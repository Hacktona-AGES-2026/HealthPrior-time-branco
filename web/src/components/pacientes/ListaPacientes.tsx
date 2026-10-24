import { useMemo, useRef, useState } from "react"
import { classeEmVigor } from "@/data/adaptador"
import { useVirtualizer } from "@tanstack/react-virtual"
import { Search } from "lucide-react"
import { PACIENTES } from "@/data/fila"
import { ClasseBadge } from "@/components/shared/Basicos"
import { normalizar } from "@/lib/filtros"
import { useStore } from "@/store/useStore"

const ORDENADOS = [...PACIENTES].sort((a, b) => a.posicao - b.posicao)
const INDICE = ORDENADOS.map((p) => ({ p, alvo: normalizar([p.id, p.iniciais, p.procedimento, p.cid, p.cid_norm, p.municipio].join(" ")) }))

export function ListaPacientes() {
  const abrirFicha = useStore((s) => s.abrirFicha)
  const [consulta, setConsulta] = useState("")
  const rolagem = useRef<HTMLDivElement>(null)

  const lista = useMemo(() => {
    const termos = normalizar(consulta.trim()).split(/\s+/).filter(Boolean)
    return (termos.length === 0 ? INDICE : INDICE.filter((i) => termos.every((t) => i.alvo.includes(t)))).map((i) => i.p)
  }, [consulta])

  const virtualizador = useVirtualizer({
    count: lista.length,
    getScrollElement: () => rolagem.current,
    estimateSize: () => 56,
    overscan: 10,
    getItemKey: (i) => lista[i]?.id ?? i,
  })

  return (
    <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col px-3 pt-3 md:px-4 md:pt-4">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <input
          type="search"
          value={consulta}
          onChange={(e) => setConsulta(e.target.value)}
          placeholder="Buscar paciente"
          aria-label="Buscar paciente"
          className="h-10 w-full rounded-md border bg-background pr-3 pl-9 text-base outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </div>
      <p className="px-1 py-2 text-xs text-muted-foreground tabular-nums">{lista.length.toLocaleString("pt-BR")} pacientes</p>
      <div ref={rolagem} className="min-h-0 flex-1 overflow-y-auto">
        {lista.length === 0 ? (
          <p className="px-1 py-6 text-sm text-muted-foreground">Nenhum paciente encontrado.</p>
        ) : (
          <ul className="relative" style={{ height: virtualizador.getTotalSize() }}>
            {virtualizador.getVirtualItems().map((v) => {
              const p = lista[v.index]
              return (
                <li key={v.key} className="absolute inset-x-0 border-b border-border/50" style={{ height: v.size, transform: `translateY(${v.start}px)` }}>
                  <button
                    type="button"
                    onClick={() => abrirFicha(p.id)}
                    className="flex h-full w-full items-center gap-3 px-2 text-left outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm">
                        <span className="font-semibold">{p.iniciais}</span> <span className="text-muted-foreground">{p.idade} anos · {p.sexo}</span>
                      </span>
                      <span className="block truncate text-xs text-muted-foreground">{p.procedimento}</span>
                    </span>
                    <ClasseBadge classe={classeEmVigor(p)} />
                    <span className="hidden w-28 shrink-0 text-right text-xs text-muted-foreground tabular-nums sm:block">{p.dias_em_fila} dias em fila</span>
                    <span className="w-12 shrink-0 text-right text-xs font-medium tabular-nums sm:w-24"><span className="hidden sm:inline">Posição </span>#{p.posicao}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
