import { useMemo } from "react"
import { CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { Paciente } from "@/data/tipos"
import { PRAZO_MAX } from "@/lib/cores"
import { addDias, diffDias, formatarData } from "@/lib/datas"
import { ROTULO_EVENTO_TIPO } from "./IconesEvento"

type Ponto = { x: number; pct: number; rotulo?: string; piora?: boolean }

const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
const PIORA = ["pronto_socorro", "internacao"]
const COR_PIORA = "var(--prazo-vencido)"
const COR_OUTRO = "var(--primary)"
const TICK = { fontSize: 12, fill: "var(--muted-foreground)" }

function Dica({ active, payload, entrada }: { active?: boolean; payload?: ReadonlyArray<{ payload: Ponto }>; entrada: string }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  const data = formatarData(addDias(entrada, d.x))
  return (
    <div className="rounded-md border bg-popover p-2 text-xs text-popover-foreground shadow-md">
      <div className="font-semibold tabular-nums">{d.rotulo ? `${data} — ${d.rotulo}` : data}</div>
      <div className="tabular-nums text-muted-foreground">{Math.round(d.pct).toLocaleString("pt-BR")}% do prazo</div>
    </div>
  )
}

export function GraficoEspera({ p }: { p: Paciente }) {
  const prazo = PRAZO_MAX[p.classe]
  const dias = p.dias_em_fila

  const { dados, temEventos, maxY, ticksY } = useMemo(() => {
    const eventos: Ponto[] = p.eventos
      .filter((e) => !e.historico)
      .map((e) => ({ x: diffDias(p.data_entrada, e.data), tipo: e.tipo }))
      .filter((e) => e.x >= 0 && e.x <= dias)
      .map((e) => ({ x: e.x, pct: (e.x / prazo) * 100, rotulo: ROTULO_EVENTO_TIPO[e.tipo], piora: PIORA.includes(e.tipo) }))
    const base: Ponto[] = [0, dias].map((x) => ({ x, pct: (x / prazo) * 100 }))
    const dados = [...base, ...eventos].sort((a, b) => a.x - b.x)
    const pctFim = (dias / prazo) * 100
    const maxY = Math.max(110, Math.ceil(pctFim * 1.1))
    const ticksY = Array.from(new Set([0, 100, Math.round(pctFim)])).sort((a, b) => a - b)
    return { dados, temEventos: eventos.length > 0, maxY, ticksY }
  }, [p, prazo, dias])

  const pctAtual = Math.round((dias / prazo) * 100)

  if (!temEventos) {
    return <p className="text-sm text-muted-foreground">Sem eventos registrados na espera.</p>
  }

  const curto = dias <= 180
  const fmtX = (v: number) => {
    const iso = addDias(p.data_entrada, v)
    const [a, m, d] = iso.split("-")
    return curto ? `${d}/${m}` : `${MESES[Number(m) - 1]}/${a.slice(2)}`
  }

  return (
    <div>
      <div className="h-48 w-full sm:h-60" role="img" aria-label={`Espera de ${dias} dias; ${pctAtual}% do prazo consumido`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dados} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="x" type="number" domain={[0, dias]} tickCount={4} minTickGap={32} interval="preserveStartEnd" tickFormatter={fmtX} tick={TICK} stroke="var(--border)" />
            <YAxis domain={[0, maxY]} ticks={ticksY} interval={0} tickFormatter={(v: number) => `${v.toLocaleString("pt-BR")}%`} tick={TICK} stroke="var(--border)" width={44} />
            <ReferenceLine y={100} stroke="var(--muted-foreground)" strokeDasharray="4 4" label={{ value: "Prazo", position: "insideTopLeft", fontSize: 12, fill: "var(--muted-foreground)" }} />
            <Tooltip content={<Dica entrada={p.data_entrada} />} cursor={{ stroke: "var(--border)" }} isAnimationActive={false} />
            <Line
              dataKey="pct"
              type="linear"
              stroke="var(--primary)"
              strokeWidth={2.5}
              isAnimationActive={false}
              activeDot={false}
              dot={(props: { cx?: number; cy?: number; index?: number; payload?: Ponto }) => {
                const { cx, cy, payload, index } = props
                if (!payload?.rotulo || cx == null || cy == null) return <g key={`d-${index}`} />
                return <circle key={`d-${index}`} cx={cx} cy={cy} r={5} fill={payload.piora ? COR_PIORA : COR_OUTRO} stroke="var(--background)" strokeWidth={1.5} />
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">Pontos: eventos durante a espera</p>
    </div>
  )
}
