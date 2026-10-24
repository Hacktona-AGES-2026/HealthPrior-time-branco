import { Activity, BarChart3, BookOpen, CircleHelp, FileCheck2, Inbox, ListOrdered, Moon, PanelLeft, Sun, UserSearch } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import type { Pagina } from "@/lib/filtros"
import { useStore } from "@/store/useStore"
import { useTema } from "@/store/tema"

const ITENS: { id: Pagina; rotulo: string; icone: typeof ListOrdered; tecla: string }[] = [
  { id: "fila", rotulo: "Fila", icone: ListOrdered, tecla: "1" },
  { id: "inbox", rotulo: "Inbox", icone: Inbox, tecla: "2" },
  { id: "pacientes", rotulo: "Pacientes", icone: UserSearch, tecla: "3" },
  { id: "analise", rotulo: "Análise geral", icone: BarChart3, tecla: "4" },
  { id: "swalis", rotulo: "SWALIS", icone: BookOpen, tecla: "5" },
  { id: "propostas", rotulo: "Propostas", icone: FileCheck2, tecla: "6" },
]

export function AppSidebar() {
  const pagina = useStore((s) => s.pagina)
  const ir = useStore((s) => s.ir)
  const setAtalhos = useStore((s) => s.setAtalhos)
  const selecionadoId = useStore((s) => s.selecionadoId)
  const { toggleSidebar, state } = useSidebar()
  const resolvido = useTema((t) => t.resolvido)
  const setTema = useTema((t) => t.setTema)
  const escuro = resolvido === "dark"

  return (
    <Sidebar collapsible="icon" className="no-print">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" tooltip="HealthPrior" render={<div />} className="cursor-default hover:bg-transparent">
              <span className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Activity className="size-4" aria-hidden />
              </span>
              <span className="grid flex-1 text-left leading-tight">
                <span className="truncate text-sm font-semibold">HealthPrior</span>
                <span className="truncate text-xs text-muted-foreground">Regulação cirúrgica SUS</span>
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {ITENS.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton isActive={pagina === item.id} tooltip={item.rotulo} onClick={() => ir(item.id)}>
                    <item.icone aria-hidden />
                    <span>{item.rotulo}</span>
                    {item.id === "pacientes" && selecionadoId && (
                      <span className="fx-pop ml-auto size-2 rounded-full bg-primary group-data-[collapsible=icon]:hidden" aria-label="Paciente selecionado" />
                    )}
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
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
            <SidebarMenuButton tooltip="Atalhos (?)" onClick={() => setAtalhos(true)}>
              <CircleHelp aria-hidden />
              <span>Atalhos</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip={state === "expanded" ? "Recolher menu ([)" : "Expandir menu ([)"} onClick={toggleSidebar}>
              <PanelLeft aria-hidden />
              <span>Recolher menu</span>
              <kbd className="ml-auto rounded border bg-muted px-1.5 text-[10px] text-muted-foreground group-data-[collapsible=icon]:hidden">[</kbd>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
