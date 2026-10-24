import { useMemo, useState } from "react"
import { Activity, BedDouble, ClipboardList, FileSearch, History, Pill, ShieldAlert, Stethoscope, Syringe, type LucideIcon } from "lucide-react"
import type { Paciente, TipoHistorico } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { formatarData } from "@/lib/datas"
import { cn } from "@/lib/utils"

const CONFIG: Record<TipoHistorico, { rotulo: string; icone: LucideIcon; cor: string }> = {
  cirurgia_previa: { rotulo: "Cirurgias", icone: Syringe, cor: "var(--cls-a2)" },
  internacao_previa: { rotulo: "Internações", icone: BedDouble, cor: "var(--cls-c)" },
  consulta: { rotulo: "Consultas", icone: Stethoscope, cor: "var(--primary)" },
  exame: { rotulo: "Exames", icone: FileSearch, cor: "oklch(0.62 0.12 185)" },
  alergia: { rotulo: "Alergias", icone: ShieldAlert, cor: "var(--desce)" },
  medicacao_continua: { rotulo: "Medicações", icone: Pill, cor: "var(--cls-c)" },
  solicitacao_anterior: { rotulo: "Solicitações", icone: ClipboardList, cor: "var(--muted-foreground)" },
  alteracao_prioridade: { rotulo: "Mudanças de prioridade", icone: Activity, cor: "oklch(0.62 0.15 300)" },
}

const LIMITE = 6

export function HistoricoPaciente({ p }: { p: Paciente }) {
  const [ativos, setAtivos] = useState<Set<TipoHistorico>>(new Set())
  const [tudo, setTudo] = useState(false)

  const alergias = p.historico.filter((h) => h.tipo === "alergia")
  const medicacoes = p.historico.filter((h) => h.tipo === "medicacao_continua")
  const contagem = useMemo(() => {
    const c = new Map<TipoHistorico, number>()
    p.historico.forEach((h) => c.set(h.tipo, (c.get(h.tipo) ?? 0) + 1))
    return c
  }, [p.historico])

  const filtrados = useMemo(
    () => [...p.historico].filter((h) => ativos.size === 0 || ativos.has(h.tipo)).sort((a, b) => b.data.localeCompare(a.data)),
    [p.historico, ativos]
  )
  const visiveis = tudo ? filtrados : filtrados.slice(0, LIMITE)

  const alternar = (tipo: TipoHistorico) =>
    setAtivos((atual) => {
      const novo = new Set(atual)
      if (novo.has(tipo)) novo.delete(tipo)
      else novo.add(tipo)
      return novo
    })

  return (
    <section className="fx-fade-up rounded-xl bg-muted/40 p-3" aria-label="Histórico do paciente">
      <h3 className="mb-3 flex items-center gap-1.5 text-sm font-semibold">
        <History className="size-4" aria-hidden /> Histórico do paciente
      </h3>

      <div className="mb-3 grid gap-2 @lg:grid-cols-2">
        <div className="rounded-lg border p-2.5" style={{ borderColor: alergias.length ? "var(--desce)" : undefined, background: alergias.length ? "color-mix(in oklab, var(--desce) 7%, transparent)" : undefined }}>
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide" style={{ color: alergias.length ? "var(--desce)" : "var(--muted-foreground)" }}>
            <ShieldAlert className="size-3.5" aria-hidden /> Alergias
          </div>
          <div className="flex flex-wrap gap-1.5">
            {alergias.length === 0 && <span className="text-xs text-muted-foreground">Nenhuma alergia registrada</span>}
            {alergias.map((a, i) => (
              <span key={a.descricao} className="fx-pop rounded-full border px-2 py-0.5 text-xs font-semibold" style={{ borderColor: "var(--desce)", color: "var(--desce)", animationDelay: `${i * 80}ms` }}>
                {a.descricao}
              </span>
            ))}
          </div>
        </div>
        <div className="rounded-lg border p-2.5" style={{ background: medicacoes.length ? "color-mix(in oklab, var(--cls-c) 7%, transparent)" : undefined }}>
          <div className="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <Pill className="size-3.5" aria-hidden /> Medicações contínuas
          </div>
          <div className="flex flex-wrap gap-1.5">
            {medicacoes.length === 0 && <span className="text-xs text-muted-foreground">Nenhuma registrada</span>}
            {medicacoes.map((m, i) => (
              <span key={m.descricao} className="fx-pop rounded-full border px-2 py-0.5 text-xs font-medium" style={{ borderColor: "var(--cls-c)", color: "var(--cls-c-fg)", animationDelay: `${i * 80}ms` }}>
                {m.descricao}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filtrar histórico por tipo">
        {(Object.keys(CONFIG) as TipoHistorico[])
          .filter((t) => contagem.has(t))
          .map((t) => {
            const { rotulo, icone: Icone } = CONFIG[t]
            const ligado = ativos.has(t)
            return (
              <button
                key={t}
                type="button"
                aria-pressed={ligado}
                onClick={() => alternar(t)}
                className={cn("inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring", ligado ? "border-primary bg-primary/10 text-primary" : "hover:bg-muted")}
              >
                <Icone className="size-3" aria-hidden />
                {rotulo}
                <span className="text-muted-foreground tabular-nums">{contagem.get(t)}</span>
              </button>
            )
          })}
        {ativos.size > 0 && (
          <Button size="xs" variant="ghost" onClick={() => setAtivos(new Set())}>
            Limpar filtros
          </Button>
        )}
      </div>

      <ol className="relative space-y-3 pl-1">
        <span className="fx-grow-y absolute top-2 bottom-2 left-[15px] w-px bg-border" style={{ transformOrigin: "center top", animationDuration: "1.1s" }} aria-hidden />
        {visiveis.map((h, i) => {
          const { icone: Icone, cor, rotulo } = CONFIG[h.tipo]
          return (
            <li key={`${h.data}-${h.descricao}`} className="fx-fade-up relative flex gap-3" style={{ animationDelay: `${Math.min(i, 8) * 70}ms` }}>
              <span className="relative z-10 flex size-[30px] shrink-0 items-center justify-center rounded-full border bg-card" style={{ borderColor: cor, color: cor }}>
                <Icone className="size-3.5" aria-hidden />
              </span>
              <div className="min-w-0 pt-0.5">
                <div className="flex flex-wrap items-baseline gap-x-2 text-xs">
                  <time className="font-semibold tabular-nums" dateTime={h.data}>
                    {formatarData(h.data)}
                  </time>
                  <span className="text-muted-foreground">{rotulo}</span>
                  <span className="text-muted-foreground">· {h.origem}</span>
                </div>
                <p className="text-sm leading-snug">{h.descricao}</p>
              </div>
            </li>
          )
        })}
        {visiveis.length === 0 && <li className="text-xs text-muted-foreground">Nenhum item para os filtros escolhidos.</li>}
      </ol>

      {filtrados.length > LIMITE && (
        <Button variant="outline" size="sm" className="mt-3 w-full" onClick={() => setTudo((v) => !v)}>
          {tudo ? "Mostrar menos" : `Ver tudo (${filtrados.length})`}
        </Button>
      )}
    </section>
  )
}
