import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Crown } from "lucide-react"
import type { Paciente } from "@/data/tipos"
import { CLASSES, COR_ORIGEM, ROTULO_ORIGEM, corClasse, indiceClasse } from "@/lib/cores"
import { CartaoGrafico } from "./Cartao"

type Passo = {
  nome: string
  curto: string
  tipo: "base" | "delta" | "final"
  inicio: number
  fim: number
  piso: number
  altura: number
  delta: number
  origem?: string
  detalhe?: string
  cor: string
  ouro: boolean
}

const nivel = (idx: number) => 4 - idx

function Rotulo({ x, y, payload }: { x?: number; y?: number; payload?: { value: string } }) {
  const linhas = (payload?.value ?? "").split(" ").reduce<string[]>((acc, palavra) => {
    const ultima = acc[acc.length - 1]
    if (ultima && (ultima + " " + palavra).length <= 13) acc[acc.length - 1] = `${ultima} ${palavra}`
    else acc.push(palavra)
    return acc
  }, [])
  return (
    <g transform={`translate(${x},${y})`}>
      {linhas.slice(0, 3).map((l, i) => (
        <text key={i} x={0} y={0} dy={12 + i * 11} textAnchor="middle" fontSize={10} fill="var(--muted-foreground)">
          {l}
        </text>
      ))}
    </g>
  )
}

function Dica({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload: Passo }> }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="max-w-64 rounded-md border bg-popover p-2 text-xs shadow-md">
      <div className="font-semibold">{d.nome}</div>
      {d.tipo === "delta" && (
        <div className="mt-0.5 flex items-center gap-1.5">
          <span className="font-bold tabular-nums">{d.delta > 0 ? `+${d.delta}` : d.delta} {Math.abs(d.delta) === 1 ? "degrau" : "degraus"}</span>
          <span className="text-muted-foreground">· {ROTULO_ORIGEM[d.origem ?? ""]}</span>
        </div>
      )}
      {d.detalhe && <div className="mt-1 text-muted-foreground">{d.detalhe}</div>}
    </div>
  )
}

type FormaProps = { x?: number; y?: number; width?: number; height?: number; payload?: Passo; index?: number }

function Forma({ x = 0, y = 0, width = 0, height = 0, payload, index = 0 }: FormaProps) {
  if (!payload) return <g />
  const sobe = payload.delta >= 0
  const h = Math.max(height, payload.tipo === "delta" ? 3 : 0)
  const yAjustado = payload.tipo === "delta" && height < 3 ? y - 1.5 : y
  return (
    <g>
      <rect
        x={x}
        y={yAjustado}
        width={width}
        height={h}
        rx={3}
        fill={payload.cor}
        fillOpacity={payload.tipo === "delta" ? 0.9 : 0.8}
        stroke={payload.ouro ? "var(--ouro)" : "none"}
        strokeWidth={payload.ouro ? 2 : 0}
        className={payload.ouro ? "fx-glow" : undefined}
        style={{
          transformBox: "fill-box",
          transformOrigin: sobe ? "center bottom" : "center top",
          animation: `fx-grow-y 0.6s cubic-bezier(0.2,0.7,0.2,1) ${index * 0.16}s both`,
        }}
      />
      {payload.tipo === "delta" && (
        <text x={x + width / 2} y={yAjustado - 4} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--foreground)" className="fx-pop" style={{ animationDelay: `${index * 0.16 + 0.5}s` }}>
          {payload.delta > 0 ? `+${payload.delta}` : payload.delta}
        </text>
      )}
      {payload.tipo !== "delta" && (
        <text x={x + width / 2} y={yAjustado + h / 2 + 4} textAnchor="middle" fontSize={13} fontWeight={800} fill="var(--foreground)" className="fx-pop" style={{ animationDelay: `${index * 0.16 + 0.5}s` }}>
          {payload.nome.match(/\((\w+)\)/)?.[1]}
        </text>
      )}
    </g>
  )
}

export function GraficoCascata({ p }: { p: Paciente }) {
  const passos = useMemo<Passo[]>(() => {
    const baseIdx = indiceClasse(p.parametros_ia.classe_base_cid)
    const lista: Passo[] = [
      { nome: `Base do CID (${p.parametros_ia.classe_base_cid})`, curto: "Base CID", tipo: "base", inicio: 0, fim: nivel(baseIdx), piso: 0, altura: nivel(baseIdx), delta: 0, detalhe: `${p.cid} define a classe de partida`, cor: corClasse(p.parametros_ia.classe_base_cid), ouro: false },
    ]
    let atual = nivel(baseIdx)
    p.parametros_ia.contribuicoes.forEach((c) => {
      const fim = atual + c.delta_degraus
      lista.push({
        nome: c.fator,
        curto: ROTULO_ORIGEM[c.origem],
        tipo: "delta",
        inicio: atual,
        fim,
        piso: Math.min(atual, fim),
        altura: Math.abs(fim - atual),
        delta: c.delta_degraus,
        origem: c.origem,
        detalhe: c.detalhe,
        cor: COR_ORIGEM[c.origem],
        ouro: c.origem === "regra_ouro" && c.delta_degraus > 0,
      })
      atual = fim
    })
    lista.push({ nome: `Classe final (${p.classe})`, curto: "Final", tipo: "final", inicio: 0, fim: atual, piso: 0, altura: atual, delta: 0, detalhe: "Decisão das regras sobre a proposta do LLM", cor: corClasse(p.classe), ouro: false })
    return lista
  }, [p])

  const temOuro = passos.some((s) => s.ouro)

  return (
    <CartaoGrafico titulo="Como a IA chegou à classe" descricao="Cascata: classe base do CID → contribuições (degraus) → classe final">
      <div className="h-64" role="img" aria-label={`Da classe base ${p.parametros_ia.classe_base_cid} até ${p.classe}`}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={passos} margin={{ top: 16, right: 8, bottom: 6, left: -14 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="curto" interval={0} height={36} tick={<Rotulo />} stroke="var(--border)" />
            <YAxis domain={[0, 4]} ticks={[0, 1, 2, 3, 4]} tickFormatter={(v: number) => CLASSES[4 - v]} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <Tooltip content={<Dica />} cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
            <Bar dataKey="piso" stackId="a" fill="transparent" isAnimationActive={false} />
            <Bar dataKey="altura" stackId="a" shape={<Forma />} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        {Object.entries(ROTULO_ORIGEM).map(([k, v]) => (
          <span key={k} className="inline-flex items-center gap-1">
            <span className="size-2.5 rounded-sm" style={{ background: COR_ORIGEM[k] }} aria-hidden />
            {v}
          </span>
        ))}
        {temOuro && (
          <span className="fx-pop inline-flex items-center gap-1 font-semibold" style={{ color: "var(--ouro)" }}>
            <Crown className="size-3" aria-hidden /> regra de ouro acionada
          </span>
        )}
      </div>
    </CartaoGrafico>
  )
}
