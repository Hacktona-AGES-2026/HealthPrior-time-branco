import type { Paciente } from "@/data/tipos"
import type { Decisao } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { estiloColuna, useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"
import { AlertaRevisao, CamadaBadge, ClasseBadge, PrazoBar, SetaVariacao, SinalChips, StatusAprovacao } from "./Basicos"

export const etiquetas = (p: Paciente) => [...(p.oncologico ? ["oncológico"] : []), ...p.motivos, ...p.sintomas]

export function LinhaResumo({ paciente: p, decisao, selecionado = false, comMarcacao = false }: { paciente: Paciente; decisao?: Decisao; selecionado?: boolean; comMarcacao?: boolean }) {
  const delta = p.posicao_atual - p.posicao
  const l = useColunas((c) => c.larguras)
  const o = useColunas((c) => c.ocultas)
  const marcado = useStore((s) => s.marcados.includes(p.id))
  const alternarMarcado = useStore((s) => s.alternarMarcado)
  return (
    <>
      {selecionado && <span key={p.id} className="fx-row-sweep pointer-events-none absolute inset-0" aria-hidden />}
      {selecionado && delta !== 0 && <span className={cn("pointer-events-none absolute inset-y-0 left-0 w-28", delta > 0 ? "fx-row-wave-up" : "fx-row-wave-down")} aria-hidden />}
      {decisao && <span key={decisao.status} className={cn("fx-flash-decisao pointer-events-none absolute inset-0", decisao.status === "aprovado" ? "[--flash:var(--sobe)]" : "[--flash:var(--cls-c)]")} aria-hidden />}
      {comMarcacao && (
        <input
          type="checkbox"
          checked={marcado}
          onChange={() => alternarMarcado(p.id)}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Selecionar ${p.id}`}
          className="relative size-3.5 shrink-0 cursor-pointer accent-[var(--primary)]"
        />
      )}
      <div className="relative shrink-0 font-bold tabular-nums" style={estiloColuna("pos", l, o)}>
        #{p.posicao}
      </div>
      <div className="relative flex shrink-0 items-center gap-1.5" style={estiloColuna("antiga", l, o)}>
        <span className="w-8 text-xs text-muted-foreground tabular-nums">{p.posicao_atual}</span>
        <SetaVariacao antiga={p.posicao_atual} nova={p.posicao} />
      </div>
      <div className="relative flex shrink-0 items-center gap-1" style={estiloColuna("classe", l, o)}>
        <ClasseBadge classe={p.classe} />
        {p.prioridade_atual && <span className="truncate text-[10px] text-muted-foreground">{p.prioridade_atual === "media" ? "méd" : p.prioridade_atual}</span>}
      </div>
      <div className="relative shrink-0" style={estiloColuna("camada", l, o)}>
        <CamadaBadge camada={p.camada} />
      </div>
      <div className="relative shrink-0" style={estiloColuna("prazo", l, o)}>
        <PrazoBar pct={p.pct} />
      </div>
      <div className="relative" style={estiloColuna("sinais", l, o)}>
        <SinalChips sinais={etiquetas(p)} />
      </div>
      <div className="relative truncate text-xs text-muted-foreground" style={estiloColuna("justificativa", l, o)} title={p.justificativa}>
        {p.justificativa}
      </div>
      <div className="relative shrink-0" style={estiloColuna("alerta", l, o)}>
        <AlertaRevisao paciente={p} />
      </div>
      <div className="relative shrink-0" style={estiloColuna("status", l, o)}>
        <StatusAprovacao decisao={decisao} />
      </div>
    </>
  )
}
