import { useMemo, useState } from "react"
import { ChevronDown, RefreshCw, TriangleAlert } from "lucide-react"
import { PACIENTES } from "@/data/fila"
import { Button } from "@/components/ui/button"
import { ClasseBadge } from "@/components/shared/Basicos"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

type Grupo = { alerta: string; ids: string[] }

const agrupar = (): Grupo[] => {
  const mapa = new Map<string, string[]>()
  PACIENTES.forEach((p) =>
    new Set(p.alertas.map((a) => (a.startsWith("HbA1c") ? "HbA1c acima de 8,5%" : a))).forEach((a) => mapa.set(a, [...(mapa.get(a) ?? []), p.id]))
  )
  return [...mapa.entries()].map(([alerta, ids]) => ({ alerta, ids })).sort((a, b) => b.ids.length - a.ids.length)
}

export function AlertasDeDados({ onTentar }: { onTentar: () => void }) {
  const grupos = useMemo(agrupar, [])
  const [aberto, setAberto] = useState<string | null>(grupos[0]?.alerta ?? null)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const setFiltros = useStore((s) => s.setFiltros)
  const ir = useStore((s) => s.ir)

  return (
    <section className="fx-fade-up space-y-3" aria-label="Alertas de dados derivados dos CSVs">
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-muted/50 p-3 text-sm" role="status">
        <TriangleAlert className="size-4 shrink-0 text-[var(--prazo-limite)]" aria-hidden />
        <span className="flex-1 text-muted-foreground">
          <b className="text-foreground">API fora do ar.</b> Enquanto isso, esta lista mostra os alertas de dados calculados dos CSVs (somente leitura): o que o pré-processamento marcaria para a equipe administrativa conferir.
        </span>
        <Button variant="outline" size="sm" onClick={onTentar}>
          <RefreshCw aria-hidden /> Tentar a API de novo
        </Button>
      </div>

      <ul className="space-y-2">
        {grupos.map((g, i) => {
          const ligado = aberto === g.alerta
          return (
            <li key={g.alerta} className="fx-fade-up rounded-xl bg-muted/40" style={{ animationDelay: `${i * 60}ms` }}>
              <button type="button" aria-expanded={ligado} onClick={() => setAberto(ligado ? null : g.alerta)} className="flex w-full items-center gap-3 rounded-xl p-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring">
                <span className="w-10 text-right text-lg font-semibold tabular-nums">{g.ids.length}</span>
                <span className="flex-1 text-sm font-medium">{g.alerta}</span>
                <ChevronDown className={cn("size-4 text-muted-foreground transition-transform", ligado && "rotate-180")} aria-hidden />
              </button>
              {ligado && (
                <div className="fx-expand border-t border-border/60 p-3">
                  <ul className="grid gap-1 @lg:grid-cols-2">
                    {g.ids.slice(0, 12).map((id) => {
                      const p = PACIENTES.find((x) => x.id === id)!
                      return (
                        <li key={id}>
                          <button type="button" onClick={() => abrirNaFila(id)} className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring">
                            <ClasseBadge classe={p.classe} />
                            <span className="font-medium tabular-nums">{id}</span>
                            <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">{p.procedimento}</span>
                            <span className="text-xs text-muted-foreground tabular-nums">#{p.posicao}</span>
                          </button>
                        </li>
                      )
                    })}
                  </ul>
                  <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                    {g.ids.length > 12 && <span>e mais {g.ids.length - 12}</span>}
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => {
                        setFiltros({ alertas: true })
                        ir("fila")
                      }}
                    >
                      Ver todos com alerta na fila
                    </Button>
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
