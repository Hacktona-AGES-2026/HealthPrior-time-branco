import { useMemo, useState } from "react"
import { AlertTriangle, FilterX, MoveUp, Ribbon, Search, SlidersHorizontal, TimerOff } from "lucide-react"
import { toast } from "sonner"
import { ESPECIALIDADES, PACIENTE_POR_ID } from "@/data/fila"
import { MenuColunas } from "./MenuColunas"
import { CLASSES } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Toggle } from "@/components/ui/toggle"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { filtrosAtivos, type Filtros, type StatusFiltro } from "@/lib/filtros"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const TOGGLES: { chave: keyof Filtros; rotulo: string; icone: typeof Ribbon }[] = [
  { chave: "oncologicos", rotulo: "Oncológicos", icone: Ribbon },
  { chave: "vencidos", rotulo: "Vencidos", icone: TimerOff },
  { chave: "alertas", rotulo: "Alertas", icone: AlertTriangle },
  { chave: "subiu", rotulo: "Subiu", icone: MoveUp },
]

const STATUS: [StatusFiltro, string][] = [
  ["todos", "Todos"],
  ["pendentes", "Pendentes"],
  ["revisados", "Revisados"],
  ["aprovados", "Aprovados"],
  ["editados", "Editados"],
]

const itensEspecialidade = (): Record<string, string> => Object.fromEntries([["todas", "Todas as especialidades"], ...ESPECIALIDADES.map((e) => [e, e])])
const ITENS_CAMADA: Record<string, string> = { todas: "Todas as camadas", "1": "Camada 1 · oncológico", "2": "Camada 2 · urgente", "3": "Camada 3 · demais" }

const ITENS_CLASSE: Record<string, string> = Object.fromEntries([["todas", "Todas as classes"], ...CLASSES.map((c) => [c, `Classe ${c}`])])

