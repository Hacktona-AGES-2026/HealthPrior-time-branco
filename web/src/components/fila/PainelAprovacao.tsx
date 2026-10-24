import { useMemo } from "react"
import { ExternalLink, MousePointerClick, PanelRightClose, PanelRightOpen, Scale } from "lucide-react"
import { PACIENTES, PACIENTE_POR_ID } from "@/data/fila"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
import { NovoEvento } from "@/components/shared/NovoEvento"
import { AlertaRevisao, CamadaBadge, MudancaClasse, PrazoBar, SetaVariacao } from "@/components/shared/Basicos"
import { cn } from "@/lib/utils"
import { useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

export function PainelAprovacao({ className, modo = "lateral" }: { className?: string; modo?: "lateral" | "drawer" }) {
  const selecionadoId = useStore((s) => s.selecionadoId)
  const decisoes = useStore((s) => s.decisoes)
  const abrirFicha = useStore((s) => s.abrirFicha)
  const largura = useColunas((c) => c.painel)
  const oculto = useColunas((c) => c.painelOculto)
  const setOculto = useColunas((c) => c.setPainelOculto)
  const p = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined
  const revisados = useMemo(() => PACIENTES.filter((x) => decisoes[x.id]).length, [decisoes])

  if (oculto && modo === "lateral") {
    return (
      <aside className={cn("fx-fade-up flex w-11 shrink-0 flex-col items-center gap-3 border-l py-3", className)} aria-label="Painel de aprovação recolhido">
        <Button variant="ghost" size="icon-sm" onClick={() => setOculto(false)} title="Mostrar painel de aprovação (])" aria-label="Mostrar painel de aprovação">
          <PanelRightOpen aria-hidden />
        </Button>
        <span className="text-[11px] text-muted-foreground tabular-nums [writing-mode:vertical-rl]">
          {revisados} de {PACIENTES.length} revisados
        </span>
        <span className="relative h-24 w-1 overflow-hidden rounded-full bg-muted" aria-hidden>
          <span className="absolute inset-x-0 bottom-0 rounded-full bg-primary/60 transition-all" style={{ height: `${(revisados / PACIENTES.length) * 100}%` }} />
        </span>
      </aside>
    )
  }

  const conteudo = (
      <div className="space-y-3 p-3">
        <div className="px-1">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground tabular-nums">
              {revisados} de {PACIENTES.length} revisados
            </span>
            <span className="flex items-center gap-1 text-xs text-muted-foreground tabular-nums">
              {Math.round((revisados / PACIENTES.length) * 100)}%
              {modo === "lateral" && (
                <Button variant="ghost" size="icon-xs" onClick={() => setOculto(true)} title="Ocultar painel de aprovação (])" aria-label="Ocultar painel de aprovação">
                  <PanelRightClose aria-hidden />
                </Button>
              )}
            </span>
          </div>
          <Progress value={(revisados / PACIENTES.length) * 100} className="mt-2 h-1" aria-label="Progresso da revisão" />
        </div>

        {!p ? (
          <div className="fx-fade-up flex flex-col items-center gap-3 rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            <MousePointerClick className="size-8 animate-bounce" aria-hidden />
            <p className="font-medium text-foreground">Nenhum caso selecionado</p>
            <p>Clique em uma barra da faixa, em uma linha da tabela ou use J/K para navegar pelos pendentes.</p>
          </div>
        ) : (
          <div key={p.id} className="fx-fade-up space-y-3">
            <div className="space-y-2.5 rounded-xl bg-muted/40 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-bold tabular-nums">{p.id}</div>
                  <div className="text-xs text-muted-foreground">
                    {p.iniciais} · {p.idade} anos · {p.sexo === "F" ? "feminino" : "masculino"} · {p.municipio}
                  </div>
                </div>
                <AlertaRevisao paciente={p} />
              </div>
              <div className="text-sm font-medium">{p.procedimento}</div>
              <div className="text-xs text-muted-foreground">
                <span className="font-semibold text-foreground">{p.cid}</span> · {p.cid_descricao}
              </div>
              <Separator />
              <dl className="grid grid-cols-2 gap-x-3 gap-y-2.5 text-xs">
                <div>
                  <dt className="text-muted-foreground">Classe</dt>
                  <dd className="mt-1">
                    <MudancaClasse de={p.prioridade_atual} para={p.classe} />
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Posição atual → proposta</dt>
                  <dd className="mt-1 flex items-center gap-1.5 font-semibold tabular-nums">
                    {p.posicao_atual} → {p.posicao}
                    <SetaVariacao antiga={p.posicao_atual} nova={p.posicao} />
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-muted-foreground">Prazo consumido</dt>
                  <dd className="mt-1">
                    <PrazoBar pct={p.pct} />
                  </dd>
                </div>
                <div className="col-span-2 flex items-center justify-between">
                  <dt className="text-muted-foreground">Camada</dt>
                  <dd>
                    <CamadaBadge camada={p.camada} />
                  </dd>
                </div>
              </dl>
              <Separator />
              <p className="text-xs leading-relaxed text-muted-foreground">{p.justificativa}</p>
              {p.alertas.length > 0 && (
                <div>
                  <div className="mb-1 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                    <Scale className="size-3" aria-hidden /> Alertas
                  </div>
                  <ul className="space-y-0.5 text-xs text-muted-foreground">
                    {p.alertas.map((a) => (
                      <li key={a}>• {a}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            <AcoesDecisao paciente={p} />
            <NovoEvento solicitacaoId={p.id} />
            <Button variant="outline" size="sm" className="w-full gap-1.5" onClick={() => abrirFicha(p.id)}>
              <ExternalLink aria-hidden /> Ver ficha completa
            </Button>
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
