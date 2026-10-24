import { useMemo } from "react"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { metricasGlobais } from "@/lib/stats"
import { useStore } from "@/store/useStore"

const TITULOS = { fila: "Fila cirúrgica", inbox: "Para revisar", pacientes: "Pacientes", analise: "Indicadores", swalis: "Classes e prazos", pendencias: "Pendências", propostas: "Propostas de regra", notificacoes: "Avisos ao paciente", importar: "Importar solicitações" }

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