export function FiltrosFila({ total, visiveis }: { total: number; visiveis: number }) {
  const ITENS_ESPECIALIDADE = itensEspecialidade()
  const filtros = useStore((s) => s.filtros)
  const setFiltros = useStore((s) => s.setFiltros)
  const limpar = useStore((s) => s.limparFiltros)
  const irParaPosicao = useStore((s) => s.irParaPosicao)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const decisoes = useStore((s) => s.decisoes)
  const ativo = filtrosAtivos(filtros)
  const [aberto, setAberto] = useState(false)
  const nAtivos = [filtros.especialidade !== "todas", filtros.classe !== "todas", filtros.camada !== "todas", filtros.oncologicos, filtros.vencidos, filtros.alertas, filtros.subiu].filter(Boolean).length
  const contagem = useMemo(() => {
    const valores = Object.values(decisoes)
    const aprovados = valores.filter((d) => d.status === "aprovado").length
    const editados = valores.filter((d) => d.status === "editado").length
    return { todos: total, pendentes: total - aprovados - editados, revisados: aprovados + editados, aprovados, editados }
  }, [decisoes, total])

  const seletor = (itens: Record<string, string>, valor: string, aoMudar: (v: string) => void, rotulo: string, className: string) => (
    <Select items={itens} value={valor} onValueChange={(v) => aoMudar(v ?? "todas")}>
      <SelectTrigger size="sm" className={className} aria-label={rotulo}>
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
  )

  const irPara = (className: string) => (
    <form
      className={className}
      onSubmit={(e) => {
        e.preventDefault()
        const campo = new FormData(e.currentTarget).get("destino")?.toString().trim() ?? ""
        const numero = Number(campo.replace("#", ""))
        const achou = Number.isInteger(numero) && numero > 0 ? irParaPosicao(numero) : PACIENTE_POR_ID[campo.toUpperCase()] ? (abrirNaFila(campo.toUpperCase()), true) : false
        if (!achou) toast.error(`Posição ou ID "${campo}" não encontrado`)
        else e.currentTarget.reset()
      }}
    >
      <Input name="destino" placeholder="Ir para #posição ou ID" className="h-9 w-full lg:h-8" aria-label="Ir para posição ou ID" />
    </form>
  )

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input id="busca-fila" value={filtros.busca} onChange={(e) => setFiltros({ busca: e.target.value })} placeholder="Buscar ID, CID ou procedimento  ( / )" className="h-9 pl-8 lg:h-8" aria-label="Buscar por ID, CID ou procedimento" />
        </div>
        <div className="hidden items-center gap-2 lg:flex">
          {seletor(ITENS_ESPECIALIDADE, filtros.especialidade, (v) => setFiltros({ especialidade: v }), "Filtrar por especialidade", "w-44")}
          {seletor(ITENS_CLASSE, filtros.classe, (v) => setFiltros({ classe: v }), "Filtrar por classe", "w-32")}
          {irPara("w-40")}
        </div>
        <Button size="sm" variant="outline" className="h-9 shrink-0 gap-1.5 lg:h-7" aria-label={`Filtros${nAtivos ? `, ${nAtivos} ativos` : ""}`} onClick={() => setAberto(true)}>
          <SlidersHorizontal aria-hidden />
          <span className="hidden sm:inline">Filtros</span>
          {nAtivos > 0 && <span className="rounded bg-primary/15 px-1 text-xs tabular-nums text-primary">{nAtivos}</span>}
        </Button>
        <div className="hidden md:block">
          <MenuColunas />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <div role="group" aria-label="Filtrar por status da revisão" className="flex min-w-0 items-center gap-0.5 overflow-x-auto rounded-lg bg-muted/60 p-0.5">
          {STATUS.map(([valor, rotulo]) => {
            const ligado = filtros.status === valor
            return (
              <button
                key={valor}
                type="button"
                aria-pressed={ligado}
                onClick={() => setFiltros({ status: valor })}
                className={cn(
                  "shrink-0 rounded-md px-2.5 py-1.5 text-xs transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring sm:py-1",
                  ligado ? "bg-background font-medium shadow-sm" : "text-muted-foreground hover:text-foreground"
                )}
              >
                {rotulo} <span className="tabular-nums opacity-60">{contagem[valor]}</span>
              </button>
            )
          })}
        </div>
        <span className="ml-auto shrink-0 text-xs text-muted-foreground tabular-nums">
          {visiveis} de {total}
        </span>
        {ativo && (
          <Button size="xs" variant="ghost" onClick={limpar} className="h-8 shrink-0 gap-1 sm:h-6" aria-label="Limpar filtros">
            <FilterX className="size-3" aria-hidden />
            Limpar
          </Button>
        )}
      </div>

      <Sheet open={aberto} onOpenChange={setAberto}>
        <SheetContent side="right" className="overflow-y-auto">
          <SheetHeader>
            <SheetTitle>Filtros</SheetTitle>
          </SheetHeader>
          <div className="flex flex-col gap-4 px-4 pb-4">
            <div className="flex flex-col gap-4 lg:hidden">
              {seletor(ITENS_ESPECIALIDADE, filtros.especialidade, (v) => setFiltros({ especialidade: v }), "Filtrar por especialidade", "w-full")}
              {seletor(ITENS_CLASSE, filtros.classe, (v) => setFiltros({ classe: v }), "Filtrar por classe", "w-full")}
              {irPara("")}
            </div>
            {seletor(ITENS_CAMADA, filtros.camada, (v) => setFiltros({ camada: v }), "Filtrar por camada", "w-full")}
            <div className="flex flex-wrap gap-2">
              {TOGGLES.map(({ chave, rotulo, icone: Icone }) => (
                <Toggle key={chave} size="sm" variant="default" pressed={filtros[chave] as boolean} onPressedChange={(v) => setFiltros({ [chave]: v })} className="h-9 gap-1 px-3 text-xs data-[pressed]:bg-primary/12 data-[pressed]:text-primary">
                  <Icone aria-hidden />
                  {rotulo}
                </Toggle>
              ))}
            </div>
            {ativo && (
              <Button size="sm" variant="outline" onClick={limpar} className="gap-1">
                <FilterX aria-hidden /> Limpar filtros
              </Button>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
