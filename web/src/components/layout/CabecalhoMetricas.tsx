import { useMemo } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { metricasGlobais } from "@/lib/stats"
import { useStore } from "@/store/useStore"

<<<<<<< Updated upstream
const TITULOS = { fila: "Fila cirúrgica", inbox: "Inbox do regulador", pacientes: "Pacientes", analise: "Análise geral", swalis: "SWALIS", pendencias: "Pendências", propostas: "Propostas do comitê", notificacoes: "Notificações" }
=======
const TITULOS = { fila: "Fila cirúrgica", inbox: "Inbox do regulador", pacientes: "Pacientes", analise: "Análise geral", swalis: "SWALIS", propostas: "Propostas de regra", importar: "Importar solicitações", notificacoes: "Notificações" }

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
>>>>>>> Stashed changes

export function CabecalhoMetricas() {
  const pagina = useStore((s) => s.pagina)
  const decisoes = useStore((s) => s.decisoes)
  const m = useMemo(() => metricasGlobais(decisoes), [decisoes])
  const mostrarProgresso = pagina === "fila" || pagina === "inbox"

  return (
    <header className="no-print sticky top-0 z-30 shrink-0 border-b border-border/60 bg-background">
      <div className="flex items-center gap-3 px-3 py-2 md:px-4 md:py-2.5">
        {/* No desktop o único botão de recolher fica na própria sidebar */}
        <SidebarTrigger className="-ml-1 size-9 text-muted-foreground md:hidden" aria-label="Abrir menu" />
        <h1 className="min-w-0 flex-1 truncate text-sm font-medium">{TITULOS[pagina]}</h1>
        {mostrarProgresso && (
          <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
            {m.revisados} de {m.totalDetalhados} revisados
          </span>
        )}
      </div>
    </header>
  )
}
