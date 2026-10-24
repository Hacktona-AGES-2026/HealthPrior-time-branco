import type { ReactNode } from "react"
import type { Paciente } from "@/data/tipos"
import { formatarData } from "@/lib/datas"

function Linha({ rotulo, children }: { rotulo: string; children: ReactNode }) {
  return (
    <div className="grid grid-cols-[8.5rem_minmax(0,1fr)] gap-x-3">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="min-w-0 break-words text-sm">{children}</dd>
    </div>
  )
}

/** Dados do pedido que o cabeçalho da ficha não mostra. */
export function DadosPedido({ p }: { p: Paciente }) {
  return (
    <section aria-labelledby="pedido" className="space-y-2">
      <h3 id="pedido" className="text-sm font-semibold">
        Dados do pedido
      </h3>
      <dl className="space-y-2">
        <Linha rotulo="Solicitação">{p.id}</Linha>
        <Linha rotulo="Entrada na fila">{formatarData(p.data_entrada)}</Linha>
        <Linha rotulo="Município">
          {p.municipio} · {p.uf}
          {p.distancia_km !== null && <span className="text-muted-foreground"> · {p.distancia_km} km do hospital</span>}
        </Linha>
      </dl>
    </section>
  )
}
