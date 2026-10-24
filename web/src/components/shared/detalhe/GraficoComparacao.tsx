import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { Paciente } from "@/data/tipos"
import { corClasse } from "@/lib/cores"
import { medianasDaClasse } from "@/lib/stats"
import { CartaoGrafico } from "./Cartao"

type Linha = { metrica: string; paciente: number; mediana: number; pPct: number; mPct: number }

function Dica({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload: Linha }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border bg-popover p-2 text-xs shadow-md">
      <div className="font-semibold">{d.metrica}</div>
      <div className="tabular-nums">Paciente: <b>{d.paciente}</b></div>
      <div className="tabular-nums text-muted-foreground">Mediana da classe: {d.mediana}</div>
    </div>
  )
}

export function GraficoComparacao({ p }: { p: Paciente }) {
  const { dados, n } = useMemo(() => {
    const m = medianasDaClasse(p.classe)
    const linhas = [
      { metrica: "Dias em fila", paciente: p.dias_em_fila, mediana: Math.round(m.dias) },
      { metrica: "Dor (EVA)", paciente: p.intensidade_dor_eva, mediana: Math.round(m.dor * 10) / 10 },
      { metrica: "Idade", paciente: p.idade, mediana: Math.round(m.idade) },
      { metrica: "Nº de sinais", paciente: p.sinais.length, mediana: Math.round(m.sinais * 10) / 10 },
    ].map((l) => {
      const maior = Math.max(l.paciente, l.mediana, 1)
      return { ...l, pPct: (l.paciente / maior) * 100, mPct: (l.mediana / maior) * 100 }
    })
    return { dados: linhas, n: m.n }
  }, [p])

  return (
    <CartaoGrafico titulo="Comparação com a classe" descricao={`Paciente vs mediana dos ${n} casos da classe ${p.classe} (barras normalizadas por métrica)`}>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados} layout="vertical" margin={{ top: 0, right: 34, bottom: 0, left: 0 }} barGap={2}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis type="category" dataKey="metrica" width={80} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="none" />
            <Tooltip content={<Dica />} cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
            <Bar name="Paciente" dataKey="pPct" fill={corClasse(p.classe)} radius={4} barSize={12} isAnimationActive animationDuration={900} />
            <Bar name="Mediana da classe" dataKey="mPct" fill="var(--muted-foreground)" fillOpacity={0.45} radius={4} barSize={12} isAnimationActive animationDuration={900} animationBegin={150} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <dl className="mt-1 grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
        {dados.map((d) => (
          <div key={d.metrica} className="flex justify-between tabular-nums">
            <dt>{d.metrica}</dt>
            <dd>
              <b className="text-foreground">{d.paciente}</b> / {d.mediana}
            </dd>
          </div>
        ))}
      </dl>
    </CartaoGrafico>
  )
}
