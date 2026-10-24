import { ExternalLink, PanelRightClose, PanelRightOpen } from "lucide-react"
import { PACIENTE_POR_ID } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
import { NovoEvento } from "@/components/shared/NovoEvento"
import { formatarPct } from "@/components/shared/Basicos"
import { cn } from "@/lib/utils"
import { useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

/** Traduz os motivos internos para frases de consultório. Retorna null para o que não ajuda a decidir. */
function traduzir(texto: string): string[] {
  const t = texto.trim()
  if (/^nenhum risco/i.test(t)) return []
  const frases: string[] = []
  const dor = t.match(/^dor EVA (\d+)/i)
  if (dor) {
    if (Number(dor[1]) > 0) frases.push(`Dor de intensidade ${dor[1]} em 10`)
    const lim = t.match(/limitação (leve|moderada|grave)/i)
    if (lim) frases.push(`Limitação nas atividades: ${lim[1].toLowerCase()}`)
    return frases
  }
  const lf = t.match(/^limitação funcional (\w+)/i)
  if (lf) return lf[1] === "nenhuma" ? [] : [`Limitação nas atividades: ${lf[1]}`]
  if (/piora durante a espera/i.test(t)) return ["Piorou durante a espera"]
  if (/sinal de alarme/i.test(t)) return ["Sinal de alarme descrito no encaminhamento"]
  if (/biópsia positiva com CID não oncológico/i.test(t)) return ["Biópsia positiva, mas o CID não é oncológico (conferir)"]
  const neo = t.match(/neoplasia maligna pelo CID (\S+)/i)
  if (neo) return [`Neoplasia maligna (CID ${neo[1]})`]
  if (/^biópsia positiva/i.test(t)) return ["Biópsia positiva"]
  if (/dor não informada/i.test(t)) return ["Dor não informada"]
  return [t.charAt(0).toUpperCase() + t.slice(1)]
}

function motivosClinicos(p: Paciente): string[] {
  const todos = [...p.motivos, ...p.sintomas].flatMap(traduzir)
  const lista = [...(p.oncologico && !todos.some((f) => f.startsWith("Neoplasia")) ? ["Caso oncológico"] : []), ...todos]
  return [...new Set(lista)].slice(0, 4)
}

function fraseDaPosicao(p: Paciente): string {
  const prioridade =
    p.camada === 1 ? "Prioridade alta por ser oncológico" : p.camada === 2 ? "Prioridade elevada por sinais de urgência" : `Ordenado pela classe ${p.classe} e pelo tempo de espera`
  const prazo = p.pct >= 100 ? `o prazo já foi ultrapassado (${formatarPct(p.pct)})` : `já usou ${formatarPct(p.pct)} do prazo`
  const base = `${prioridade}; ${prazo} (${p.dias_em_fila} ${p.dias_em_fila === 1 ? "dia" : "dias"} em fila).`
  if (p.posicao < p.posicao_atual) return `${base} Subiu da posição ${p.posicao_atual} para ${p.posicao}.`
  if (p.posicao > p.posicao_atual) return `${base} Desceu da posição ${p.posicao_atual} para ${p.posicao}.`
  return `${base} Mantém a posição ${p.posicao}.`
}

export function PainelAprovacao({ className, modo = "lateral" }: { className?: string; modo?: "lateral" | "drawer" }) {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const abrirFicha = useStore((s) => s.abrirFicha)
  const largura = useColunas((c) => c.painel)
  const oculto = useColunas((c) => c.painelOculto)
  const setOculto = useColunas((c) => c.setPainelOculto)
  const p = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  if (oculto && modo === "lateral") {
    return (
      <aside className={cn("flex w-11 shrink-0 flex-col items-center border-l py-3", className)} aria-label="Painel de aprovação recolhido">
        <Button variant="ghost" size="icon-sm" onClick={() => setOculto(false)} title="Mostrar detalhes do paciente (])" aria-label="Mostrar painel de aprovação">
          <PanelRightOpen aria-hidden />
        </Button>
      </aside>
    )
  }

  const motivos = p ? motivosClinicos(p) : []

  const conteudo = (
    <div className="p-4">
      {!p ? (
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-muted-foreground">Selecione um paciente na lista para ver os detalhes.</p>
          {modo === "lateral" && (
            <Button variant="ghost" size="icon-sm" className="-mt-1 -mr-1 shrink-0 max-md:size-9" onClick={() => setOculto(true)} title="Ocultar painel (])" aria-label="Ocultar painel de aprovação">
              <PanelRightClose aria-hidden />
            </Button>
          )}
        </div>
      ) : (
        <div key={p.id} className="space-y-4">
          <section aria-label="Identificação" className="space-y-1">
            <div className="flex items-start justify-between gap-2">
              <div className="text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">{p.iniciais}</span> · {p.idade} anos · {p.sexo === "F" ? "feminino" : "masculino"} · {p.municipio}
              </div>
              {modo === "lateral" && (
                <Button variant="ghost" size="icon-sm" className="-mt-1 -mr-1 shrink-0 max-md:size-9" onClick={() => setOculto(true)} title="Ocultar painel (])" aria-label="Ocultar painel de aprovação">
                  <PanelRightClose aria-hidden />
                </Button>
              )}
            </div>
            <div className="text-sm font-bold">{p.procedimento}</div>
            <div className="text-xs text-muted-foreground">
              {p.cid}
              {p.cid_descricao && ` · ${p.cid_descricao}`}
            </div>
          </section>

          {motivos.length > 0 && (
            <>
              <Separator />
              <section aria-labelledby="pq-fila" className="space-y-1.5">
                <h3 id="pq-fila" className="text-xs font-semibold text-muted-foreground">
                  Por que está na fila
                </h3>
                <ul className="list-disc space-y-0.5 pl-4 text-sm">
                  {motivos.map((m) => (
                    <li key={m}>{m}</li>
                  ))}
                </ul>
              </section>
            </>
          )}

          <Separator />
          <section aria-labelledby="pq-posicao" className="space-y-1.5">
            <h3 id="pq-posicao" className="text-xs font-semibold text-muted-foreground">
              Por que está na posição {p.posicao}
            </h3>
            <p className="text-sm">{fraseDaPosicao(p)}</p>
          </section>

          {p.alertas.length > 0 && (
            <>
              <Separator />
              <ul className="list-disc space-y-0.5 pl-4 text-sm text-muted-foreground">
                {p.alertas.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </>
          )}

          <Separator />
          <section aria-label="Decisão" className="space-y-2">
            <AcoesDecisao paciente={p} />
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <NovoEvento solicitacaoId={p.id} />
              <Button variant="link" size="sm" className="h-9 gap-1.5 px-0 text-muted-foreground" onClick={() => abrirFicha(p.id)}>
                <ExternalLink aria-hidden /> Ver ficha completa
              </Button>
            </div>
          </section>
        </div>
      )}
    </div>
  )

  if (modo === "drawer") return conteudo

  return (
    <aside className={cn("flex shrink-0 flex-col overflow-y-auto border-l", className)} style={{ width: largura }} aria-label="Painel de aprovação">
      {conteudo}
    </aside>
  )
}
