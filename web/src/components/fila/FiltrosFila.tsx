import { useState } from "react"
import { AlertTriangle, FilterX, Search, SlidersHorizontal, TimerOff } from "lucide-react"
import { ESPECIALIDADES } from "@/data/fila"
import { CLASSES } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Toggle } from "@/components/ui/toggle"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { filtrosAtivos, type Filtros, type StatusFiltro } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const TOGGLES: { chave: keyof Filtros; rotulo: string; icone: typeof TimerOff }[] = [
  { chave: "vencidos", rotulo: "Prazo vencido", icone: TimerOff },
  { chave: "alertas", rotulo: "Com alerta", icone: AlertTriangle },
]

const STATUS: [StatusFiltro, string][] = [
  ["todos", "Todos"],
  ["pendentes", "A revisar"],
  ["revisados", "Revisados"],
]

const itensEspecialidade = (): Record<string, string> => Object.fromEntries([["todas", "Todas"], ...ESPECIALIDADES.map((e) => [e, e])])
const ITENS_CAMADA: Record<string, string> = { todas: "Todas", "1": "Oncológicos", "2": "Urgentes", "3": "Demais" }

const ITENS_CLASSE: Record<string, string> = Object.fromEntries([["todas", "Todas"], ...CLASSES.map((c) => [c, `Classe ${c}`])])

export function FiltrosFila({ total, visiveis }: { total: number; visiveis: number }) {
  const ITENS_ESPECIALIDADE = itensEspecialidade()
  const filtros = useStore((s) => s.filtros)
  const setFiltros = useStore((s) => s.setFiltros)
  const limpar = useStore((s) => s.limparFiltros)
  const ativo = filtrosAtivos(filtros)
  const [aberto, setAberto] = useState(false)
  const nAtivos = [filtros.especialidade !== "todas", filtros.classe !== "todas", filtros.camada !== "todas", filtros.oncologicos, filtros.vencidos, filtros.alertas, filtros.subiu].filter(Boolean).length

  const seletor = (itens: Record<string, string>, valor: string, aoMudar: (v: string) => void, rotulo: string) => (
    <label className="flex flex-col gap-1.5 text-sm font-medium">
      {rotulo}
      <Select items={itens} value={valor} onValueChange={(v) => aoMudar(v ?? "todas")}>
        <SelectTrigger className="h-9 w-full" aria-label={rotulo}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(itens).map(([v, r]) => (
            <SelectItem key={v} value={v}>
              {r}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </label>
  )

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-0 flex-1 basis-full sm:basis-56">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input id="busca-fila" value={filtros.busca} onChange={(e) => setFiltros({ busca: e.target.value })} placeholder="Buscar" className="h-9 pl-8" aria-label="Buscar por ID, CID ou procedimento" />
        </div>
        <div role="group" aria-label="Filtrar por situação da revisão" className="flex shrink-0 items-center gap-0.5 rounded-lg bg-muted/60 p-0.5">
          {STATUS.map(([valor, rotulo]) => {
            const ligado = filtros.status === valor
            return (
              <button
                key={valor}
                type="button"
                aria-pressed={ligado}
                onClick={() => setFiltros({ status: valor })}
                className={cn(
                  "h-9 shrink-0 rounded-md px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring sm:h-8",
                  ligado ? "bg-background font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {rotulo}
              </button>
            )
          })}
        </div>
        <Button variant="outline" className="h-9 shrink-0 gap-1.5" aria-label={`Filtros${nAtivos ? `, ${nAtivos} ativos` : ""}`} onClick={() => setAberto(true)}>
          <SlidersHorizontal aria-hidden />
          Filtros
          {nAtivos > 0 && <span className="rounded bg-primary/15 px-1.5 text-xs tabular-nums text-primary">{nAtivos}</span>}
        </Button>
        {ativo && (
          <div className="flex shrink-0 items-center gap-1 text-xs text-muted-foreground">
            <span className="tabular-nums">
              {visiveis} de {total}
            </span>
            <Button size="xs" variant="ghost" onClick={limpar} className="h-9 gap-1 sm:h-7" aria-label="Limpar filtros">
              <FilterX className="size-3" aria-hidden />
              Limpar
            </Button>
          </div>
        )}
      </div>

      <Sheet open={aberto} onOpenChange={setAberto}>
        <SheetContent side="right" className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Filtros</SheetTitle>
          </SheetHeader>
          <div className="flex flex-col gap-4 px-4 pb-4">
            {seletor(ITENS_CAMADA, filtros.camada, (v) => setFiltros({ camada: v }), "Prioridade")}
            {seletor(ITENS_CLASSE, filtros.classe, (v) => setFiltros({ classe: v }), "Classe")}
            {seletor(ITENS_ESPECIALIDADE, filtros.especialidade, (v) => setFiltros({ especialidade: v }), "Especialidade")}
            <div className="flex flex-wrap gap-2">
              {TOGGLES.map(({ chave, rotulo, icone: Icone }) => (
                <Toggle key={chave} variant="default" pressed={filtros[chave] as boolean} onPressedChange={(v) => setFiltros({ [chave]: v })} className="h-9 gap-1 px-3 text-sm data-[pressed]:bg-primary/12 data-[pressed]:text-primary">
                  <Icone aria-hidden />
                  {rotulo}
                </Toggle>
              ))}
            </div>
            {ativo && (
              <Button variant="outline" onClick={limpar} className="h-9 gap-1">
                <FilterX aria-hidden /> Limpar filtros
              </Button>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
