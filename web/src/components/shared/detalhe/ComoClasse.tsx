import type { Paciente } from "@/data/tipos"
import { PRAZO_MAX } from "@/lib/cores"
import { limparJargao, motivoClaro } from "@/lib/regrasSwalis"
import { ClasseBadge } from "@/components/shared/Basicos"
import { useStore } from "@/store/useStore"
import { useDetalheApi } from "./DetalheApi"

type Criterio = { nivel: number; motivos: string[] }

function Linha({ nome, c }: { nome: string; c: Criterio }) {
  const motivos = c.nivel > 0 ? c.motivos.slice(0, 2).map(motivoClaro).filter(Boolean) : []
  return (
    <li>
      <span className="font-medium">{nome}:</span> {c.nivel > 0 ? `nível ${c.nivel}${motivos.length ? ` — ${motivos.join("; ")}` : ""}` : "sem sinais"}
    </li>
  )
}

/** Os critérios vêm do SWALIS ao vivo (detalhe da API); o instantâneo do paciente só serve sem API. */
function criteriosAoVivo(motivos: { sinal: string; evidencia: string }[] | undefined): { progressao: Criterio; sintoma: Criterio } | null {
  if (!motivos) return null
  const ler = (sinal: string): Criterio | null => {
    const m = motivos.find((x) => x.sinal === sinal)
    const r = m?.evidencia.match(/^\s*(?:progress[ãa]o|sintoma)\s+(\d+)\s*:\s*(.*)$/i)
    if (!r) return null
    const nivel = Number(r[1])
    return { nivel, motivos: nivel > 0 ? limparJargao(r[2]).split(/;\s+/).filter(Boolean) : [] }
  }
  const progressao = ler("eixo_progressao")
  const sintoma = ler("eixo_sintoma")
  return progressao && sintoma ? { progressao, sintoma } : null
}

export function ComoClasse({ p }: { p: Paciente }) {
  const abrirSwalis = useStore((s) => s.abrirSwalis)
  const { d } = useDetalheApi(p.id)
  const criterios = criteriosAoVivo(d?.score.motivos) ?? p.eixos
  return (
    <section aria-labelledby="como-classe" className="space-y-2">
      <h3 id="como-classe" className="text-sm font-semibold">
        Como a classe foi definida
      </h3>
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <ClasseBadge classe={p.classe} /> <span>Classe {p.classe} · prazo máximo de {PRAZO_MAX[p.classe]} dias</span>
      </p>
      <ul className="space-y-0.5 text-sm">
        <Linha nome="Progressão da doença" c={criterios.progressao} />
        <Linha nome="Sintomas" c={criterios.sintoma} />
      </ul>
      <button type="button" onClick={() => abrirSwalis(p)} className="inline-flex min-h-9 items-center text-sm text-primary underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-ring">
        Ver todas as classes e prazos
      </button>
    </section>
  )
}
