import type { Paciente } from "@/data/tipos"
import { cn } from "@/lib/utils"
import { useDetalheApi } from "./DetalheApi"

const numero = (n: number, casas = 0) => n.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas })

type Fator = { valor: number; explicacao: string }

/** O back registra cada fator como "<explicação> → ×1,03"; aqui separamos o número do texto. */
function lerFator(motivos: { sinal: string; evidencia: string }[], sinal: string): Fator | null {
  const m = motivos.find((x) => x.sinal === sinal)
  const r = m?.evidencia.match(/^(.*?)\s*→\s*×\s*(\d+(?:[.,]\d+)?)/)
  if (!r) return null
  return { valor: Number(r[2].replace(",", ".")), explicacao: r[1].trim() }
}

const claroComorbidade = (t: string) => t.replace(/\(texto:([^)]+)\)/, "($1)")
const claroIdade = (t: string) => t.replace(/^[A-Z]\d+\s+(\d+-\d+):\s*/, "faixa de $1 anos: ")

function Linha({ operador, valor, titulo, detalhe, total = false }: { operador?: string; valor: string; titulo: string; detalhe?: string; total?: boolean }) {
  return (
    <li className={cn("grid grid-cols-[6.5rem_minmax(0,1fr)] items-baseline gap-x-3 py-1.5 sm:grid-cols-[8rem_minmax(0,1fr)]", total && "border-t pt-2.5")}>
      <span className={cn("text-right tabular-nums", total ? "text-lg font-semibold" : "text-base font-medium")}>
        {operador && <span className="mr-1.5 font-normal text-muted-foreground">{operador}</span>}
        {valor}
      </span>
      <span className="min-w-0 text-sm">
        <span className={cn(total && "font-semibold")}>{titulo}</span>
        {detalhe && <span className="block text-xs text-muted-foreground">{detalhe}</span>}
      </span>
    </li>
  )
}

/** A conta da pontuação que ordena a fila: % do prazo × comorbidade × idade. Só com a API (o cálculo é do servidor). */
export function CalculoScore({ p }: { p: Paciente }) {
  const { d } = useDetalheApi(p.id)
  const s = d?.score
  if (!d || !s || s.pct_prazo_consumido == null || s.score_efetivo == null) return null

  const comorbidade = lerFator(s.motivos, "fator_comorbidade")
  const idade = lerFator(s.motivos, "fator_idade")
  const prazo = s.prazo_dias ?? undefined
  const ajustado = s.score_medico != null && s.score_sistema != null && s.score_medico !== s.score_sistema
  const bloco = p.camada === 3 ? "dos demais pacientes" : "prioritário (câncer e urgências)"

  return (
    <section aria-labelledby="calculo-score" className="space-y-2">
      <h3 id="calculo-score" className="text-sm font-semibold">
        Como a pontuação foi calculada
      </h3>
      <ul>
        <Linha
          valor={`${numero(s.pct_prazo_consumido)}%`}
          titulo="do prazo consumido"
          detalhe={prazo ? `${numero(p.dias_em_fila)} dias de espera para um prazo de ${numero(prazo)} dias` : undefined}
        />
        {comorbidade && <Linha operador="×" valor={numero(comorbidade.valor, 2)} titulo="comorbidades" detalhe={claroComorbidade(comorbidade.explicacao)} />}
        {idade && <Linha operador="×" valor={numero(idade.valor, 2)} titulo="idade" detalhe={claroIdade(idade.explicacao)} />}
        <Linha operador="=" valor={numero(s.score_sistema ?? s.score_efetivo)} titulo="pontuação" total />
      </ul>
      {ajustado && (
        <p className="text-sm">
          O regulador ajustou a pontuação para <b>{numero(s.score_medico!)}</b>.
        </p>
      )}
      <p className="text-xs text-muted-foreground">
        Os fatores vão de ×1,00 a ×1,15 e nunca reduzem a pontuação. No bloco {bloco}, a fila segue da maior pontuação para a menor
        {p.posicao ? `: este paciente está na posição ${numero(p.posicao)}` : ""}.
      </p>
    </section>
  )
}
