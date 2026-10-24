import type { Paciente } from "@/data/tipos"
import { formatarData } from "@/lib/datas"
import { CartaoGrafico } from "./Cartao"
import { COR_EVENTO, ICONE_EVENTO, ROTULO_EVENTO_TIPO } from "./IconesEvento"

export function LinhaTempoEventos({ p }: { p: Paciente }) {
  return (
    <CartaoGrafico titulo="Linha do tempo da espera" descricao={`${p.eventos.length} eventos desde a entrada na fila`}>
      <ol className="relative max-h-60 space-y-3 overflow-y-auto pr-1 pl-1">
        <span className="fx-grow-y absolute top-2 bottom-2 left-[15px] w-px bg-border" style={{ transformOrigin: "center top", animationDuration: "1.1s" }} aria-hidden />
        {p.eventos.map((e, i) => {
          const Icone = ICONE_EVENTO[e.tipo]
          return (
            <li key={`${e.data}-${i}`} className="fx-fade-up relative flex gap-3" style={{ animationDelay: `${i * 90}ms` }}>
              <span className="relative z-10 flex size-[30px] shrink-0 items-center justify-center rounded-full border bg-card" style={{ borderColor: COR_EVENTO[e.tipo], color: COR_EVENTO[e.tipo] }}>
                <Icone className="size-3.5" aria-hidden />
              </span>
              <div className="min-w-0 pt-0.5">
                <div className="flex items-baseline gap-2 text-xs">
                  <span className="font-semibold">{ROTULO_EVENTO_TIPO[e.tipo]}</span>
                  <time className="text-muted-foreground tabular-nums" dateTime={e.data}>
                    {formatarData(e.data)}
                  </time>
                </div>
                <p className="text-xs leading-snug text-muted-foreground">{e.descricao}</p>
              </div>
            </li>
          )
        })}
      </ol>
    </CartaoGrafico>
  )
}
