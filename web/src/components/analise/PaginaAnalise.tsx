import { useMemo, useState } from "react"
import { Bar, BarChart, CartesianGrid, Cell, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { ChevronDown, CheckCheck, Layers, Siren, TimerOff, type LucideIcon } from "lucide-react"
import { ESPECIALIDADES, PACIENTES, TOTAL_FILA } from "@/data/fila"
import { CLASSES, NOME_CAMADA, corClasse, corPrazo } from "@/lib/cores"
import { useContagem } from "@/lib/motion"
import { cn } from "@/lib/utils"
import { CamadaBadge, ClasseBadge } from "@/components/shared/Basicos"
import { CartaoGrafico } from "@/components/shared/detalhe/Cartao"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useStore } from "@/store/useStore"

function Resumo({ icone: Icone, rotulo, valor, sufixo = "", cor, detalhe, indice, aoClicar }: { icone: LucideIcon; rotulo: string; valor: number; sufixo?: string; cor?: string; detalhe: string; indice: number; aoClicar?: () => void }) {
  const animado = useContagem(valor, 900)
  return (
    <button type="button" onClick={aoClicar} className="fx-fade-up flex items-start gap-3 rounded-xl bg-muted/40 p-3 text-left transition-colors outline-none hover:bg-muted/70 focus-visible:ring-2 focus-visible:ring-ring" style={{ animationDelay: `${indice * 80}ms` }}>
      <Icone className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0">
        <div className="text-xl leading-none font-semibold tabular-nums" style={{ color: cor }}>
          {Math.round(animado).toLocaleString("pt-BR")}
          {sufixo}
        </div>
        <div className="mt-1 text-xs font-medium">{rotulo}</div>
        <div className="truncate text-xs text-muted-foreground">{detalhe}</div>
      </div>
    </button>
  )
}

const BINS_PRAZO: [string, number, number][] = [
  ["0–25%", 0, 25],
  ["25–50%", 25, 50],
  ["50–75%", 50, 75],
  ["75–100%", 75, 100],
  ["100–200%", 100, 200],
  ["200–500%", 200, 500],
  ["500–1000%", 500, 1000],
  [">1000%", 1000, Infinity],
]

const BINS_POSICAO: [string, number, number][] = [
  ["desceu >100", -Infinity, -100],
  ["desceu até 100", -100, -1],
  ["igual", 0, 0],
  ["subiu até 100", 1, 100],
  ["subiu 100–300", 101, 300],
  ["subiu >300", 301, Infinity],
]

const grupoAlerta = (a: string) => (a.startsWith("HbA1c") ? "HbA1c acima de 8,5%" : a)


