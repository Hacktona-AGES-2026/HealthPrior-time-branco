import { useMemo } from "react"
import { CartesianGrid, ComposedChart, Line, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { Paciente } from "@/data/tipos"
import { PRAZO_MAX, corClasse } from "@/lib/cores"
import { addDias, diffDias, formatarData } from "@/lib/datas"
import { CartaoGrafico } from "./Cartao"
import { EVENTO_GRAVE, ROTULO_EVENTO_TIPO } from "./IconesEvento"

type Ponto = { x: number; pct: number }

function Dica({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload: Ponto }> }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md border bg-popover p-2 text-xs shadow-md">
      <div className="font-semibold tabular-nums">{payload[0].payload.x} dias de espera</div>
      <div className="tabular-nums text-muted-foreground">{Math.round(payload[0].payload.pct).toLocaleString("pt-BR")}% do prazo</div>
    </div>
  )
}

export function GraficoEspera({ p }: { p: Paciente }) {
  const prazo = PRAZO_MAX[p.classe]
  const { dados, marcas, minX, maxY } = useMemo(() => {
    const pontos: Ponto[] = [0, p.dias_em_fila].map((x) => ({ x, pct: (x / prazo) * 100 }))
    const marcas = p.eventos
      .filter((e) => EVENTO_GRAVE.includes(e.tipo))
      .map((e) => ({ x: diffDias(p.data_entrada, e.data), rotulo: ROTULO_EVENTO_TIPO[e.tipo], historico: e.historico, id: e.id }))
    const minX = Math.min(0, ...marcas.map((m) => m.x - 5))
    return { dados: pontos, marcas, minX, maxY: Math.max(120, Math.ceil(p.pct * 1.08)) }
  }, [p, prazo])

  return (
    <CartaoGrafico titulo="Espera × prazo da classe" descricao={`Prazo de ${prazo} dias · ${p.dias_em_fila.toLocaleString("pt-BR")} dias desde ${formatarData(p.data_entrada)} · tracejadas: eventos graves (cinza: antes da entrada)`} className="@lg:col-span-2">
      <div className="h-48 sm:h-60" role="img" aria-label={`${Math.round(p.pct)}% do prazo consumido em ${p.dias_em_fila} dias`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={dados} margin={{ top: 18, right: 16, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <ReferenceArea y1={100} y2={maxY} fill="var(--prazo-vencido)" fillOpacity={0.07} />
            <ReferenceArea x1={Math.min(minX, 0)} x2={0} fill="var(--muted-foreground)" fillOpacity={0.08} />
            <XAxis dataKey="x" type="number" domain={[minX, p.dias_em_fila]} tickFormatter={(v: number) => `${v}d`} tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <YAxis domain={[0, maxY]} tickFormatter={(v: number) => `${Math.round(v).toLocaleString("pt-BR")}%`} tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" width={56} />
            <ReferenceLine y={100} stroke="var(--prazo-vencido)" strokeDasharray="5 4" label={{ value: `prazo (${prazo}d)`, position: "insideTopLeft", fontSize: 12, fill: "var(--prazo-vencido)" }} />
            {marcas.map((m) => (
              <ReferenceLine key={m.id} x={m.x} stroke={m.historico ? "var(--muted-foreground)" : "var(--foreground)"} strokeOpacity={0.5} strokeDasharray="2 3" label={{ value: m.rotulo, position: "top", fontSize: 12, fill: "var(--muted-foreground)" }} />
            ))}
            <Tooltip content={<Dica />} />
            <Line dataKey="pct" type="linear" stroke={corClasse(p.classe)} strokeWidth={3} isAnimationActive animationDuration={1100} dot={{ r: 4.5, fill: corClasse(p.classe), stroke: "var(--background)", strokeWidth: 1.5 }} activeDot={{ r: 6 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <span className="sr-only">{addDias(p.data_entrada, p.dias_em_fila)}</span>
    </CartaoGrafico>
  )
}
