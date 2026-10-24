import { ArrowDown, ArrowUp } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import type { Decisao } from "@/lib/filtros"
import { estiloColuna, useColunas } from "@/store/colunas"
import { AlertaRevisao, ClasseBadge, PrazoBar, StatusAprovacao } from "./Basicos"

export const etiquetas = (p: Paciente) => [...(p.oncologico ? ["oncológico"] : []), ...p.motivos, ...p.sintomas]

// Principal motivo clínico, em linguagem de consultório.
export const motivoClinico = (p: Paciente): string => {
  const todos = [...p.motivos, ...p.sintomas].map((m) => m.toLowerCase())
  const tem = (trecho: string) => todos.some((m) => m.includes(trecho))
  const dor = todos.map((m) => /dor eva (\d+)/.exec(m)).find(Boolean)
  const nota = dor ? Number(dor[1]) : null

  if (p.oncologico) return tem("neoplasia maligna") || tem("biópsia positiva") ? "Câncer confirmado" : "Suspeita de câncer"
  if (tem("sinal de alarme")) return "Sinal de alarme descrito no pedido"
  if (tem("evento de piora")) return "Piorou enquanto esperava"
  if (tem("biópsia positiva")) return "Biópsia positiva: conferir o diagnóstico"
  if (tem("limitação funcional grave")) return "Limitação grave nas atividades"
  if (nota !== null && nota >= 7) return `Dor forte (${nota}/10)`
  if (tem("limitação funcional moderada")) return "Limitação moderada nas atividades"
  if (nota !== null && nota >= 4) return `Dor moderada (${nota}/10)`
  if (nota !== null) return `Dor leve (${nota}/10)`
  if (tem("dor não informada")) return "Dor não informada"
  if (tem("nenhum risco")) return "Sem sinal de piora registrado"
  return p.motivos[0] ?? p.sintomas[0] ?? "Aguardando a vez na fila"
}

export const textoDias = (dias: number) => (dias === 1 ? "1 dia em fila" : `${dias.toLocaleString("pt-BR")} dias em fila`)

export function LinhaResumo({ paciente: p, decisao }: { paciente: Paciente; decisao?: Decisao; selecionado?: boolean }) {
  const delta = p.posicao_atual - p.posicao
  const l = useColunas((c) => c.larguras)
  const o = useColunas((c) => c.ocultas)
  const motivo = motivoClinico(p)
  const pendente = !decisao
  return (
    <>
      <div className="flex shrink-0 items-center gap-1 font-bold tabular-nums" style={estiloColuna("pos", l, o)}>
        #{p.posicao}
        {delta !== 0 && (
          <span className="text-muted-foreground" title={delta > 0 ? `Subiu ${delta} posições (era #${p.posicao_atual})` : `Desceu ${-delta} posições (era #${p.posicao_atual})`}>
            {delta > 0 ? <ArrowUp className="size-3" aria-label={`Subiu ${delta} posições`} /> : <ArrowDown className="size-3" aria-label={`Desceu ${-delta} posições`} />}
          </span>
        )}
      </div>
      <div className="min-w-0" style={estiloColuna("paciente", l, o)}>
        <div className="flex items-center gap-2 text-sm">
          <span className="truncate font-medium">
            {p.iniciais} · {p.idade} anos · {p.sexo}
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
        <PrazoBar pct={p.pct} />
        <div className="mt-0.5 text-xs text-muted-foreground tabular-nums">{textoDias(p.dias_em_fila)}</div>
      </div>
      <div className="truncate text-sm text-muted-foreground" style={estiloColuna("porque", l, o)} title={[motivo, ...p.motivos, ...p.sintomas].filter((m, i, a) => a.indexOf(m) === i).join(" · ")}>
        {motivo}
      </div>
      <div className="flex shrink-0 items-center gap-1" style={estiloColuna("status", l, o)}>
        {pendente ? <span className="text-xs text-muted-foreground">A revisar</span> : <StatusAprovacao decisao={decisao} />}
        <AlertaRevisao paciente={p} />
      </div>
    </>
  )
}
