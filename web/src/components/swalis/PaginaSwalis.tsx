import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Archive, ChevronDown, Crown, FlaskConical, Hourglass, ShieldCheck, TrendingUp, UserCheck, History, type LucideIcon } from "lucide-react"
import { META, PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { CLASSES, FAIXAS_PRAZO, corClasse, corPrazo, rotuloPrazo } from "@/lib/cores"
import { cn } from "@/lib/utils"
import { ClasseBadge } from "@/components/shared/Basicos"
import { CartaoGrafico } from "@/components/shared/detalhe/Cartao"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useStore } from "@/store/useStore"

type Regra = { codigo: string; titulo: string; texto: string; icone: LucideIcon; ouro?: boolean; vale?: (p: Paciente) => boolean }

const REGRAS: Regra[] = [
  { codigo: "I-01", titulo: "Regra de ouro", texto: "Paciente com CID iniciado por C nunca fica abaixo de quem não tem urgência clínica. Vale o CID, nunca a flag oncológica do cadastro.", icone: Crown, ouro: true, vale: (p) => p.oncologico },
  { codigo: "I-04", titulo: "Humano decide a classe", texto: "Mudança de classe exige decisão do regulador. A carga inicial fica marcada como sugerida, não confirmada.", icone: UserCheck },
  { codigo: "I-05", titulo: "O LLM extrai, não decide", texto: "O modelo só extrai e cita trechos do texto. Nunca define classe nem altera CID sozinho.", icone: FlaskConical, vale: (p) => p.sinais_texto.length > 0 },
  { codigo: "I-06", titulo: "Antes da entrada é histórico", texto: "Eventos anteriores à entrada na fila não contam como piora durante a espera.", icone: History, vale: (p) => p.eventos.some((e) => e.historico) },
  { codigo: "I-07", titulo: "Alertas não entram no score", texto: "HbA1c, ASA, distância, faltas e quantidade de eventos viram alertas e auditoria, não pontuação.", icone: ShieldCheck, vale: (p) => p.alertas.length > 0 },
  { codigo: "I-03", titulo: "Nada é apagado", texto: "Solicitações saem da fila por status (ativa, suspensa, removida) com motivo, nunca por exclusão.", icone: Archive },
]

const TITULO_SECAO = "text-base font-semibold"

