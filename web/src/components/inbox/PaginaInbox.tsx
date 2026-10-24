import { Inbox } from "lucide-react"
import { PACIENTES } from "@/data/fila"
import { ClasseBadge } from "@/components/shared/Basicos"
import { Button } from "@/components/ui/button"
import { CLASSES } from "@/lib/cores"
import { useStore } from "@/store/useStore"

/** US-12: classe sugerida pelo SWALIS diferente da classe em vigor; só vale depois de um profissional decidir. */
export default function PaginaInbox() {
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const itens = PACIENTES.filter((p) => p.inbox).sort((a, b) => CLASSES.indexOf(a.classe) - CLASSES.indexOf(b.classe) || a.posicao - b.posicao)

  return (
    <div className="min-h-0 flex-1 overflow-y-auto p-4">
      <div className="mx-auto max-w-5xl space-y-3">
        <div className="flex items-center gap-2">
          <Inbox className="size-4 text-muted-foreground" aria-hidden />
          <h2 className="text-sm font-semibold">Inbox do regulador</h2>
          <span className="text-xs text-muted-foreground tabular-nums">{itens.length} propostas aguardando decisão</span>
        </div>
        {itens.length === 0 ? (
          <p className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">Nenhuma proposta pendente.</p>
        ) : (
          <ul className="divide-y rounded-lg border" aria-label="Propostas aguardando decisão">
            {itens.map((p) => (
              <li key={p.id} className="flex items-center gap-3 p-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                    <span className="font-semibold tabular-nums">{p.id}</span>
                    <span className="inline-flex items-center gap-1.5">
                      {p.classe_vigente ? <ClasseBadge classe={p.classe_vigente} /> : <span className="text-xs text-muted-foreground">sem classe</span>}
                      <span aria-hidden>→</span>
                      <ClasseBadge classe={p.classe} />
                    </span>
                    <span className="text-xs text-muted-foreground tabular-nums">posição {p.posicao}</span>
                  </div>
                  <p className="break-words text-sm">{p.procedimento}</p>
                  <p className="line-clamp-2 break-words text-xs text-muted-foreground">{p.inbox?.motivos[0] ?? "—"}</p>
                </div>
                <Button size="sm" variant="outline" className="h-9 shrink-0 sm:h-8" onClick={() => abrirNaFila(p.id)} aria-label={`Revisar ${p.id}`}>
                  Revisar
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
