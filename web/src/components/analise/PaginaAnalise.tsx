import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { AlertTriangle, CheckCheck, Ribbon, TimerOff, type LucideIcon } from "lucide-react"
import { ESPECIALIDADES, FANTASMAS, PACIENTES } from "@/data/fila"
import { CLASSES, corClasse, corPrazo } from "@/lib/cores"
import { usarContagem } from "@/lib/motion"
import { cn } from "@/lib/utils"
import { ClasseBadge, ConfiancaSelo } from "@/components/shared/Basicos"
import { CartaoGrafico } from "@/components/shared/detalhe/Cartao"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useStore } from "@/store/useStore"

const todos = () => [
  ...FANTASMAS.map((f) => ({ classe: f.classe, antiga: f.classe_antiga, pct: f.prazo_consumido_pct })),
  ...PACIENTES.map((p) => ({ classe: p.classe, antiga: p.classe_antiga, pct: p.prazo_consumido_pct })),
]

function Resumo({ icone: Icone, rotulo, valor, sufixo = "", cor, detalhe, indice }: { icone: LucideIcon; rotulo: string; valor: number; sufixo?: string; cor: string; detalhe: string; indice: number }) {
  const animado = usarContagem(valor, 900)
  return (
    <div className="fx-fade-up flex items-start gap-3 rounded-xl bg-muted/40 p-3" style={{ animationDelay: `${indice * 80}ms` }}>
      <Icone className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0">
        <div className="text-xl leading-none font-semibold tabular-nums" style={{ color: cor }}>
          {Math.round(animado)}
          {sufixo}
        </div>
        <div className="mt-1 text-xs font-medium">{rotulo}</div>
        <div className="truncate text-[11px] text-muted-foreground">{detalhe}</div>
      </div>
    </div>
  )
}

