import { useMemo } from "react"
import { AlertTriangle, FilterX, MoveUp, Ribbon, Search, TimerOff } from "lucide-react"
import { toast } from "sonner"
import { ESPECIALIDADES, PACIENTE_POR_ID } from "@/data/fila"
import { MenuColunas } from "./MenuColunas"
import { CLASSES } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Toggle } from "@/components/ui/toggle"
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
  const contagem = useMemo(() => {
    const valores = Object.values(decisoes)
    const aprovados = valores.filter((d) => d.status === "aprovado").length
    const editados = valores.filter((d) => d.status === "editado").length
    return { todos: total, pendentes: total - aprovados - editados, revisados: aprovados + editados, aprovados, editados }
  }, [decisoes, total])

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center gap-2">
      <div className="relative min-w-48 flex-1">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input id="busca-fila" value={filtros.busca} onChange={(e) => setFiltros({ busca: e.target.value })} placeholder="Buscar ID, CID, procedimento ou iniciais  ( / )" className="h-8 pl-8" aria-label="Buscar por ID, CID ou procedimento" />
      </div>
      <Select items={ITENS_ESPECIALIDADE} value={filtros.especialidade} onValueChange={(v) => setFiltros({ especialidade: v ?? "todas" })}>
        <SelectTrigger size="sm" className="w-40" aria-label="Filtrar por especialidade">
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
        <SelectTrigger size="sm" className="w-32" aria-label="Filtrar por classe">
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
      <Select items={ITENS_CAMADA} value={filtros.camada} onValueChange={(v) => setFiltros({ camada: v ?? "todas" })}>
        <SelectTrigger size="sm" className="w-40" aria-label="Filtrar por camada">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(ITENS_CAMADA).map(([valor, rotulo]) => (
            <SelectItem key={valor} value={valor}>
              {rotulo}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <form
        className="flex items-center gap-1"
        onSubmit={(e) => {
          e.preventDefault()
          const campo = new FormData(e.currentTarget).get("destino")?.toString().trim() ?? ""
          const numero = Number(campo.replace("#", ""))
          const achou = Number.isInteger(numero) && numero > 0 ? irParaPosicao(numero) : PACIENTE_POR_ID[campo.toUpperCase()] ? (abrirNaFila(campo.toUpperCase()), true) : false
          if (!achou) toast.error(`Posição ou ID "${campo}" não encontrado`)
          else e.currentTarget.reset()
        }}
      >
        <Input name="destino" placeholder="Ir para #posição ou ID" className="h-8 w-40" aria-label="Ir para posição ou ID" />
      </form>
      <MenuColunas />
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
      {TOGGLES.map(({ chave, rotulo, icone: Icone }) => (
        <Toggle key={chave} size="sm" variant="default" pressed={filtros[chave] as boolean} onPressedChange={(v) => setFiltros({ [chave]: v })} className="h-7 gap-1 px-2 text-xs data-[pressed]:bg-primary/12 data-[pressed]:text-primary">
          <Icone aria-hidden />
          {rotulo}
        </Toggle>
      ))}
      <div role="group" aria-label="Filtrar por status da revisão" className="flex items-center gap-0.5 rounded-lg bg-muted/60 p-0.5">
        {STATUS.map(([valor, rotulo]) => {
          const ligado = filtros.status === valor
          return (
            <button
              key={valor}
              type="button"
              aria-pressed={ligado}
              onClick={() => setFiltros({ status: valor })}
              className={cn(
                "rounded-md px-2.5 py-1 text-xs transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring",
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
    </div>
  )
}
