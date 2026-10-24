import { useMemo } from "react"
import { CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { Classe, Paciente } from "@/data/tipos"
import { corClasse } from "@/lib/cores"
import { HOJE, diffDias, formatarData } from "@/lib/datas"
import { ClasseBadge } from "@/components/shared/Basicos"
import { CartaoGrafico } from "./Cartao"

type Ponto = { x: number; real?: number; proj?: number; classe: Classe; motivo: string; data: string; pct: number }

const ROTULO_EVENTO: Record<string, string> = { pronto_socorro: "PS", biopsia: "Biópsia", internacao: "Internação", consulta_reavaliacao: "Reavaliação" }

function Dica({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload: Ponto }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="max-w-60 rounded-md border bg-popover p-2 text-xs shadow-md">
      <div className="flex items-center justify-between gap-2">
        <span className="font-semibold tabular-nums">{formatarData(d.data)}</span>
        <ClasseBadge classe={d.classe} />
      </div>
      <div className="mt-1 font-semibold tabular-nums">{d.pct}% do prazo</div>
      <div className="mt-0.5 text-muted-foreground">{d.motivo}</div>
    </div>
  )
}

export function GraficoEvolucao({ p }: { p: Paciente }) {
  const { dados, segmentos, eventos, maxX, maxY } = useMemo(() => {
    const mapa = new Map<number, Ponto>()
    const ultimoReal = diffDias(p.data_entrada_fila, HOJE)
    p.evolucao.forEach((e) => {
      const x = diffDias(p.data_entrada_fila, e.data)
      const futuro = x > ultimoReal
      const anterior = mapa.get(x)
      mapa.set(x, {
        x,
        real: futuro ? undefined : e.prazo_consumido_pct,
        proj: futuro || x === ultimoReal ? e.prazo_consumido_pct : anterior?.proj,
        classe: e.classe,
        motivo: e.motivo,
        data: e.data,
        pct: e.prazo_consumido_pct,
      })
    })
    const lista = [...mapa.values()].sort((a, b) => a.x - b.x)
    const segs = lista.slice(0, -1).map((pt, i) => ({ x1: pt.x, x2: lista[i + 1].x, classe: pt.classe }))
    const ev = p.eventos
      .filter((e) => ROTULO_EVENTO[e.tipo])
      .map((e) => ({ x: diffDias(p.data_entrada_fila, e.data), rotulo: ROTULO_EVENTO[e.tipo], descricao: e.descricao }))
    return { dados: lista, segmentos: segs, eventos: ev, maxX: lista[lista.length - 1].x, maxY: Math.ceil(Math.max(110, ...lista.map((d) => d.pct + 8)) / 20) * 20 }
  }, [p])

  return (
    <CartaoGrafico titulo="Evolução no tempo" descricao="% do prazo consumido por dia de espera · fundo = classe vigente · linhas = eventos" className="@lg:col-span-2">
      <div className="h-64" role="img" aria-label={`Evolução do prazo consumido até ${p.prazo_consumido_pct}% em ${p.dias_em_fila} dias`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dados} margin={{ top: 18, right: 16, bottom: 4, left: -8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            {segmentos.map((s, i) => (
              <ReferenceArea key={i} x1={s.x1} x2={s.x2} fill={corClasse(s.classe)} fillOpacity={0.13} ifOverflow="extendDomain" />
            ))}
            <XAxis dataKey="x" type="number" domain={[0, maxX]} tickFormatter={(v: number) => `${v}d`} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <YAxis domain={[0, maxY]} ticks={Array.from({ length: maxY / 20 + 1 }, (_, i) => i * 20)} tickFormatter={(v: number) => `${v}%`} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <ReferenceLine y={100} stroke="var(--prazo-vencido)" strokeDasharray="5 4" label={{ value: "100% do prazo", position: "insideTopLeft", fontSize: 10, fill: "var(--prazo-vencido)" }} />
            {eventos.map((e, i) => (
              <ReferenceLine key={i} x={e.x} stroke="var(--foreground)" strokeOpacity={0.45} strokeDasharray="2 3" label={{ value: e.rotulo, position: "top", fontSize: 10, fill: "var(--foreground)" }} />
            ))}
            <Tooltip content={<Dica />} />
            <Line dataKey="proj" type="linear" stroke="var(--muted-foreground)" strokeDasharray="5 4" strokeWidth={2} dot={false} isAnimationActive animationDuration={1200} animationBegin={600} connectNulls />
            <Line
              dataKey="real"
              type="linear"
              stroke="var(--foreground)"
              strokeWidth={2.4}
              isAnimationActive
              animationDuration={1100}
              connectNulls
              dot={(props: { cx?: number; cy?: number; payload?: Ponto; index?: number }) => {
                const { cx, cy, payload, index } = props
                if (cx === undefined || cy === undefined || !payload || payload.real === undefined) return <g key={index} />
                return <circle key={index} cx={cx} cy={cy} r={4.5} fill={corClasse(payload.classe)} stroke="var(--background)" strokeWidth={1.5} />
              }}
              activeDot={{ r: 6 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )
}
