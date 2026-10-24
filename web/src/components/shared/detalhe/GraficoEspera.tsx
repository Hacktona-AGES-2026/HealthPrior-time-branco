import { useMemo } from "react"
import type { Paciente } from "@/data/tipos"
import { PRAZO_MAX } from "@/lib/cores"
import { addDias, diffDias, formatarData } from "@/lib/datas"
import { ROTULO_EVENTO_TIPO } from "./IconesEvento"

const PIORA = ["pronto_socorro", "internacao"]
const COR_DENTRO = "var(--primary)"
const COR_ATRASO = "var(--prazo-vencido)"

const fmtDias = (n: number) => `${n.toLocaleString("pt-BR")} ${n === 1 ? "dia" : "dias"}`

/**
 * Linha do tempo da espera: entrada → prazo → hoje, com os eventos como pontos.
 * Não usa escala em %: quando a espera passa muito do prazo (ex.: 1.318 dias para 21), a curva
 * achata o prazo no chão do gráfico e os rótulos se sobrepõem.
 */
export function GraficoEspera({ p }: { p: Paciente }) {
  const prazo = PRAZO_MAX[p.classe]
  const dias = p.dias_em_fila
  const total = Math.max(dias, prazo, 1)
  const pos = (d: number) => `${(Math.min(Math.max(d, 0), total) / total) * 100}%`

  const eventos = useMemo(
    () =>
      p.eventos
        .filter((e) => !e.historico)
        .map((e) => ({ dia: diffDias(p.data_entrada, e.data), data: e.data, tipo: e.tipo }))
        .filter((e) => e.dia >= 0 && e.dia <= dias)
        .map((e) => ({ ...e, rotulo: ROTULO_EVENTO_TIPO[e.tipo], piora: PIORA.includes(e.tipo) })),
    [p, dias]
  )

  const dataPrazo = addDias(p.data_entrada, prazo)
  const dataHoje = addDias(p.data_entrada, dias)
  const atraso = dias - prazo
  const frase =
    atraso > 0
      ? `Aguarda há ${fmtDias(dias)}. O prazo de ${fmtDias(prazo)} venceu em ${formatarData(dataPrazo)}, há ${fmtDias(atraso)}.`
      : `Aguarda há ${fmtDias(dias)}. Faltam ${fmtDias(prazo - dias)} para o prazo de ${fmtDias(prazo)}.`

  const prazoNaDireita = prazo / total > 0.6
  const hojeNaDireita = dias / total > 0.6
  // Hoje perto da entrada: o rótulo da entrada desce para a linha de baixo, onde só há o prazo (à direita).
  const entradaEmbaixo = dias / total < 0.3 && prazoNaDireita

  return (
    <div className="space-y-2">
      <p className="text-sm">{frase}</p>

      <div role="img" aria-label={frase} className="pt-1">
        <div className="relative h-4 text-xs text-muted-foreground tabular-nums">
          {!entradaEmbaixo && <span className="absolute left-0 top-0 whitespace-nowrap">Entrada {formatarData(p.data_entrada)}</span>}
          <span
            className="absolute top-0 whitespace-nowrap"
            style={hojeNaDireita ? { right: `calc(100% - ${pos(dias)})` } : { left: pos(dias) }}
          >
            Hoje {formatarData(dataHoje)}
          </span>
        </div>

        <div className="relative my-1.5 h-4">
          <div className="absolute inset-x-0 top-1/2 h-1.5 -translate-y-1/2 rounded-full bg-muted" />
          <div
            className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-full"
            style={{ left: 0, width: pos(Math.min(dias, prazo)), background: COR_DENTRO }}
          />
          {atraso > 0 && (
            <div
              className="absolute top-1/2 h-1.5 -translate-y-1/2 rounded-r-full"
              style={{ left: pos(prazo), width: `calc(${pos(dias)} - ${pos(prazo)})`, background: COR_ATRASO }}
            />
          )}
          <span className="absolute top-0.5 h-3 w-0.5 -translate-x-1/2 rounded-full bg-foreground" style={{ left: pos(prazo) }} aria-hidden />
          <span className="absolute top-0 h-4 w-0.5 -translate-x-1/2 rounded-full bg-primary" style={{ left: pos(dias) }} aria-hidden />
          {eventos.map((e, i) => (
            <span
              key={`${e.data}-${e.tipo}-${i}`}
              className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-background"
              style={{ left: pos(e.dia), background: e.piora ? COR_ATRASO : "var(--foreground)" }}
              title={`${formatarData(e.data)} — ${e.rotulo}`}
            />
          ))}
        </div>

        <div className="relative h-4 text-xs text-muted-foreground tabular-nums">
          {entradaEmbaixo && <span className="absolute left-0 top-0 whitespace-nowrap">Entrada {formatarData(p.data_entrada)}</span>}
          <span
            className="absolute top-0 whitespace-nowrap"
            style={prazoNaDireita ? { right: `calc(100% - ${pos(prazo)})` } : { left: pos(prazo) }}
          >
            Prazo {formatarData(dataPrazo)}
          </span>
        </div>
      </div>

      {eventos.length > 0 && (
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: COR_ATRASO }} aria-hidden />
            Pronto-socorro ou internação
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-foreground" aria-hidden />
            Outros eventos
          </span>
        </p>
      )}
    </div>
  )
}
