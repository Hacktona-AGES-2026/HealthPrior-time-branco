import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { Paciente } from "@/data/tipos"
import { usarContagem } from "@/lib/motion"
import { CartaoGrafico } from "./Cartao"

const corConfianca = (v: number) => (v < 0.6 ? "var(--desce)" : v < 0.8 ? "var(--prazo-limite)" : "var(--sobe)")

function Medidor({ valor }: { valor: number }) {
  const animado = usarContagem(valor * 100, 1000)
  const cor = corConfianca(valor)
  const arco = "M 10 60 A 50 50 0 0 1 110 60"
  return (
    <svg viewBox="0 0 120 74" className="mx-auto w-44" role="img" aria-label={`Confiança geral ${Math.round(valor * 100)}%`}>
      <path d={arco} fill="none" stroke="var(--muted)" strokeWidth={11} strokeLinecap="round" />
      <path d={arco} pathLength={100} fill="none" stroke={cor} strokeWidth={11} strokeLinecap="round" strokeDasharray="100" style={{ strokeDashoffset: 100 - animado, transition: "stroke-dashoffset 0.05s linear" }} />
      <line x1={60} y1={60} x2={60} y2={20} stroke="var(--foreground)" strokeWidth={2} strokeLinecap="round" style={{ transformOrigin: "60px 60px", transform: `rotate(${-90 + animado * 1.8}deg)`, transition: "transform 0.05s linear" }} />
      <circle cx={60} cy={60} r={4} fill="var(--foreground)" />
      <text x={60} y={50} textAnchor="middle" fontSize={15} fontWeight={800} fill={cor} className="tabular-nums" dy={-2}>
        {Math.round(animado)}%
      </text>
      <text x={10} y={72} fontSize={7} fill="var(--muted-foreground)" textAnchor="middle">0</text>
      <text x={110} y={72} fontSize={7} fill="var(--muted-foreground)" textAnchor="middle">100</text>
    </svg>
  )
}

export function GraficoConfianca({ p }: { p: Paciente }) {
  const dados = p.parametros_ia.confianca_detalhe.map((c) => ({ ...c, pct: Math.round(c.valor * 100) }))
  return (
    <CartaoGrafico titulo="Confiança" descricao="Medidor geral e componentes que a compõem">
      <Medidor valor={p.confianca} />
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados} layout="vertical" margin={{ top: 0, right: 30, bottom: 0, left: 0 }}>
            <XAxis type="number" domain={[0, 100]} hide />
            <YAxis type="category" dataKey="componente" width={138} tick={{ fontSize: 10.5, fill: "var(--muted-foreground)" }} stroke="none" />
            <Tooltip formatter={(v) => [`${v}%`, "Confiança"]} cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
            <Bar dataKey="pct" radius={4} barSize={11} isAnimationActive animationDuration={900} fill="var(--primary)">
              <LabelList dataKey="pct" position="right" formatter={(v) => `${v}%`} fontSize={10.5} fill="var(--foreground)" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )
}