export default function PaginaSwalis() {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const paciente = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  const porClasse = useMemo(
    () =>
      CLASSES.map((c) => {
        const g = PACIENTES.filter((p) => p.classe === c)
        const vencidos = g.filter((p) => p.pct > 100).length
        return { classe: c, noPrazo: g.length - vencidos, vencidos, total: g.length }
      }),
    []
  )

  const pct = paciente?.pct ?? 0
  const posicaoMarcador = pct <= 100 ? pct * 0.8 : 80 + Math.min(1, (pct - 100) / 1000) * 20

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-6xl space-y-6 p-4">
        <section className="fx-fade-up rounded-xl bg-muted/40 p-4">
          <h2 className={cn("mb-2 flex items-center gap-2", TITULO_SECAO)}>
            <Hourglass className="size-4" aria-hidden /> Como funciona o SWALIS
          </h2>
          <div className="max-w-prose space-y-2 text-sm leading-relaxed text-muted-foreground">
            <p>
              Cada solicitação recebe uma <b className="text-foreground">classe de urgência</b> com prazo máximo de espera. O <b className="text-foreground">% do prazo consumido</b> é dias em fila ÷ prazo da classe e ordena dentro da classe.
            </p>
            <p>
              A ordem final vem da trava: <b className="text-foreground">camada 1 (oncológicos), camada 2 (urgentes), camada 3 (demais)</b>, e o score decide dentro de cada camada.
            </p>
          </div>
          <p className="mt-3 max-w-prose rounded-lg bg-background/60 p-3 text-xs leading-relaxed text-muted-foreground">
            {META.versao_regras.startsWith("stub") ? (
              <>
                <b className="text-foreground">Versão {META.versao_regras}: SWALIS provisório.</b> A classe vem da prioridade manual do cadastro (alta → B, média → C, baixa → D, oncológico → A2).
              </>
            ) : (
              <>
                <b className="text-foreground">Regras {META.versao_regras}.</b> A classe sai do cruzamento de dois eixos: progressão (CID, biópsia e sinais do texto) e sintoma (dor, limitação e complicações). Os sinais do LLM só geram alertas e nunca mudam a classe.
              </>
            )}
          </p>
        </section>

        <section className="fx-fade-up overflow-hidden rounded-xl bg-muted/40" style={{ animationDelay: "80ms" }}>
          <h2 className={cn("px-4 pt-4 pb-2", TITULO_SECAO)}>Classes de urgência</h2>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-20">Classe</TableHead>
                  <TableHead>Descrição</TableHead>
                  <TableHead className="w-28">Prazo máximo</TableHead>
                  <TableHead>Exemplos</TableHead>
                  <TableHead className="w-24 text-right">Na fila</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {META.swalis.map((c, i) => {
                  const atual = paciente?.classe === c.classe
                  return (
                    <TableRow key={c.classe} className={cn("fx-fade-up transition-colors", atual && "bg-primary/10")} style={{ animationDelay: `${i * 70}ms` }}>
                      <TableCell>
                        <ClasseBadge classe={c.classe} className={atual ? "fx-glow" : undefined} />
                      </TableCell>
                      <TableCell className="whitespace-normal text-sm">{c.descricao}</TableCell>
                      <TableCell className="font-semibold tabular-nums">{c.prazo} dias</TableCell>
                      <TableCell className="whitespace-normal text-xs text-muted-foreground">{c.exemplos}</TableCell>
                      <TableCell className="text-right tabular-nums">{porClasse.find((x) => x.classe === c.classe)?.total ?? 0}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </div>
        </section>

        <section className="fx-fade-up rounded-xl bg-muted/40 p-4" style={{ animationDelay: "120ms" }} aria-labelledby="titulo-faixas">
          <h2 id="titulo-faixas" className={cn("mb-4", TITULO_SECAO)}>
            Faixas do % do prazo consumido
          </h2>
          <div className="relative pt-8 pb-1">
            <div className="flex h-5 overflow-hidden rounded-full">
              {[{ ...FAIXAS_PRAZO[0], largura: 50 }, { ...FAIXAS_PRAZO[1], largura: 25 }, { ...FAIXAS_PRAZO[2], largura: 25 }].map((f, i) => (
                <div key={f.rotulo} className="fx-grow-x" style={{ width: `${f.largura * 0.8}%`, background: f.cor, animationDelay: `${i * 160}ms` }} />
              ))}
              <div className="fx-grow-x flex-1" style={{ background: FAIXAS_PRAZO[3].cor, animationDelay: "480ms", backgroundImage: "repeating-linear-gradient(135deg, transparent 0 4px, rgb(255 255 255 / 0.4) 4px 6px)" }} />
            </div>
            <div className="relative mt-1 h-4 text-xs text-muted-foreground tabular-nums">
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
              <div key={paciente.id} className="fx-fade-up absolute top-0 -translate-x-1/2" style={{ left: `${posicaoMarcador}%` }}>
                <div className="flex flex-col items-center">
                  <span className="rounded-full bg-card px-2 py-0.5 text-xs font-bold whitespace-nowrap shadow-sm" style={{ boxShadow: `inset 0 0 0 1px ${corPrazo(pct)}`, color: corPrazo(pct) }}>
                    {paciente.iniciais} · {Math.round(pct).toLocaleString("pt-BR")}%
                  </span>
                  <span className="h-2.5 w-0.5" style={{ background: corPrazo(pct) }} />
                  <span className="size-2.5 -translate-y-1.5 rotate-45" style={{ background: corPrazo(pct) }} />
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
            <p className="fx-fade-up mt-3 text-xs text-muted-foreground">
              Selecionado: <b className="text-foreground">{paciente.id}</b> com {Math.round(pct).toLocaleString("pt-BR")}% do prazo da classe {paciente.classe} ({rotuloPrazo(pct).toLowerCase()}).
            </p>
          )}
        </section>

        <div className="grid gap-4 @3xl:grid-cols-2">
          <details className="group fx-fade-up rounded-xl bg-muted/40 open:pb-4" open={Boolean(paciente)} style={{ animationDelay: "160ms" }}>
            <summary className="flex cursor-pointer list-none items-center justify-between gap-2 rounded-xl p-4 outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
              <span className={cn("flex items-center gap-2", TITULO_SECAO)}>
                <TrendingUp className="size-4" aria-hidden /> Regras e invariantes do sistema
              </span>
              <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform group-open:rotate-180" aria-hidden />
            </summary>
            <div className="space-y-3 px-4">
              {paciente && <p className="text-xs text-muted-foreground">Regras que se aplicam a {paciente.id} ficam destacadas.</p>}
              <ul className="space-y-2">
                {REGRAS.map((r, i) => {
                  const aplica = paciente && r.vale ? r.vale(paciente) : false
                  return (
                    <li
                      key={r.codigo}
                      className={cn("fx-fade-up relative overflow-hidden rounded-xl p-3", r.ouro ? "fx-glow" : "bg-background/60", aplica && "ring-2 ring-primary/40")}
                      style={{ animationDelay: `${200 + i * 120}ms`, background: r.ouro ? "color-mix(in oklab, var(--ouro) 14%, transparent)" : undefined }}
                    >
                      <div className="relative flex items-start gap-3">
                        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg" style={{ background: r.ouro ? "var(--ouro)" : "var(--muted)", color: r.ouro ? "oklch(0.25 0.05 80)" : undefined }}>
                          <r.icone className="size-4" aria-hidden />
                        </span>
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                            {r.titulo}
                            <Badge variant="outline" className="text-xs font-normal">
                              {r.codigo}
                            </Badge>
                            {aplica && <Badge className="fx-pop text-xs">vale para este paciente</Badge>}
                          </div>
                          <p className="mt-0.5 max-w-prose text-xs leading-relaxed text-muted-foreground">{r.texto}</p>
                        </div>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          </details>

          <CartaoGrafico titulo="Solicitações por classe" descricao="Vencidos (>100% do prazo) em vermelho hachurado" atraso={200}>
            <div className="h-48 sm:h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={porClasse} margin={{ top: 20, right: 8, bottom: 0, left: -6 }}>
                  <defs>
                    <pattern id="hachura-vencido" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                      <rect width="6" height="6" fill="var(--prazo-vencido)" />
                      <rect width="2.5" height="6" fill="white" fillOpacity="0.45" />
                    </pattern>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="classe" tick={{ fontSize: 12, fontWeight: 600, fill: "var(--foreground)" }} stroke="var(--border)" />
                  <YAxis tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
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
              <div className="fx-pop mt-2 flex flex-wrap items-center gap-2 rounded-lg bg-background/60 p-2 text-xs">
                <ClasseBadge classe={paciente.classe} />
                <span>
                  <b>{paciente.id}</b> · classe {paciente.classe} · <b style={{ color: corPrazo(pct) }}>{Math.round(pct).toLocaleString("pt-BR")}% do prazo</b>
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
