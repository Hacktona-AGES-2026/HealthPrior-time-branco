import { Suspense, lazy } from "react"
import { AppSidebar } from "@/components/layout/AppSidebar"
import { CabecalhoMetricas } from "@/components/layout/CabecalhoMetricas"
import { CarregandoPagina } from "@/components/shared/Carregando"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { useStore } from "@/store/useStore"

const PaginaFila = lazy(() => import("@/components/fila/PaginaFila"))
const PaginaInbox = lazy(() => import("@/components/inbox/PaginaInbox"))
const PaginaPacientes = lazy(() => import("@/components/pacientes/PaginaPacientes"))
const PaginaAnalise = lazy(() => import("@/components/analise/PaginaAnalise"))
const PaginaSwalis = lazy(() => import("@/components/swalis/PaginaSwalis"))
const PaginaPendencias = lazy(() => import("@/components/pendencias/PaginaPendencias"))
const PaginaNotificacoes = lazy(() => import("@/components/notificacoes/PaginaNotificacoes"))
const PaginaImportar = lazy(() => import("@/components/importar/PaginaImportar"))
const PaginaPropostas = lazy(() => import("@/components/propostas/PaginaPropostas"))

function Conteudo() {
  const pagina = useStore((s) => s.pagina)
  const versaoDados = useStore((s) => s.versaoDados)
  return (
    <Suspense fallback={<CarregandoPagina rotulo="Carregando página" />}>
      {/* versaoDados: remonta a página quando a fila é recarregada da API */}
      <div key={`${pagina}-${versaoDados}`} className="flex min-h-0 min-w-0 flex-1 flex-col">
        {pagina === "fila" && <PaginaFila />}
        {pagina === "inbox" && <PaginaInbox />}
        {pagina === "pacientes" && <PaginaPacientes />}
        {pagina === "analise" && <PaginaAnalise />}
        {pagina === "swalis" && <PaginaSwalis />}
        {pagina === "pendencias" && <PaginaPendencias />}
        {pagina === "propostas" && <PaginaPropostas />}
        {pagina === "importar" && <PaginaImportar />}
        {pagina === "notificacoes" && <PaginaNotificacoes />}
      </div>
    </Suspense>
  )
}

export default function App() {
  const sidebarAberta = useStore((s) => s.sidebarAberta)
  const setSidebar = useStore((s) => s.setSidebar)

  return (
    <>
      <TooltipProvider delay={250}>
        <SidebarProvider open={sidebarAberta} onOpenChange={setSidebar} className="h-svh min-w-0">
          <AppSidebar />
          <SidebarInset className="min-h-0 min-w-0 overflow-hidden">
            <CabecalhoMetricas />
            <Conteudo />
          </SidebarInset>
        </SidebarProvider>
        <Toaster position="bottom-center" richColors closeButton offset={{ bottom: 16, left: 12, right: 12 }} mobileOffset={{ bottom: 16, left: 12, right: 12 }} />
      </TooltipProvider>
    </>
  )
}
