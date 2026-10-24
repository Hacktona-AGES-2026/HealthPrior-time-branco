import { useState } from "react"
import { ClipboardCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet"
import { useStore } from "@/store/useStore"
import { PainelAprovacao } from "./PainelAprovacao"

export function PainelDrawer() {
  const [aberto, setAberto] = useState(false)
  const selecionadoId = useStore((s) => s.selecionadoId)
  return (
    <div className="lg:hidden">
      <Button className="fixed right-4 bottom-4 z-30 gap-2 rounded-full shadow-lg" onClick={() => setAberto(true)} aria-label="Abrir painel de aprovação">
        <ClipboardCheck aria-hidden />
        {selecionadoId ?? "Aprovação"}
      </Button>
      <Sheet open={aberto} onOpenChange={setAberto}>
        <SheetContent side="right" className="w-full overflow-y-auto pt-10 sm:max-w-md">
          <SheetTitle className="sr-only">Painel de aprovação</SheetTitle>
          <SheetDescription className="sr-only">Aprovar ou editar a classe do paciente selecionado</SheetDescription>
          <PainelAprovacao modo="drawer" />
        </SheetContent>
      </Sheet>
    </div>
  )
}
