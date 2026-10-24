import { useMemo, useState } from "react"
import type { Evento, Paciente } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { formatarData } from "@/lib/datas"

const LIMITE = 8

export type DecisaoHistorico = { id: string; data: string; texto: string }

const RESULTADO: Record<string, Record<string, string>> = {
  biopsia: { positivo: "positiva", negativo: "negativa", inconclusivo: "inconclusiva" },
  exame_imagem: { progressao: "progressão", estavel: "sem mudança", positivo: "alterado", negativo: "sem alteração", inconclusivo: "inconclusivo" },
  consulta_reavaliacao: { piora: "piora", estavel: "estável", alta: "alta", relata_melhora: "relata melhora", relata_piora: "relata piora" },
  contato_telefonico: { atendeu: "atendeu", nao_atendeu: "não atendeu", desistiu: "paciente desistiu", informou_cirurgia_outro_servico: "informou cirurgia em outro serviço" },
}

/** Frase curta em português para um evento, sem códigos. */
export function fraseEvento(e: Evento): string {
  const r = e.resultado ? RESULTADO[e.tipo]?.[e.resultado] : undefined
  switch (e.tipo) {
    case "pronto_socorro":
      return "Atendimento no pronto-socorro"
    case "internacao":
      return e.valor ? `Internação de ${e.valor} ${e.valor === 1 ? "dia" : "dias"}` : "Internação"
    case "biopsia":
      return r ? `Biópsia: ${r}` : "Biópsia"
    case "exame_imagem":
      return r ? `Exame de imagem: ${r}` : "Exame de imagem"
    case "consulta_reavaliacao":
      return r ? `Consulta de reavaliação: ${r}` : "Consulta de reavaliação"
    case "hba1c":
      return e.valor !== null ? `HbA1c: ${String(e.valor).replace(".", ",")}%` : "Exame de HbA1c"
    case "falta":
      return "Falta à consulta"
    case "contato_telefonico":
      return r ? `Contato telefônico: ${r}` : "Contato telefônico"
  }
}

/** Linha do tempo única: eventos do paciente e decisões do regulador, mais recente primeiro. */
export function HistoricoPaciente({ p, decisoes = [], carregando = false }: { p: Paciente; decisoes?: DecisaoHistorico[]; carregando?: boolean }) {
  const [tudo, setTudo] = useState(false)

  const itens = useMemo(() => {
    const evs = p.eventos.map((e) => ({
      id: e.id,
      data: e.data,
      texto: fraseEvento(e) + (e.historico || e.data < p.data_entrada ? " (antes da fila)" : ""),
    }))
    return [...evs, ...decisoes].sort((a, b) => b.data.localeCompare(a.data))
  }, [p.eventos, p.data_entrada, decisoes])

  const visiveis = tudo ? itens : itens.slice(0, LIMITE)

  return (
    <section aria-labelledby="historico" className="space-y-2">
      <h3 id="historico" className="text-sm font-semibold">
        Histórico
      </h3>
      {itens.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhum registro para esta solicitação.</p>
      ) : (
        <ul className="divide-y">
          {visiveis.map((i) => (
            <li key={i.id} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-x-3 py-1.5 text-sm">
              <span className="text-xs leading-5 text-muted-foreground tabular-nums">{formatarData(i.data)}</span>
              <span className="min-w-0 break-words">{i.texto}</span>
            </li>
          ))}
        </ul>
      )}
      {itens.length > LIMITE && (
        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setTudo((v) => !v)}>
          {tudo ? "Ver menos" : `Ver todos (${itens.length})`}
        </Button>
      )}
      {carregando && <p className="text-xs text-muted-foreground">Carregando registros do sistema…</p>}
    </section>
  )
}
