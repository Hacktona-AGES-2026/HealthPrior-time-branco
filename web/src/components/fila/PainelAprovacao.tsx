import { ExternalLink, PanelRightClose, PanelRightOpen, TriangleAlert } from "lucide-react"
import { PACIENTE_POR_ID } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
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
    if (Number(dor[1]) > 0) frases.push(`Dor ${dor[1]}/10`)
    const lim = t.match(/limitação (leve|moderada|grave)/i)
    if (lim) frases.push(`Limitação ${lim[1].toLowerCase()}`)
    return frases
  }
  const lf = t.match(/^limitação funcional (\w+)/i)
  if (lf) return lf[1] === "nenhuma" ? [] : [`Limitação ${lf[1]}`]
  if (/piora durante a espera/i.test(t)) return ["Piorou na espera"]
  if (/sinal de alarme/i.test(t)) return ["Sinal de alarme"]
  if (/biópsia positiva com CID não oncológico/i.test(t)) return ["Biópsia positiva; conferir CID"]
  const neo = t.match(/neoplasia maligna pelo CID (\S+)/i)
  if (neo) return ["Câncer confirmado"]
  if (/^biópsia positiva/i.test(t)) return ["Biópsia positiva"]
  if (/dor não informada/i.test(t)) return ["Dor não informada"]
  return [t.charAt(0).toUpperCase() + t.slice(1)]
}

function motivosClinicos(p: Paciente): string[] {
  const todos = [...p.motivos, ...p.sintomas].flatMap(traduzir)
  const lista = [...(p.oncologico && !todos.some((f) => f.startsWith("Câncer")) ? ["Oncológico"] : []), ...todos]
  return [...new Set(lista)].slice(0, 3)
}

function linhaDados(p: Paciente): string {
  const pos = p.posicao_atual !== p.posicao ? `Posição ${p.posicao} (era ${p.posicao_atual})` : `Posição ${p.posicao}`
  return `${pos} · ${formatarPct(p.pct)} do prazo · ${p.dias_em_fila} dias`
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
        <Button variant="ghost" size="icon-sm" onClick={() => setOculto(false)} title="Mostrar painel (])" aria-label="Mostrar painel de aprovação">
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
          <p className="text-sm text-muted-foreground">Selecione um paciente.</p>
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
                <span className="font-semibold text-foreground">{p.iniciais}</span> · {p.idade} anos · {p.sexo}
              </div>
              {modo === "lateral" && (
                <Button variant="ghost" size="icon-sm" className="-mt-1 -mr-1 shrink-0 max-md:size-9" onClick={() => setOculto(true)} title="Ocultar painel (])" aria-label="Ocultar painel de aprovação">
                  <PanelRightClose aria-hidden />
                </Button>
              )}
            </div>
            <div className="text-sm font-bold">{p.procedimento}</div>
            <div className="text-xs text-muted-foreground">
              CID {p.cid}
              {p.cid_descricao && ` — ${p.cid_descricao}`}
            </div>
          </section>

          <Separator />
          <section aria-labelledby="motivo" className="space-y-1">
            <h3 id="motivo" className="text-xs font-semibold text-muted-foreground">
              Motivo
            </h3>
            {motivos.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-4 text-sm">
                {motivos.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            )}
            <p className="text-xs text-muted-foreground tabular-nums">{linhaDados(p)}</p>
          </section>

          {p.alertas.length > 0 && (
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <span>{p.alertas.join(" · ")}</span>
            </p>
          )}

          <Separator />
          <section aria-label="Decisão" className="space-y-2">
            <AcoesDecisao paciente={p} />
            <Button variant="outline" className="h-9 w-full gap-1.5" onClick={() => abrirFicha(p.id)}>
              <ExternalLink aria-hidden /> Ver ficha completa
            </Button>
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
