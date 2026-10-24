import { useMemo } from "react"
import { Progress } from "@/components/ui/progress"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { usarContagem } from "@/lib/motion"
import { metricasGlobais } from "@/lib/stats"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const TITULOS = { fila: "Fila cirúrgica", pacientes: "Pacientes", analise: "Análise geral", swalis: "SWALIS", pendencias: "Pendências" }

function Metrica({ rotulo, valor, cor, ativo, aoClicar }: { rotulo: string; valor: number; cor?: string; ativo?: boolean; aoClicar: () => void }) {
  const animado = usarContagem(valor)
  return (
    <button
      type="button"
      onClick={aoClicar}
      aria-pressed={ativo}
      title={ativo ? "Clique para remover o filtro" : "Clique para filtrar a fila"}
      className={cn(
        "inline-flex items-baseline gap-1.5 rounded-md px-1.5 py-0.5 whitespace-nowrap transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring",
        ativo && "bg-primary/10"
      )}
    >
      <span key={valor} className="fx-pop text-sm font-semibold tabular-nums" style={{ color: cor }}>
        {Math.round(animado).toLocaleString("pt-BR")}
      </span>
      <span className={cn("text-xs", ativo ? "font-medium text-foreground" : "text-muted-foreground")}>{rotulo}</span>
    </button>
  )
}

export function CabecalhoMetricas() {
  const pagina = useStore((s) => s.pagina)
  const decisoes = useStore((s) => s.decisoes)
  const filtros = useStore((s) => s.filtros)
  const setFiltros = useStore((s) => s.setFiltros)
  const limparFiltros = useStore((s) => s.limparFiltros)
  const ir = useStore((s) => s.ir)
  const m = useMemo(() => metricasGlobais(decisoes), [decisoes])
  const filtrar = (parcial: Parameters<typeof setFiltros>[0]) => {
    setFiltros(parcial)
    ir("fila")
  }
  const semFiltros = JSON.stringify(Object.values(filtros)) === JSON.stringify(["", "todas", "todas", false, false, false, false, "todos"])
  const progresso = (m.revisados / m.totalDetalhados) * 100

  return (
    <header className="no-print sticky top-0 z-30 flex shrink-0 flex-wrap items-center gap-x-5 gap-y-1 border-b border-border/60 bg-background/90 px-4 py-2.5 backdrop-blur">
      <SidebarTrigger className="-ml-2 text-muted-foreground" aria-label="Recolher ou expandir menu" />
      <h1 className="text-sm font-medium">{TITULOS[pagina]}</h1>
      <div className="flex flex-1 flex-wrap items-baseline gap-x-5 gap-y-1">
        <Metrica rotulo="na fila" valor={m.total} ativo={semFiltros} aoClicar={() => { limparFiltros(); ir("fila") }} />
        <Metrica rotulo="mudaram" valor={m.mudaram} ativo={filtros.mudou} aoClicar={() => filtrar({ mudou: !filtros.mudou })} />
        <Metrica rotulo="onc. corrigidos" valor={m.oncologicosCorrigidos} ativo={filtros.oncologicos} aoClicar={() => filtrar({ oncologicos: !filtros.oncologicos })} />
        <Metrica rotulo="vencidos" valor={m.vencidos} cor={m.vencidos > 0 ? "var(--prazo-vencido)" : undefined} ativo={filtros.vencidos} aoClicar={() => filtrar({ vencidos: !filtros.vencidos })} />
        <Metrica rotulo="para revisar" valor={m.revisar} cor={m.revisar > 0 ? "var(--prazo-limite)" : undefined} ativo={filtros.divergencia} aoClicar={() => filtrar({ divergencia: !filtros.divergencia })} />
      </div>
      <button
        type="button"
        aria-pressed={filtros.status === "revisados"}
        title="Clique para ver só os revisados"
        onClick={() => filtrar({ status: filtros.status === "revisados" ? "todos" : "revisados" })}
        className={cn("flex min-w-36 flex-col gap-1 rounded-md px-1.5 py-0.5 text-left transition-colors outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring", filtros.status === "revisados" && "bg-primary/10")}
      >
        <span className="text-xs text-muted-foreground tabular-nums">
          {m.revisados} de {m.totalDetalhados} revisados
        </span>
        <Progress value={progresso} className="h-1" aria-label="Progresso da revisão" />
      </button>
    </header>
  )
}
