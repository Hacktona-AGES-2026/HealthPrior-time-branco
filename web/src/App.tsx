import { Suspense, lazy, useCallback } from "react"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { CabecalhoMetricas } from "@/components/layout/CabecalhoMetricas"
import { PaletaBusca } from "@/components/layout/PaletaBusca"
import { ShortcutsDialog } from "@/components/layout/ShortcutsDialog"
import { CarregandoPagina } from "@/components/shared/Carregando"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { usarAtalhos } from "@/lib/atalhos"
import { useStore } from "@/store/useStore"

const PaginaFila = lazy(() => import("@/components/fila/PaginaFila"))
const PaginaInbox = lazy(() => import("@/components/inbox/PaginaInbox"))
const PaginaPacientes = lazy(() => import("@/components/pacientes/PaginaPacientes"))
const PaginaAnalise = lazy(() => import("@/components/analise/PaginaAnalise"))
const PaginaSwalis = lazy(() => import("@/components/swalis/PaginaSwalis"))
const PaginaPropostas = lazy(() => import("@/components/propostas/PaginaPropostas"))
const PaginaPendencias = lazy(() => import("@/components/pendencias/PaginaPendencias"))

function Conteudo() {
  const pagina = useStore((s) => s.pagina)
  const versaoDados = useStore((s) => s.versaoDados)
  return (
    <Suspense fallback={<CarregandoPagina rotulo="Carregando página" />}>
      {/* versaoDados: remonta a página quando a fila é recarregada da API */}
      <div key={`${pagina}-${versaoDados}`} className="fx-fade-up flex min-h-0 flex-1 flex-col">
        {pagina === "fila" && <PaginaFila />}
        {pagina === "inbox" && <PaginaInbox />}
        {pagina === "pacientes" && <PaginaPacientes />}
        {pagina === "analise" && <PaginaAnalise />}
        {pagina === "swalis" && <PaginaSwalis />}
        {pagina === "pendencias" && <PaginaPendencias />}
        {pagina === "propostas" && <PaginaPropostas />}
      </div>
    </Suspense>
  )
}

export default function App() {
  const sidebarAberta = useStore((s) => s.sidebarAberta)
  const setSidebar = useStore((s) => s.setSidebar)
  const alternarMenu = useCallback(() => useStore.getState().setSidebar(!useStore.getState().sidebarAberta), [])
  usarAtalhos(alternarMenu)

  return (
    <>
      <TooltipProvider delay={250}>
        <SidebarProvider open={sidebarAberta} onOpenChange={setSidebar} className="h-svh">
          <AppSidebar />
          <SidebarInset className="min-h-0 min-w-0 overflow-hidden">
            <CabecalhoMetricas />
            <Conteudo />
          </SidebarInset>
        </SidebarProvider>
        <ShortcutsDialog />
        <PaletaBusca />
        <Toaster position="bottom-center" richColors closeButton />
      </TooltipProvider>
    </>
  )
}
