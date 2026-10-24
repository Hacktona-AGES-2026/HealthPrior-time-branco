import type { Paciente, Prioridade } from "@/data/tipos"
import { addDias, diffDias, formatarData } from "@/lib/datas"
import { formatarPct } from "@/components/shared/Basicos"
import { classeEmVigor, propostaPendente } from "@/data/adaptador"

const MANUAL: Record<Prioridade, string> = { alta: "alta", media: "média", baixa: "baixa" }
const CLASSE_DA_MANUAL: Record<Prioridade, string[]> = { alta: ["A1", "A2"], media: ["B"], baixa: ["C", "D"] }

/** Resumo em uma linha: tempo de fila, prazo, posição e classe. */
export function Resumo({ p }: { p: Paciente }) {
  const largura = Math.max(0, Math.min(100, p.pct))
  const classe = classeEmVigor(p)
  const proposta = propostaPendente(p)
  const difere = p.prioridade_atual && !CLASSE_DA_MANUAL[p.prioridade_atual].includes(classe)
  const hoje = addDias(p.data_entrada, p.dias_em_fila)
  const rev = p.data_revisao_prioridade
  const antiga = rev ? diffDias(rev, hoje) > 365 : false
  const textoPrioridade = p.prioridade_atual
    ? `Prioridade da regulação: ${MANUAL[p.prioridade_atual]}, ${rev ? `revisada em ${formatarData(rev)}` : "sem data de revisão"}${antiga ? " (há mais de um ano)" : ""}`
    : "Prioridade da regulação: não definida"
  return (
    <section aria-label="Resumo" className="space-y-3 text-sm">
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
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
        <div className="font-semibold">Classe {classe}</div>
        <div className="text-xs text-muted-foreground">
          {proposta
            ? `proposta ${proposta} aguardando aprovação`
            : difere && p.prioridade_atual
              ? `prioridade manual: ${MANUAL[p.prioridade_atual]}`
              : "classe de prioridade"}
        </div>
      </div>
      </div>
      <p className="text-xs text-muted-foreground">{textoPrioridade}</p>
    </section>
  )
}
