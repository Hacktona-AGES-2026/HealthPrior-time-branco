import type { Paciente } from "@/data/tipos"
import type { Decisao } from "@/lib/filtros"
import { estiloColuna, useColunas } from "@/store/colunas"
import { corPrazo } from "@/lib/cores"
import { AlertaRevisao, ClasseBadge, StatusAprovacao } from "./Basicos"

export const textoDias = (dias: number) => (dias === 1 ? "1 dia" : `${dias.toLocaleString("pt-BR")} dias`)

export function LinhaResumo({ paciente: p, decisao }: { paciente: Paciente; decisao?: Decisao; selecionado?: boolean }) {
  const l = useColunas((c) => c.larguras)
  const o = useColunas((c) => c.ocultas)
  const pendente = !decisao
  return (
    <>
      <div className="shrink-0 font-bold tabular-nums" style={estiloColuna("pos", l, o)}>
        #{p.posicao}
      </div>
      <div className="min-w-0" style={estiloColuna("paciente", l, o)}>
        <div className="flex items-center gap-2 text-sm">
          <span className="truncate font-medium">
            {p.iniciais}, {p.idade} a
          </span>
          {p.oncologico && <span className="shrink-0 text-xs font-semibold text-primary">Oncológico</span>}
        </div>
        <div className="truncate text-xs text-muted-foreground" title={p.procedimento}>
          {p.procedimento}
        </div>
      </div>
      <div className="shrink-0" style={estiloColuna("classe", l, o)}>
        <ClasseBadge classe={p.classe} />
      </div>
      <div className="min-w-0 shrink-0" style={estiloColuna("prazo", l, o)}>
        <span className="block h-1.5 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={Math.round(p.pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Prazo consumido" title={`${Math.round(p.pct)}% do prazo`}>
          <span className="block h-full rounded-full" style={{ width: `${Math.min(100, p.pct)}%`, background: corPrazo(p.pct) }} />
        </span>
        <div className="mt-1 text-xs text-muted-foreground tabular-nums">{textoDias(p.dias_em_fila)}</div>
      </div>
      <div className="flex shrink-0 items-center gap-1" style={estiloColuna("status", l, o)}>
        {pendente ? <span className="text-xs text-muted-foreground">A revisar</span> : <StatusAprovacao decisao={decisao} />}
        <AlertaRevisao paciente={p} />
      </div>
    </>
  )
}
