import { BarChart3, BellRing, FileUp, BookOpen, CircleHelp, ClipboardList, Gavel, Inbox, ListOrdered, Moon, PanelLeft, Sun, UserSearch } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import { formatarContador, useContadores } from "@/components/layout/useContadores"
import { PAGINAS_POR_TECLA } from "@/lib/atalhos"
import type { Pagina } from "@/lib/filtros"
import { useStore } from "@/store/useStore"
import { useTema } from "@/store/tema"

type Item = { id: Pagina; rotulo: string; icone: typeof ListOrdered }
const GRUPOS: { titulo: string; itens: Item[] }[] = [
  {
    titulo: "Regulação",
    itens: [
      { id: "fila", rotulo: "Fila", icone: ListOrdered },
      { id: "inbox", rotulo: "Para revisar", icone: Inbox },
      { id: "pacientes", rotulo: "Pacientes", icone: UserSearch },
      { id: "swalis", rotulo: "Classes e prazos", icone: BookOpen },
    ],
  },
  {
    titulo: "Dados e equipe",
    itens: [
      { id: "pendencias", rotulo: "Pendências", icone: ClipboardList },
      { id: "importar", rotulo: "Importar solicitações", icone: FileUp },
      { id: "notificacoes", rotulo: "Avisos ao paciente", icone: BellRing },
    ],
  },
  {
    titulo: "Comitê",
    itens: [
      { id: "propostas", rotulo: "Propostas de regra", icone: Gavel },
      { id: "analise", rotulo: "Indicadores", icone: BarChart3 },
    ],
  },
]

export function AppSidebar() {
  const pagina = useStore((s) => s.pagina)
  const ir = useStore((s) => s.ir)
  const setAtalhos = useStore((s) => s.setAtalhos)
  const { toggleSidebar, state, isMobile, setOpenMobile } = useSidebar()
  const fechar = () => { if (isMobile) setOpenMobile(false) }
  const resolvido = useTema((t) => t.resolvido)
  const setTema = useTema((t) => t.setTema)
  const escuro = resolvido === "dark"
  const c = useContadores()
  const contador = (id: Pagina): { n: number; texto: string; atencao: boolean } | null => {
    const n = id === "inbox" ? c.paraRevisar : id === "pendencias" ? c.pendencias : null
    if (!n) return null
    return { n, texto: id === "inbox" ? `${n.toLocaleString("pt-BR")} para revisar` : `${n.toLocaleString("pt-BR")} ${n === 1 ? "pendência aberta" : "pendências abertas"}`, atencao: id === "pendencias" && c.pendenciasBloqueantes }
  }

  return (
    <Sidebar collapsible="icon" className="no-print">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" tooltip="HealthPrior" render={<div />} className="cursor-default hover:bg-transparent">
              <img src="/logo.png" alt="" width={32} height={32} className="size-8 shrink-0 object-contain" />
              <span className="grid flex-1 text-left leading-tight">
                <span className="truncate text-sm font-semibold">HealthPrior</span>
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        {GRUPOS.map((g, i) => (
          <SidebarGroup key={g.titulo} className={i > 0 ? "group-data-[collapsible=icon]:mt-1 group-data-[collapsible=icon]:border-t group-data-[collapsible=icon]:border-sidebar-border" : undefined}>
            <SidebarGroupLabel className="h-7 text-[11px] text-muted-foreground">{g.titulo}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {g.itens.map((item) => {
                  const tecla = String(PAGINAS_POR_TECLA.indexOf(item.id) + 1)
                  const ct = contador(item.id)
                  return (
                    <SidebarMenuItem key={item.id}>
                      <SidebarMenuButton isActive={pagina === item.id} tooltip={`${item.rotulo} (${tecla})`} onClick={() => { ir(item.id); fechar() }}>
                        <item.icone aria-hidden />
                        <span>{item.rotulo}</span>
                      </SidebarMenuButton>
                      {ct && (
                        <>
                          <SidebarMenuBadge aria-label={ct.texto} className={ct.atencao ? "text-[var(--prazo-limite)]" : "text-muted-foreground"}>
                            {formatarContador(ct.n)}
                          </SidebarMenuBadge>
                          <span
                            role="img"
                            aria-label={ct.texto}
                            className={`pointer-events-none absolute top-1 right-1 hidden size-2 rounded-full group-data-[collapsible=icon]:block ${ct.atencao ? "bg-[var(--prazo-limite)]" : "bg-muted-foreground"}`}
                          />
                        </>
                      )}
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip={escuro ? "Tema claro" : "Tema escuro"} onClick={() => setTema(escuro ? "light" : "dark")}>
              {escuro ? <Sun aria-hidden /> : <Moon aria-hidden />}
              <span>{escuro ? "Tema claro" : "Tema escuro"}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Atalhos (?)" onClick={() => { setAtalhos(true); fechar() }}>
              <CircleHelp aria-hidden />
              <span>Atalhos</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem className="hidden md:block">
            <SidebarMenuButton tooltip={state === "expanded" ? "Recolher menu ([)" : "Expandir menu ([)"} onClick={toggleSidebar}>
              <PanelLeft aria-hidden />
              <span>{state === "expanded" ? "Recolher menu" : "Expandir menu"}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
