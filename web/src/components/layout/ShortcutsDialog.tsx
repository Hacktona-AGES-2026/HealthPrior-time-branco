import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useStore } from "@/store/useStore"

const ATALHOS = [
  ["A", "Aprovar o caso selecionado e avançar"],
  ["R", "Rejeitar (abre classe final e motivo)"],
  ["J", "Próximo caso pendente"],
  ["K", "Caso pendente anterior"],
  ["Esc", "Recolher a linha expandida / cancelar rejeição"],
  ["[", "Recolher ou expandir o menu lateral"],
  ["]", "Ocultar ou mostrar o painel de aprovação"],
  ["?", "Mostrar esta ajuda"],
  ["Arrastar", "Na faixa: zoom em um intervalo de posições"],
]

export function ShortcutsDialog() {
  const aberto = useStore((s) => s.atalhosAbertos)
  const setAtalhos = useStore((s) => s.setAtalhos)
  return (
    <Dialog open={aberto} onOpenChange={setAtalhos}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Atalhos de teclado</DialogTitle>
          <DialogDescription>Ignorados enquanto o foco estiver em um campo de texto.</DialogDescription>
        </DialogHeader>
        <ul className="divide-y">
          {ATALHOS.map(([tecla, texto]) => (
            <li key={tecla} className="flex items-center justify-between gap-4 py-2 text-sm">
              <span>{texto}</span>
              <kbd className="min-w-8 rounded border bg-muted px-2 py-0.5 text-center text-xs font-semibold">{tecla}</kbd>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  )
}
