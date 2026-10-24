import type { Paciente, Prioridade } from "@/data/tipos"
import { formatarPct } from "@/components/shared/Basicos"

const MANUAL: Record<Prioridade, string> = { alta: "alta", media: "média", baixa: "baixa" }
const CLASSE_DA_MANUAL: Record<Prioridade, string[]> = { alta: ["A1", "A2"], media: ["B"], baixa: ["C", "D"] }

/** Resumo em uma linha: tempo de fila, prazo, posição e classe. */
export function Resumo({ p }: { p: Paciente }) {
  const largura = Math.max(0, Math.min(100, p.pct))
  const difere = p.prioridade_atual && !CLASSE_DA_MANUAL[p.prioridade_atual].includes(p.classe)
  return (
    <section aria-label="Resumo" className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm sm:grid-cols-4">
      <div>
        <div className="font-semibold tabular-nums">{p.dias_em_fila} dias</div>
        <div className="text-xs text-muted-foreground">em fila</div>
      </div>
      <div>
        <div className="font-semibold tabular-nums">{formatarPct(p.pct)}</div>
        <div className="text-xs text-muted-foreground">do prazo consumido</div>
        <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-muted" aria-hidden>
          <div className="h-full bg-foreground/60" style={{ width: `${largura}%` }} />
        </div>
      </div>
      <div>
        <div className="font-semibold tabular-nums">#{p.posicao}</div>
        <div className="text-xs text-muted-foreground">posição na fila</div>
      </div>
      <div>
        <div className="font-semibold">Classe {p.classe}</div>
        <div className="text-xs text-muted-foreground">{difere && p.prioridade_atual ? `prioridade manual: ${MANUAL[p.prioridade_atual]}` : "classe de prioridade"}</div>
      </div>
    </section>
  )
}
