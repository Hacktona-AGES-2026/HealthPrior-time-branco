import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Crown, Hourglass, ShieldCheck, Sparkles, TrendingUp, UserRound, type LucideIcon } from "lucide-react"
import { FANTASMAS, PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import { CLASSES, DESCRICAO_CLASSE, FAIXAS_PRAZO, PRAZO_MAX, corClasse, corPrazo, rotuloPrazo } from "@/lib/cores"
import { cn } from "@/lib/utils"
import { ClasseBadge } from "@/components/shared/Basicos"
import { CartaoGrafico } from "@/components/shared/detalhe/Cartao"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useStore } from "@/store/useStore"

const EXEMPLOS = {
  A1: "Obstrução intestinal com risco de estrangulamento; isquemia aguda de membro",
  A2: "Câncer com prazo curto: biópsia positiva aguardando cirurgia",
  B: "Câncer de pele não melanoma; coxartrose com dor em repouso",
  C: "Cirurgias eletivas sintomáticas: hérnia redutível, varizes com dor",
  D: "Eletivas estáveis: catarata inicial, hérnia assintomática",
}

type Regra = { codigo: string; titulo: string; texto: string; icone: LucideIcon; ouro?: boolean; gatilho: (regras: string[]) => boolean }

const REGRAS: Regra[] = [
  { codigo: "R01", titulo: "Regra de ouro", texto: "Câncer nunca abaixo de B. Demais C* no mínimo A2 (C44, pele não melanoma, pode ser B).", icone: Crown, ouro: true, gatilho: (r) => r.some((x) => x.startsWith("R01")) },
  { codigo: "R02", titulo: "O LLM propõe, as regras decidem", texto: "A saída do modelo é uma sugestão. A classe final só vale depois de passar pelas regras determinísticas.", icone: Sparkles, gatilho: (r) => r.some((x) => x.startsWith("R02")) },
  { codigo: "R05", titulo: "Fragilidade só sobe", texto: "Idade avançada e ASA alto podem elevar a classe, nunca rebaixá-la.", icone: ShieldCheck, gatilho: (r) => r.some((x) => x.startsWith("R05")) },
  { codigo: "R06", titulo: "Idade só como modificador", texto: "A idade isolada não define classe: apenas modula outros sinais clínicos.", icone: UserRound, gatilho: (r) => r.some((x) => x.startsWith("R06")) },
]

