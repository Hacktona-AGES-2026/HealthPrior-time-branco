import { PACIENTES, TOTAL_FILA } from "@/data/fila"
import type { Camada, Paciente } from "@/data/tipos"
import { DESCRICAO_CAMADA, NOME_CAMADA } from "@/lib/cores"
import { CartaoGrafico } from "./Cartao"
import { SetaVariacao } from "@/components/shared/Basicos"

const COR: Record<Camada, string> = { 1: "var(--cls-a2)", 2: "var(--cls-b)", 3: "var(--cls-d)" }

export function CartaCamada({ p }: { p: Paciente }) {
  const delta = p.posicao_atual - p.posicao
  const TAMANHOS = ([1, 2, 3] as Camada[]).map((c) => ({ camada: c, n: PACIENTES.filter((x) => x.camada === c).length }))
  return (
    <CartaoGrafico titulo="Camada e posição" descricao="A trava impõe a ordem por camadas; o score ordena dentro de cada uma" className="@lg:col-span-2">
      <div className="relative pt-5 pb-1">
        <div className="flex h-4 overflow-hidden rounded-full">
          {TAMANHOS.map((t, i) => (
            <div key={t.camada} className="fx-grow-x relative" style={{ width: `${(t.n / TOTAL_FILA) * 100}%`, background: COR[t.camada], opacity: t.camada === p.camada ? 1 : 0.35, animationDelay: `${i * 140}ms` }} title={`Camada ${t.camada}: ${t.n}`} />
          ))}
        </div>
        <div className="fx-fade-up absolute top-0 -translate-x-1/2 text-center" style={{ left: `${(p.posicao / TOTAL_FILA) * 100}%`, animationDelay: "500ms" }}>
          <div className="rounded-full bg-foreground px-1.5 text-[10px] font-semibold text-background tabular-nums">#{p.posicao}</div>
          <div className="mx-auto size-1.5 rotate-45 bg-foreground" />
        </div>
        <div className="mt-1 flex text-[11px] text-muted-foreground">
          {TAMANHOS.map((t) => (
            <div key={t.camada} style={{ width: `${(t.n / TOTAL_FILA) * 100}%` }} className="truncate tabular-nums">
              {t.camada} · {NOME_CAMADA[t.camada]} ({t.n})
            </div>
          ))}
        </div>
      </div>
      <div className="mt-3 space-y-2 text-sm">
        <p>
          <span className="font-semibold">Camada {p.camada}: </span>
          <span className="text-muted-foreground">{DESCRICAO_CAMADA[p.camada]}</span>
        </p>
        {(p.motivos.length > 0 || p.sintomas.length > 0) && (
          <ul className="space-y-1 text-xs">
            {p.motivos.map((m, i) => (
              <li key={m} className="fx-fade-up flex items-start gap-1.5" style={{ animationDelay: `${i * 90}ms` }}>
                <span className="mt-1 size-1.5 shrink-0 rounded-full" style={{ background: "var(--cls-b)" }} aria-hidden />
                <span>{m}</span>
                <span className="text-muted-foreground">(define a camada)</span>
              </li>
            ))}
            {p.sintomas.map((m, i) => (
              <li key={m} className="fx-fade-up flex items-start gap-1.5 text-muted-foreground" style={{ animationDelay: `${(p.motivos.length + i) * 90}ms` }}>
                <span className="mt-1 size-1.5 shrink-0 rounded-full bg-muted-foreground/50" aria-hidden />
                <span>{m} (sintoma, não define camada)</span>
              </li>
            ))}
          </ul>
        )}
        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-background/60 p-2 text-xs">
          <span className="text-muted-foreground">Fila atual (prioridade manual + data)</span>
          <b className="tabular-nums">#{p.posicao_atual}</b>
          <span className="text-muted-foreground">→ proposta</span>
          <b className="tabular-nums">#{p.posicao}</b>
          <SetaVariacao antiga={p.posicao_atual} nova={p.posicao} />
          <span className="text-muted-foreground tabular-nums">{delta === 0 ? "sem mudança" : delta > 0 ? `subiu ${delta}` : `desceu ${-delta}`}</span>
        </div>
      </div>
    </CartaoGrafico>
  )
}
