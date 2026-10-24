import { useRef, type ReactNode } from "react"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"

type Props = {
  aberto: boolean
  titulo: string
  descricao?: ReactNode
  rotuloConfirmar: string
  aoConfirmar: () => void
  aoCancelar: () => void
  ocupado?: boolean
}

export function DialogoConfirmacao({ aberto, titulo, descricao, rotuloConfirmar, aoConfirmar, aoCancelar, ocupado = false }: Props) {
  const cancelar = useRef<HTMLButtonElement>(null)
  return (
    <Dialog open={aberto} onOpenChange={(v) => !v && aoCancelar()}>
      <DialogContent showCloseButton={false} initialFocus={cancelar}>
        <DialogHeader>
          <DialogTitle>{titulo}</DialogTitle>
          {descricao && <DialogDescription>{descricao}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <Button ref={cancelar} variant="outline" className="h-9" onClick={aoCancelar}>
            Cancelar
          </Button>
          <Button className="h-9" disabled={ocupado} onClick={aoConfirmar}>
            {rotuloConfirmar}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