export default function PaginaSwalis() {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const paciente = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined
  const regrasDoPaciente = paciente?.parametros_ia.regras_acionadas ?? []

  const porClasse = useMemo(() => {
    const todos = [...FANTASMAS.map((f) => ({ classe: f.classe, pct: f.prazo_consumido_pct })), ...PACIENTES.map((p) => ({ classe: p.classe, pct: p.prazo_consumido_pct }))]
    return CLASSES.map((c) => {
      const g = todos.filter((t) => t.classe === c)
      const vencidos = g.filter((t) => t.pct > 100).length
      return { classe: c, noPrazo: g.length - vencidos, vencidos }
    })
  }, [])

  const pct = paciente?.prazo_consumido_pct ?? 0

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-6xl space-y-4 p-4">
        <section className="fx-fade-up rounded-xl bg-muted/40 p-4">
          <h2 className="mb-2 flex items-center gap-2 text-base font-semibold">
            <Hourglass className="size-4" aria-hidden /> Como funciona o SWALIS
          </h2>
          <p className="text-sm leading-relaxed text-muted-foreground">
            Cada paciente recebe uma <b className="text-foreground">classe de urgência</b> com um prazo máximo de espera. O <b className="text-foreground">score é o % do prazo consumido</b>: dias de espera divididos pelo prazo da classe. Quando a urgência é reavaliada, o paciente muda de classe mas{" "}
            <b className="text-foreground">mantém o percentual já acumulado</b> (método cumulativo), de modo que quem subiu de classe não perde o tempo já esperado.
          </p>
        </section>

        <section className="fx-fade-up rounded-xl bg-muted/40" style={{ animationDelay: "80ms" }}>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-20">Classe</TableHead>
                <TableHead>Descrição</TableHead>
                <TableHead className="w-28">Prazo máximo</TableHead>
                <TableHead>Exemplos clínicos (mock)</TableHead>
                <TableHead className="w-24 text-right">Na fila</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {CLASSES.map((c, i) => {
                const atual = paciente?.classe === c
                const quantidade = porClasse[i].noPrazo + porClasse[i].vencidos
                return (
                  <TableRow key={c} className={cn("fx-fade-up transition-colors", atual && "bg-primary/10")} style={{ animationDelay: `${i * 70}ms` }}>
                    <TableCell>
                      <ClasseBadge classe={c} className={atual ? "fx-glow" : undefined} />
                    </TableCell>
                    <TableCell className="whitespace-normal text-sm">{DESCRICAO_CLASSE[c]}</TableCell>
                    <TableCell className="font-semibold tabular-nums">{PRAZO_MAX[c]} dias</TableCell>
                    <TableCell className="whitespace-normal text-xs text-muted-foreground">{EXEMPLOS[c]}</TableCell>
                    <TableCell className="text-right tabular-nums">{quantidade}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </section>

        <section className="fx-fade-up rounded-xl bg-muted/40 p-4" style={{ animationDelay: "120ms" }} aria-label="Faixas do percentual do prazo">
          <h3 className="mb-3 text-xs font-semibold tracking-wide text-muted-foreground uppercase">Faixas do % do prazo consumido</h3>
          <div className="relative pt-8 pb-1">
            <div className="flex h-5 overflow-hidden rounded-full">
              {[
                { ...FAIXAS_PRAZO[0], largura: 50 },
                { ...FAIXAS_PRAZO[1], largura: 25 },
                { ...FAIXAS_PRAZO[2], largura: 25 },
              ].map((f, i) => (
                <div key={f.rotulo} className="fx-grow-x" style={{ width: `${f.largura * 0.8}%`, background: f.cor, animationDelay: `${i * 160}ms` }} />
              ))}
              <div className="fx-grow-x flex-1" style={{ background: FAIXAS_PRAZO[3].cor, animationDelay: "480ms", backgroundImage: "repeating-linear-gradient(135deg, transparent 0 4px, rgb(255 255 255 / 0.4) 4px 6px)" }} />
            </div>
            <div className="relative mt-1 h-4 text-[11px] text-muted-foreground tabular-nums">
              {[0, 50, 75, 100].map((v) => (
                <span key={v} className="absolute -translate-x-1/2" style={{ left: `${v * 0.8}%` }}>
                  {v}%
                </span>
              ))}
              <span className="absolute" style={{ left: "88%" }}>
                &gt;100%
              </span>
            </div>
            {paciente && (
              <div key={paciente.solicitacao_id} className="fx-fade-up absolute top-0 -translate-x-1/2" style={{ left: `${pct <= 100 ? pct * 0.8 : 80 + Math.min(1, (pct - 100) / 40) * 20}%` }}>
                <div className="flex flex-col items-center">
                  <span className="rounded-full border bg-card px-2 py-0.5 text-[11px] font-bold whitespace-nowrap shadow-sm" style={{ borderColor: corPrazo(pct), color: corPrazo(pct) }}>
                    {paciente.iniciais} · {Math.round(pct)}%
                  </span>
                  <span className="h-2.5 w-0.5" style={{ background: corPrazo(pct) }} />
                  <span className="size-2.5 rotate-45 -translate-y-1.5" style={{ background: corPrazo(pct) }} />
                </div>
              </div>
            )}
          </div>
          <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
            {FAIXAS_PRAZO.map((f) => (
              <li key={f.rotulo} className="inline-flex items-center gap-1.5">
                <span className="size-3 rounded-sm" style={{ background: f.cor }} aria-hidden />
                {f.rotulo}
              </li>
            ))}
          </ul>
          {paciente && (
            <p className="fx-fade-up mt-2 text-xs text-muted-foreground">
              Paciente selecionado: <b className="text-foreground">{paciente.solicitacao_id}</b> está com {Math.round(pct)}% do prazo da classe {paciente.classe} ({rotuloPrazo(pct).toLowerCase()}).
            </p>
          )}
        </section>

        <div className="grid gap-4 @3xl:grid-cols-2">
          <section className="fx-fade-up rounded-xl bg-muted/40 p-4" style={{ animationDelay: "160ms" }} aria-label="Regras do nosso algoritmo">
            <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold">
              <TrendingUp className="size-4" aria-hidden /> Regras do nosso algoritmo
            </h3>
            {paciente && <p className="mb-2 text-xs text-muted-foreground">Regras acionadas em {paciente.solicitacao_id} ficam destacadas.</p>}
            <ul className="space-y-2">
              {REGRAS.map((r, i) => {
                const acionada = paciente ? r.gatilho(regrasDoPaciente) : false
                return (
                  <li
                    key={r.codigo}
                    className={cn("fx-fade-up relative overflow-hidden rounded-lg border p-3", r.ouro && "fx-glow", acionada && "ring-2 ring-primary/50")}
                    style={{
                      animationDelay: `${200 + i * 140}ms`,
                      borderColor: r.ouro ? "var(--ouro)" : undefined,
                      background: r.ouro ? "color-mix(in oklab, var(--ouro) 12%, transparent)" : undefined,
                    }}
                  >
                    {acionada && <span key={paciente?.solicitacao_id} className="fx-row-sweep pointer-events-none absolute inset-0" aria-hidden />}
                    <div className="relative flex items-start gap-3">
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg" style={{ background: r.ouro ? "var(--ouro)" : "var(--muted)", color: r.ouro ? "oklch(0.25 0.05 80)" : undefined }}>
                        <r.icone className="size-4" aria-hidden />
                      </span>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                          {r.titulo}
                          <Badge variant="outline" className="text-[10px]">
                            {r.codigo}
                          </Badge>
                          {acionada && (
                            <Badge className="fx-pop text-[10px]">acionada neste paciente</Badge>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{r.texto}</p>
                      </div>
                    </div>
                  </li>
                )
              })}
            </ul>
          </section>

          <CartaoGrafico titulo="Pacientes por classe" descricao="Fila inteira · vencidos (>100%) marcados em vermelho hachurado" atraso={200}>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={porClasse} margin={{ top: 20, right: 8, bottom: 0, left: -12 }}>
                  <defs>
                    <pattern id="hachura-vencido" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                      <rect width="6" height="6" fill="var(--prazo-vencido)" />
                      <rect width="2.5" height="6" fill="white" fillOpacity="0.45" />
                    </pattern>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="classe" tick={{ fontSize: 12, fontWeight: 600, fill: "var(--foreground)" }} stroke="var(--border)" />
                  <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
                  <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
                  <Bar name="No prazo" dataKey="noPrazo" stackId="c" animationDuration={900}>
                    {porClasse.map((d) => (
                      <Cell key={d.classe} fill={corClasse(d.classe)} fillOpacity={paciente && paciente.classe !== d.classe ? 0.4 : 1} stroke={paciente?.classe === d.classe ? "var(--foreground)" : "none"} strokeWidth={2} />
                    ))}
                  </Bar>
                  <Bar name="Vencidos" dataKey="vencidos" stackId="c" fill="url(#hachura-vencido)" radius={[4, 4, 0, 0]} animationDuration={900} animationBegin={200} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            {paciente ? (
              <div className="fx-pop mt-2 flex flex-wrap items-center gap-2 rounded-lg border bg-muted/40 p-2 text-xs">
                <ClasseBadge classe={paciente.classe} />
                <span>
                  <b>{paciente.solicitacao_id}</b> · classe {paciente.classe} · <b style={{ color: corPrazo(pct) }}>{Math.round(pct)}% do prazo</b>
                </span>
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">Selecione um paciente na Fila ou em Pacientes para destacar a classe e o % do prazo aqui.</p>
            )}
          </CartaoGrafico>
        </div>
      </div>
    </div>
  )
}
