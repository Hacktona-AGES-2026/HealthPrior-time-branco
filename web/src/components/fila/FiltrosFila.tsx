import { useMemo } from "react"
import { AlertTriangle, FilterX, MoveVertical, Ribbon, Search, TimerOff } from "lucide-react"
import { ESPECIALIDADES } from "@/data/fila"
import { CLASSES } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Toggle } from "@/components/ui/toggle"
import { FILTROS_VAZIOS, type Filtros, type StatusFiltro } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const TOGGLES: { chave: keyof Filtros; rotulo: string; icone: typeof Ribbon }[] = [
  { chave: "oncologicos", rotulo: "Oncológicos", icone: Ribbon },
  { chave: "vencidos", rotulo: "Vencidos", icone: TimerOff },
  { chave: "mudou", rotulo: "Mudou de posição", icone: MoveVertical },
  { chave: "divergencia", rotulo: "Divergência / revisar", icone: AlertTriangle },
]

const STATUS: [StatusFiltro, string][] = [
  ["todos", "Todos"],
  ["pendentes", "Pendentes"],
  ["revisados", "Revisados"],
  ["aprovados", "Aprovados"],
  ["rejeitados", "Rejeitados"],
]

const itensEspecialidade = (): Record<string, string> => Object.fromEntries([["todas", "Todas as especialidades"], ...ESPECIALIDADES.map((e) => [e, e])])
const ITENS_CLASSE: Record<string, string> = Object.fromEntries([["todas", "Todas as classes"], ...CLASSES.map((c) => [c, `Classe ${c}`])])

export function FiltrosFila({ total, visiveis }: { total: number; visiveis: number }) {
  const ITENS_ESPECIALIDADE = itensEspecialidade()
  const filtros = useStore((s) => s.filtros)
  const setFiltros = useStore((s) => s.setFiltros)
  const limpar = useStore((s) => s.limparFiltros)
  const decisoes = useStore((s) => s.decisoes)
  const ativo = JSON.stringify(filtros) !== JSON.stringify(FILTROS_VAZIOS)
  const contagem = useMemo(() => {
    const valores = Object.values(decisoes)
    const aprovados = valores.filter((d) => d.status === "aprovado").length
    const rejeitados = valores.filter((d) => d.status === "rejeitado").length
    return { todos: total, pendentes: total - aprovados - rejeitados, revisados: aprovados + rejeitados, aprovados, rejeitados }
  }, [decisoes, total])

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="relative min-w-48 flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input value={filtros.busca} onChange={(e) => setFiltros({ busca: e.target.value })} placeholder="Buscar ID, CID ou procedimento" className="h-8 pl-8" aria-label="Buscar por ID, CID ou procedimento" />
      </div>
      <Select items={ITENS_ESPECIALIDADE} value={filtros.especialidade} onValueChange={(v) => setFiltros({ especialidade: v ?? "todas" })}>
        <SelectTrigger size="sm" className="w-44" aria-label="Filtrar por especialidade">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(ITENS_ESPECIALIDADE).map(([valor, rotulo]) => (
            <SelectItem key={valor} value={valor}>
              {rotulo}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select items={ITENS_CLASSE} value={filtros.classe} onValueChange={(v) => setFiltros({ classe: v ?? "todas" })}>
        <SelectTrigger size="sm" className="w-36" aria-label="Filtrar por classe">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(ITENS_CLASSE).map(([valor, rotulo]) => (
            <SelectItem key={valor} value={valor}>
              {rotulo}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {TOGGLES.map(({ chave, rotulo, icone: Icone }) => (
        <Toggle key={chave} size="sm" variant="outline" pressed={filtros[chave] as boolean} onPressedChange={(v) => setFiltros({ [chave]: v })} className="gap-1 data-[pressed]:border-primary data-[pressed]:bg-primary/10 data-[pressed]:text-primary">
          <Icone aria-hidden />
          {rotulo}
        </Toggle>
      ))}
      <div role="group" aria-label="Filtrar por status da revisão" className="flex w-full items-center gap-0.5 rounded-lg bg-muted/60 p-0.5">
        {STATUS.map(([valor, rotulo]) => {
          const ligado = filtros.status === valor
          return (
            <button
              key={valor}
              type="button"
              aria-pressed={ligado}
              onClick={() => setFiltros({ status: valor })}
              className={cn(
                "flex-1 rounded-md px-2 py-1 text-xs transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring",
                ligado ? "bg-background font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"
              )}
            >
              {rotulo} <span className="tabular-nums opacity-60">{contagem[valor]}</span>
            </button>
          )
        })}
      </div>
      <span className="ml-auto text-xs text-muted-foreground tabular-nums">
        {visiveis} de {total}
      </span>
      {ativo && (
        <Button size="xs" variant="ghost" onClick={limpar} className="fx-pop gap-1">
          <FilterX className="size-3" aria-hidden />
          Limpar
        </Button>
      )}
    </div>
  )
}