export default function PaginaAnalise() {
  const TODOS = todos()
  const decisoes = useStore((s) => s.decisoes)
  const abrirNaFila = useStore((s) => s.abrirNaFila)

  const dados = useMemo(() => {
    const porClasse = CLASSES.map((c) => ({
      classe: c,
      antes: TODOS.filter((t) => t.antiga === c).length,
      depois: TODOS.filter((t) => t.classe === c).length,
    }))
    const bins = Array.from({ length: 11 }, (_, i) => ({
      faixa: i === 10 ? ">100" : `${i * 10}–${i * 10 + 9}`,
      n: TODOS.filter((t) => (i === 10 ? t.pct > 100 : t.pct >= i * 10 && t.pct < i * 10 + 10 && t.pct <= 100)).length,
      cor: corPrazo(i === 10 ? 110 : i * 10 + 5),
    }))
    const subiram = TODOS.filter((t) => CLASSES.indexOf(t.classe) < CLASSES.indexOf(t.antiga)).length
    const desceram = TODOS.filter((t) => CLASSES.indexOf(t.classe) > CLASSES.indexOf(t.antiga)).length
    const mantiveram = TODOS.length - subiram - desceram
    const porEsp = ESPECIALIDADES.map((e) => {
      const g = PACIENTES.filter((p) => p.especialidade === e)
      return {
        especialidade: e,
        subiu: g.filter((p) => p.posicao_nova < p.posicao_antiga).length,
        desceu: -g.filter((p) => p.posicao_nova > p.posicao_antiga).length,
      }
    })
    const matriz = ESPECIALIDADES.map((e) => ({
      especialidade: e,
      celulas: CLASSES.map((c) => PACIENTES.filter((p) => p.especialidade === e && p.classe === c).length),
    }))
    const maxCelula = Math.max(...matriz.flatMap((m) => m.celulas))
    const histConf = Array.from({ length: 6 }, (_, i) => ({
      faixa: i === 5 ? "90–100%" : `${40 + i * 10}–${49 + i * 10}%`,
      n: PACIENTES.filter((p) => (i === 5 ? p.confianca >= 0.9 : p.confianca >= 0.4 + i * 0.1 && p.confianca < 0.5 + i * 0.1)).length,
      baixa: 0.4 + i * 0.1 < 0.6,
    }))
    const menores = [...PACIENTES].sort((a, b) => a.confianca - b.confianca).slice(0, 10)
    return { porClasse, bins, subiram, desceram, mantiveram, porEsp, matriz, maxCelula, histConf, menores }
  }, [])

  const aprovados = Object.values(decisoes).filter((d) => d.status === "aprovado").length
  const rejeitados = Object.values(decisoes).filter((d) => d.status === "rejeitado").length
  const revisados = aprovados + rejeitados
  const oncCorrigidos = PACIENTES.filter((p) => p.cid.startsWith("C") && p.classe_antiga !== p.classe).length
  const vencidos = TODOS.filter((t) => t.pct > 100).length
  const divergencias = PACIENTES.filter((p) => p.divergencia).length

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-7xl space-y-4 p-4">
        <div className="grid grid-cols-1 gap-3 @lg:grid-cols-2 @4xl:grid-cols-4">
          <Resumo indice={0} icone={Ribbon} rotulo="Oncológicos corrigidos" valor={oncCorrigidos} cor="var(--cls-a2-fg)" detalhe="Classe elevada pela regra de ouro e pelo texto" />
          <Resumo indice={1} icone={TimerOff} rotulo="Vencidos (>100% do prazo)" valor={vencidos} cor="var(--prazo-vencido)" detalhe="Na fila inteira de 941 pacientes" />
          <Resumo indice={2} icone={AlertTriangle} rotulo="Divergências com a regulação" valor={divergencias} cor="var(--prazo-limite)" detalhe="IA discorda da prioridade humana" />
          <Resumo indice={3} icone={CheckCheck} rotulo="Aprovado / rejeitado" valor={revisados === 0 ? 0 : Math.round((aprovados / revisados) * 100)} sufixo="%" cor="var(--sobe)" detalhe={`${aprovados} aprovados · ${rejeitados} rejeitados · ${PACIENTES.length - revisados} pendentes`} />
        </div>

        <div className="grid gap-3 @3xl:grid-cols-2">
          <CartaoGrafico titulo="Contagem por classe: antes × depois" descricao="Fila inteira (941 pacientes)">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dados.porClasse} margin={{ top: 16, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="classe" tick={{ fontSize: 12, fill: "var(--foreground)", fontWeight: 600 }} stroke="var(--border)" />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} />
                  <Bar name="Antes (regulação)" dataKey="antes" fill="var(--muted-foreground)" fillOpacity={0.5} radius={[4, 4, 0, 0]} animationDuration={900} />
                  <Bar name="Depois (IA)" dataKey="depois" fill="var(--primary)" radius={[4, 4, 0, 0]} animationDuration={900} animationBegin={200}>
                    {dados.porClasse.map((d) => (
                      <Cell key={d.classe} fill={corClasse(d.classe)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CartaoGrafico>

          <CartaoGrafico titulo="Histograma do % do prazo consumido" descricao="Verde ideal · amarelo ótimo · laranja no limite · vermelho vencido">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dados.bins} margin={{ top: 16, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="faixa" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} stroke="var(--border)" interval={0} />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} formatter={(v) => [v, "Pacientes"]} />
                  <ReferenceLine x=">100" stroke="var(--prazo-vencido)" strokeDasharray="3 3" />
                  <Bar dataKey="n" radius={[4, 4, 0, 0]} animationDuration={1000}>
                    {dados.bins.map((b) => (
                      <Cell key={b.faixa} fill={b.cor} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CartaoGrafico>

          <CartaoGrafico titulo="Quantos subiram e desceram" descricao="Fila inteira, por mudança de classe">
            <div className="grid grid-cols-3 gap-2 py-2">
              {[
                { rotulo: "Subiram", valor: dados.subiram, cor: "var(--sobe)", sinal: "▲" },
                { rotulo: "Mantiveram", valor: dados.mantiveram, cor: "var(--muted-foreground)", sinal: "=" },
                { rotulo: "Desceram", valor: dados.desceram, cor: "var(--desce)", sinal: "▼" },
              ].map((b) => (
                <div key={b.rotulo} className="rounded-lg border p-2 text-center">
                  <div className="text-xl font-bold tabular-nums" style={{ color: b.cor }}>
                    {b.sinal} {b.valor}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{b.rotulo}</div>
                </div>
              ))}
            </div>
            <div className="mb-1 text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Por especialidade (casos detalhados, posição)</div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dados.porEsp} layout="vertical" stackOffset="sign" margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" tickFormatter={(v: number) => String(Math.abs(v))} />
                  <YAxis type="category" dataKey="especialidade" width={118} interval={0} tick={{ fontSize: 10.5, fill: "var(--foreground)" }} stroke="none" />
                  <Tooltip formatter={(v, nome) => [Math.abs(Number(v)), nome]} cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
                  <ReferenceLine x={0} stroke="var(--foreground)" />
                  <Bar name="Subiram" dataKey="subiu" stackId="s" fill="var(--sobe)" animationDuration={900} />
                  <Bar name="Desceram" dataKey="desceu" stackId="s" fill="var(--desce)" animationDuration={900} animationBegin={150} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CartaoGrafico>

          <CartaoGrafico titulo="Mapa de calor: especialidade × classe" descricao="Casos detalhados · número em cada célula">
            <div className="overflow-x-auto">
              <table className="w-full border-separate border-spacing-1 text-xs">
                <thead>
                  <tr>
                    <th />
                    {CLASSES.map((c) => (
                      <th key={c} className="pb-1">
                        <ClasseBadge classe={c} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dados.matriz.map((linha, li) => (
                    <tr key={linha.especialidade}>
                      <th className="pr-2 text-left font-medium whitespace-nowrap">{linha.especialidade}</th>
                      {linha.celulas.map((n, ci) => (
                        <td
                          key={ci}
                          className={cn("fx-pop h-8 rounded text-center font-semibold tabular-nums", n === 0 && "text-muted-foreground/60")}
                          style={{
                            animationDelay: `${(li * 5 + ci) * 25}ms`,
                            background: n === 0 ? "var(--muted)" : `color-mix(in oklab, ${corClasse(CLASSES[ci])} ${Math.round(20 + (n / dados.maxCelula) * 65)}%, transparent)`,
                          }}
                          title={`${linha.especialidade} · ${CLASSES[ci]}: ${n}`}
                        >
                          {n}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CartaoGrafico>

          <CartaoGrafico titulo="Histograma de confiança" descricao="Abaixo de 60% pede revisão humana">
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dados.histConf} margin={{ top: 16, right: 8, bottom: 0, left: -12 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="faixa" tick={{ fontSize: 10.5, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} formatter={(v) => [v, "Pacientes"]} />
                  <Bar dataKey="n" radius={[4, 4, 0, 0]} animationDuration={900}>
                    {dados.histConf.map((b) => (
                      <Cell key={b.faixa} fill={b.baixa ? "var(--desce)" : "var(--primary)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CartaoGrafico>

          <CartaoGrafico titulo="10 casos de menor confiança" descricao="Clique para abrir o paciente na fila">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pos.</TableHead>
                  <TableHead>Caso</TableHead>
                  <TableHead>Classe</TableHead>
                  <TableHead className="text-right">Confiança</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dados.menores.map((p, i) => (
                  <TableRow key={p.solicitacao_id} className="fx-fade-up cursor-pointer" style={{ animationDelay: `${i * 45}ms` }} onClick={() => abrirNaFila(p.solicitacao_id)}>
                    <TableCell className="tabular-nums">#{p.posicao_nova}</TableCell>
                    <TableCell>
                      <button type="button" className="text-left outline-none focus-visible:underline" onClick={() => abrirNaFila(p.solicitacao_id)}>
                        <div className="font-semibold tabular-nums">{p.solicitacao_id}</div>
                        <div className="max-w-52 truncate text-xs text-muted-foreground">{p.procedimento}</div>
                      </button>
                    </TableCell>
                    <TableCell>
                      <ClasseBadge classe={p.classe} />
                    </TableCell>
                    <TableCell className="text-right">
                      <ConfiancaSelo valor={p.confianca} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CartaoGrafico>
        </div>
      </div>
    </div>
  )
}
