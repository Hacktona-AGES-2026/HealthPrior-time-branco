import { useMemo, useState } from "react"
import { History, Link2 } from "lucide-react"
import type { Evento, Paciente, TipoEvento } from "@/data/tipos"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { formatarData } from "@/lib/datas"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"
import { COR_EVENTO, ICONE_EVENTO, ROTULO_EVENTO_TIPO } from "./IconesEvento"

const LIMITE = 6

const detalheValor = (e: Evento) => {
  if (e.valor === null) return null
  if (e.tipo === "hba1c") return `${String(e.valor).replace(".", ",")}%`
  if (e.tipo === "internacao") return `${e.valor} dias`
  return String(e.valor)
}

export function HistoricoPaciente({ p }: { p: Paciente }) {
  const [ativos, setAtivos] = useState<Set<TipoEvento>>(new Set())
  const [tudo, setTudo] = useState(false)
  const selecionar = useStore((s) => s.selecionar)

  const contagem = useMemo(() => {
    const c = new Map<TipoEvento, number>()
    p.eventos.forEach((e) => c.set(e.tipo, (c.get(e.tipo) ?? 0) + 1))
    return c
  }, [p.eventos])

  const filtrados = useMemo(() => [...p.eventos].filter((e) => ativos.size === 0 || ativos.has(e.tipo)).sort((a, b) => b.data.localeCompare(a.data)), [p.eventos, ativos])
  const visiveis = tudo ? filtrados : filtrados.slice(0, LIMITE)

  const alternar = (tipo: TipoEvento) =>
    setAtivos((atual) => {
      const novo = new Set(atual)
      if (novo.has(tipo)) novo.delete(tipo)
      else novo.add(tipo)
      return novo
    })

  return (
    <section className="fx-fade-up rounded-xl bg-muted/40 p-3" aria-label="Eventos do paciente">
      <h3 className="mb-3 flex flex-wrap items-center gap-1.5 text-sm font-semibold">
        <History className="size-4" aria-hidden /> Eventos do paciente
        <span className="text-xs font-normal text-muted-foreground tabular-nums">{p.eventos.length} registrados</span>
      </h3>

      {p.eventos.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum evento registrado para esta solicitação.</p>
      ) : (
        <>
          <div className="mb-3 flex flex-wrap gap-1.5" role="group" aria-label="Filtrar eventos por tipo">
            {(Object.keys(ICONE_EVENTO) as TipoEvento[])
              .filter((t) => contagem.has(t))
              .map((t) => {
                const Icone = ICONE_EVENTO[t]
                const ligado = ativos.has(t)
                return (
                  <button
                    key={t}
                    type="button"
                    aria-pressed={ligado}
                    onClick={() => alternar(t)}
                    className={cn("inline-flex min-h-9 items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium sm:min-h-0 outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring", ligado ? "bg-primary/15 text-foreground" : "bg-background/60 text-muted-foreground hover:text-foreground")}
                  >
                    <Icone className="size-3" aria-hidden />
                    {ROTULO_EVENTO_TIPO[t]}
                    <span className="tabular-nums opacity-60">{contagem.get(t)}</span>
                  </button>
                )
              })}
            {ativos.size > 0 && (
              <Button size="sm" variant="ghost" className="h-9 sm:h-8" onClick={() => setAtivos(new Set())}>
                Limpar filtros
              </Button>
            )}
          </div>

          <div className="max-h-[26rem] overflow-y-auto overscroll-contain pr-1 sm:max-h-[32rem]">
          <ol className="relative space-y-3 pl-1">
            <span className="fx-grow-y absolute top-2 bottom-2 left-[15px] w-px bg-border" style={{ transformOrigin: "center top", animationDuration: "1.1s" }} aria-hidden />
            {visiveis.map((e, i) => {
              const Icone = ICONE_EVENTO[e.tipo]
              const valor = detalheValor(e)
              return (
                <li key={e.id} className="fx-fade-up relative flex gap-3" style={{ animationDelay: `${Math.min(i, 8) * 70}ms` }}>
                  <span className="relative z-10 flex size-[30px] shrink-0 items-center justify-center rounded-full bg-card" style={{ boxShadow: `inset 0 0 0 1px ${COR_EVENTO[e.tipo]}`, color: COR_EVENTO[e.tipo] }}>
                    <Icone className="size-3.5" aria-hidden />
                  </span>
                  <div className="min-w-0 pt-0.5">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-xs">
                      <span className="font-semibold">{ROTULO_EVENTO_TIPO[e.tipo]}</span>
                      <time className="tabular-nums text-muted-foreground" dateTime={e.data}>
                        {formatarData(e.data)}
                      </time>
                      {e.resultado && <Badge variant="secondary" className="px-1.5 font-normal">{e.resultado.replaceAll("_", " ")}</Badge>}
                      {valor && <span className="font-medium tabular-nums">{valor}</span>}
                      {e.historico && <Badge variant="outline" title="Histórico: não conta como piora" className="px-1.5 font-normal text-muted-foreground">antes da entrada</Badge>}
                      {e.origem && <span className="text-muted-foreground">· {e.origem}</span>}
                    </div>
                    <p className="break-words text-sm leading-snug">{e.descricao}</p>
                  </div>
                </li>
              )
            })}
          </ol>
          </div>

          {filtrados.length > LIMITE && (
            <Button variant="outline" size="sm" className="mt-3 h-9 w-full sm:h-8" onClick={() => setTudo((v) => !v)}>
              {tudo ? "Mostrar menos" : `Ver tudo (${filtrados.length})`}
            </Button>
          )}
        </>
      )}

      {p.outras.length > 0 && (
        <div className="mt-4 border-t border-border/60 pt-3">
          <h4 className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            <Link2 className="size-3" aria-hidden /> Outras solicitações do mesmo paciente
          </h4>
          <ul className="space-y-1">
            {p.outras.map((o) => (
              <li key={o.id}>
                <button type="button" onClick={() => selecionar(o.id, true)} className="text-left text-sm outline-none hover:underline focus-visible:underline">
                  <b className="tabular-nums">{o.id}</b> · {o.procedimento} · #{o.posicao}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
