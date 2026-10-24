import type { Paciente } from "@/data/tipos"
import type { Decisao } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { estiloColuna, useColunas } from "@/store/colunas"
import { AlertaRevisao, ClasseBadge, PrazoBar, SetaVariacao, SinalChips, StatusAprovacao } from "./Basicos"

export function LinhaResumo({ paciente: p, decisao, selecionado = false }: { paciente: Paciente; decisao?: Decisao; selecionado?: boolean }) {
  const delta = p.posicao_antiga - p.posicao_nova
  const l = useColunas((c) => c.larguras)
  return (
    <>
      {selecionado && <span key={p.solicitacao_id} className="fx-row-sweep pointer-events-none absolute inset-0" aria-hidden />}
      {selecionado && delta !== 0 && <span className={cn("pointer-events-none absolute inset-y-0 left-0 w-28", delta > 0 ? "fx-row-wave-up" : "fx-row-wave-down")} aria-hidden />}
      <div className="relative shrink-0 font-bold tabular-nums" style={estiloColuna("pos", l)}>#{p.posicao_nova}</div>
      <div className="relative flex shrink-0 items-center gap-1.5" style={estiloColuna("antiga", l)}>
        <span className="w-7 text-xs text-muted-foreground tabular-nums">{p.posicao_antiga}</span>
        <SetaVariacao antiga={p.posicao_antiga} nova={p.posicao_nova} />
      </div>
      <div className="relative flex shrink-0 items-center gap-1" style={estiloColuna("classe", l)}>
        <ClasseBadge classe={p.classe} />
        {p.classe !== p.classe_antiga && <span className="text-[10px] text-muted-foreground">de {p.classe_antiga}</span>}
      </div>
      <div className="relative shrink-0" style={estiloColuna("prazo", l)}>
        <PrazoBar pct={p.prazo_consumido_pct} />
      </div>
      <div className="relative" style={estiloColuna("sinais", l)}>
        <SinalChips sinais={p.sinais} />
      </div>
      <div className="relative truncate text-xs text-muted-foreground" style={estiloColuna("justificativa", l)} title={p.justificativa}>
        {p.justificativa}
      </div>
      <div className="relative shrink-0" style={estiloColuna("alerta", l)}>
        <AlertaRevisao paciente={p} />
      </div>
      <div className="relative shrink-0" style={estiloColuna("status", l)}>
        <StatusAprovacao decisao={decisao} />
      </div>
    </>
  )
}