export default function PaginaAnalise() {
  const decisoes = useStore((s) => s.decisoes)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const setFiltros = useStore((s) => s.setFiltros)
  const ir = useStore((s) => s.ir)
  const [maisAberto, setMaisAberto] = useState(false)

  const dados = useMemo(() => {
    const prioridades = [
      ["alta", "Alta"],
      ["media", "Média"],
      ["baixa", "Baixa"],
      ["vazia", "Sem prioridade"],
    ] as const
    const porClasse = CLASSES.map((c) => {
      const g = PACIENTES.filter((p) => p.classe === c)
      return {
        classe: c,
        alta: g.filter((p) => p.prioridade_atual === "alta").length,
        media: g.filter((p) => p.prioridade_atual === "media").length,
        baixa: g.filter((p) => p.prioridade_atual === "baixa").length,
        vazia: g.filter((p) => p.prioridade_atual === null).length,
      }
    }).filter((d) => d.alta + d.media + d.baixa + d.vazia > 0)
    const bins = BINS_PRAZO.map(([faixa, de, ate]) => ({
      faixa,
      n: PACIENTES.filter((p) => p.pct >= de && (ate === Infinity ? true : p.pct < ate)).length,
      cor: corPrazo(de >= 100 ? 110 : de + 1),
    }))
    const posicoes = BINS_POSICAO.map(([faixa, de, ate]) => {
      const n = PACIENTES.filter((p) => {
        const d = p.posicao_atual - p.posicao
        return d >= de && d <= ate
      }).length
      return { faixa, n, sobe: de > 0 }
    })
    const porEsp = ESPECIALIDADES.map((e) => {
      const g = PACIENTES.filter((p) => p.especialidade === e)
      return { especialidade: e, c1: g.filter((p) => p.camada === 1).length, c2: g.filter((p) => p.camada === 2).length, c3: g.filter((p) => p.camada === 3).length }
    }).sort((a, b) => b.c1 + b.c2 + b.c3 - (a.c1 + a.c2 + a.c3))
    const matriz = ESPECIALIDADES.map((e) => ({ especialidade: e, celulas: CLASSES.map((c) => PACIENTES.filter((p) => p.especialidade === e && p.classe === c).length) }))
    const maxCelula = Math.max(...matriz.flatMap((m) => m.celulas))
    const contagemAlertas = new Map<string, number>()
    PACIENTES.forEach((p) => new Set(p.alertas.map(grupoAlerta)).forEach((a) => contagemAlertas.set(a, (contagemAlertas.get(a) ?? 0) + 1)))
    const alertas = [...contagemAlertas.entries()].sort((a, b) => b[1] - a[1])
    const esperas = [...PACIENTES].sort((a, b) => b.dias_em_fila - a.dias_em_fila).slice(0, 10)
    return { prioridades, porClasse, bins, posicoes, porEsp, matriz, maxCelula, alertas, esperas }
  }, [])

  const aprovados = Object.values(decisoes).filter((d) => d.status === "aprovado").length
  const editados = Object.values(decisoes).filter((d) => d.status === "editado").length
  const revisados = aprovados + editados
  const oncologicos = PACIENTES.filter((p) => p.camada === 1).length
  const urgentes = PACIENTES.filter((p) => p.camada === 2).length
  const vencidos = PACIENTES.filter((p) => p.pct > 100).length
  const filtrarEIr = (parcial: Parameters<typeof setFiltros>[0]) => {
    setFiltros(parcial)
    ir("fila")
  }
  const corPrioridade = { alta: "var(--cls-a1)", media: "var(--cls-b)", baixa: "var(--cls-c)", vazia: "var(--muted-foreground)" }
  const corCamada = { c1: "var(--cls-a2)", c2: "var(--cls-b)", c3: "var(--cls-d)" }

  const cartaoPrioridade = (
    <CartaoGrafico titulo="Prioridade manual × classe sugerida" descricao="Cadastro hoje vs. classe do SWALIS">
      <div className="h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados.porClasse} margin={{ top: 12, right: 8, bottom: 0, left: -6 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis dataKey="classe" tick={{ fontSize: 12, fontWeight: 600, fill: "var(--foreground)" }} stroke="var(--border)" />
            <YAxis tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            {dados.prioridades.map(([chave, rotulo], i) => (
              <Bar key={chave} name={rotulo} dataKey={chave} stackId="p" fill={corPrioridade[chave]} fillOpacity={0.85} animationDuration={900} animationBegin={i * 120} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )

  const cartaoHistograma = (
    <CartaoGrafico titulo="Histograma do % do prazo consumido" descricao="Acima de 100% são vencidos">
      <div className="h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados.bins} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" tickCount={4} />
            <YAxis type="category" dataKey="faixa" width={76} interval={0} tick={{ fontSize: 12, fill: "var(--foreground)" }} stroke="none" />
            <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} formatter={(v) => [v, "Solicitações"]} />
            <ReferenceLine y="100–200%" stroke="var(--prazo-vencido)" strokeDasharray="3 3" />
            <Bar dataKey="n" radius={[0, 4, 4, 0]} animationDuration={0}>
              {dados.bins.map((b) => (
                <Cell key={b.faixa} fill={b.cor} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )

  const cartaoPosicao = (
    <CartaoGrafico titulo="Mudança de posição: atual → proposta" descricao="Quantas posições cada solicitação sobe ou desce">
      <div className="h-48 sm:h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados.posicoes} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" tickCount={4} />
            <YAxis type="category" dataKey="faixa" width={112} interval={0} tick={{ fontSize: 12, fill: "var(--foreground)" }} stroke="none" />
            <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} formatter={(v) => [v, "Solicitações"]} />
            <Bar dataKey="n" radius={[0, 4, 4, 0]} animationDuration={0}>
              {dados.posicoes.map((b) => (
                <Cell key={b.faixa} fill={b.faixa === "igual" ? "var(--muted-foreground)" : b.sobe ? "var(--sobe)" : "var(--desce)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )

  const cartaoEsperas = (
    <CartaoGrafico titulo="10 maiores esperas" descricao="Clique para abrir na fila">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Pos.</TableHead>
            <TableHead>Caso</TableHead>
            <TableHead>Camada</TableHead>
            <TableHead className="text-right">Dias</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {dados.esperas.map((p, i) => (
            <TableRow key={p.id} className="fx-fade-up cursor-pointer" style={{ animationDelay: `${i * 45}ms` }} onClick={() => abrirNaFila(p.id)}>
              <TableCell className="tabular-nums">#{p.posicao}</TableCell>
              <TableCell>
                <button type="button" className="text-left outline-none focus-visible:underline" onClick={() => abrirNaFila(p.id)}>
                  <div className="font-semibold tabular-nums">{p.id}</div>
                  <div className="max-w-40 truncate text-xs text-muted-foreground sm:max-w-52">{p.procedimento}</div>
                </button>
              </TableCell>
              <TableCell>
                <CamadaBadge camada={p.camada} />
              </TableCell>
              <TableCell className="text-right font-semibold tabular-nums">{p.dias_em_fila.toLocaleString("pt-BR")}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </CartaoGrafico>
  )

  const cartaoCamadas = (
    <CartaoGrafico titulo="Camadas por especialidade" descricao="Solicitações de cada especialidade por camada">
      <div className="h-72 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={dados.porEsp} layout="vertical" margin={{ top: 0, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12, fill: "var(--muted-foreground)" }} stroke="var(--border)" />
            <YAxis type="category" dataKey="especialidade" width={112} interval={0} tick={{ fontSize: 12, fill: "var(--foreground)" }} stroke="none" />
            <Tooltip cursor={{ fill: "var(--muted)", fillOpacity: 0.5 }} />
            <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
            <Bar name={`1 · ${NOME_CAMADA[1]}`} dataKey="c1" stackId="c" fill={corCamada.c1} animationDuration={900} />
            <Bar name={`2 · ${NOME_CAMADA[2]}`} dataKey="c2" stackId="c" fill={corCamada.c2} animationDuration={900} animationBegin={150} />
            <Bar name={`3 · ${NOME_CAMADA[3]}`} dataKey="c3" stackId="c" fill={corCamada.c3} animationDuration={900} animationBegin={300} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </CartaoGrafico>
  )

  const cartaoMapa = (
    <CartaoGrafico titulo="Mapa de calor: especialidade × classe" descricao="Número de solicitações por célula">
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
                    className={cn("fx-pop h-7 rounded text-center font-semibold tabular-nums", n === 0 && "text-muted-foreground/60")}
                    style={{
                      animationDelay: `${(li * 5 + ci) * 20}ms`,
                      background: n === 0 ? "var(--muted)" : `color-mix(in oklab, ${corClasse(CLASSES[ci])} ${Math.round(18 + (n / dados.maxCelula) * 60)}%, transparent)`,
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
  )

  const cartaoAlertas = (
    <CartaoGrafico titulo="Alertas de dados" descricao="Inconsistências do cadastro · clique para filtrar">
      <ul className="space-y-1.5">
        {dados.alertas.map(([alerta, n], i) => (
          <li key={alerta}>
            <button type="button" onClick={() => filtrarEIr({ alertas: true })} className="group w-full rounded-md p-1 text-left outline-none hover:bg-muted/60 focus-visible:ring-2 focus-visible:ring-ring">
              <div className="mb-0.5 flex items-baseline justify-between gap-2 text-xs">
                <span>{alerta}</span>
                <span className="font-semibold tabular-nums">{n}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <div className="fx-grow-x h-full rounded-full bg-[var(--prazo-limite)]" style={{ width: `${(n / dados.alertas[0][1]) * 100}%`, animationDelay: `${i * 90}ms` }} />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </CartaoGrafico>
  )

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="@container mx-auto max-w-7xl space-y-5 p-4">
        <div className="grid grid-cols-1 gap-3 @lg:grid-cols-2 @4xl:grid-cols-4">
          <Resumo indice={0} icone={Layers} rotulo="Camada 1 · oncológicos" valor={oncologicos} cor="var(--cls-a2-fg)" detalhe="CID iniciado por C" aoClicar={() => filtrarEIr({ camada: "1" })} />
          <Resumo indice={1} icone={Siren} rotulo="Camada 2 · urgentes" valor={urgentes} cor="var(--cls-b-fg)" detalhe="Sinal clínico de urgência" aoClicar={() => filtrarEIr({ camada: "2" })} />
          <Resumo indice={2} icone={TimerOff} rotulo="Vencidos (>100% do prazo)" valor={vencidos} cor="var(--prazo-vencido)" detalhe={`de ${TOTAL_FILA} na fila`} aoClicar={() => filtrarEIr({ vencidos: true })} />
          <Resumo indice={3} icone={CheckCheck} rotulo="Revisados" valor={revisados} cor="var(--sobe)" detalhe={`${aprovados} aprovados · ${editados} editados · ${TOTAL_FILA - revisados} pendentes`} aoClicar={() => filtrarEIr({ status: "revisados" })} />
        </div>

        <section aria-label="Resumo das análises">
          <h2 className="mb-2 text-sm font-semibold">Resumo</h2>
          <div className="grid gap-3 md:grid-cols-2">
            {cartaoPrioridade}
            {cartaoPosicao}
            {cartaoHistograma}
            {cartaoEsperas}
          </div>
        </section>

        <section aria-label="Mais análises" className="space-y-2">
          <button
            type="button"
            aria-expanded={maisAberto}
            aria-controls={maisAberto ? "mais-analises" : undefined}
            onClick={() => setMaisAberto((v) => !v)}
            className="flex w-full items-center justify-between gap-2 rounded-xl bg-muted/40 p-3 text-left text-sm font-semibold outline-none transition-colors hover:bg-muted/70 focus-visible:ring-2 focus-visible:ring-ring"
          >
            Mais análises
            <ChevronDown className={cn("size-4 shrink-0 text-muted-foreground transition-transform", maisAberto && "rotate-180")} aria-hidden />
          </button>
          {maisAberto && (
            <div id="mais-analises" className="grid gap-3 md:grid-cols-2">
              {cartaoCamadas}
              {cartaoMapa}
              {cartaoAlertas}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
