import { useMemo } from "react"
import { Progress } from "@/components/ui/progress"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { filtrosAtivos } from "@/lib/filtros"
import { usarContagem } from "@/lib/motion"
import { metricasGlobais } from "@/lib/stats"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const TITULOS = { fila: "Fila cirúrgica", inbox: "Inbox do regulador", pacientes: "Pacientes", analise: "Análise geral", swalis: "SWALIS", pendencias: "Pendências", propostas: "Propostas de regra" }

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
  const progresso = (m.revisados / m.totalDetalhados) * 100
  const filtrar = (parcial: Parameters<typeof setFiltros>[0]) => {
    setFiltros(parcial)
    ir("fila")
  }

  return (
    <header className="no-print sticky top-0 z-30 flex shrink-0 flex-wrap items-center gap-x-5 gap-y-1 border-b border-border/60 bg-background/90 px-4 py-2.5 backdrop-blur">
      <SidebarTrigger className="-ml-2 text-muted-foreground" aria-label="Recolher ou expandir menu" />
      <h1 className="text-sm font-medium">{TITULOS[pagina]}</h1>
      <div className="flex flex-1 flex-wrap items-baseline gap-x-4 gap-y-1">
        <Metrica rotulo="na fila" valor={m.total} ativo={!filtrosAtivos(filtros)} aoClicar={() => { limparFiltros(); ir("fila") }} />
        <Metrica rotulo="oncológicos" valor={m.oncologicos} ativo={filtros.camada === "1"} aoClicar={() => filtrar({ camada: filtros.camada === "1" ? "todas" : "1" })} />
        <Metrica rotulo="urgentes" valor={m.urgentes} ativo={filtros.camada === "2"} aoClicar={() => filtrar({ camada: filtros.camada === "2" ? "todas" : "2" })} />
        <Metrica rotulo="vencidos" valor={m.vencidos} cor="var(--prazo-vencido)" ativo={filtros.vencidos} aoClicar={() => filtrar({ vencidos: !filtros.vencidos })} />
        <Metrica rotulo="com alertas" valor={m.comAlertas} cor="var(--prazo-limite)" ativo={filtros.alertas} aoClicar={() => filtrar({ alertas: !filtros.alertas })} />
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
