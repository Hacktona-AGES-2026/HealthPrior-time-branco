import { useRef } from "react"
import { ALTURA_FAIXA_PADRAO, useColunas } from "@/store/colunas"

export function DivisorFaixa() {
  const altura = useColunas((c) => c.alturaFaixa)
  const setAltura = useColunas((c) => c.setAlturaFaixa)
  const origem = useRef<{ y: number; h: number } | null>(null)
  return (
    <div
      role="separator"
      aria-orientation="horizontal"
      aria-label="Arraste para cima para dar mais espaço à tabela (duplo clique restaura)"
      tabIndex={0}
      className="group/dv flex h-3 cursor-row-resize touch-none items-center justify-center outline-none"
      onDoubleClick={() => setAltura(ALTURA_FAIXA_PADRAO)}
      onPointerDown={(e) => {
        origem.current = { y: e.clientY, h: altura }
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (origem.current) setAltura(origem.current.h + e.clientY - origem.current.y)
      }}
      onPointerUp={() => {
        origem.current = null
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowUp") setAltura(altura - 16)
        if (e.key === "ArrowDown") setAltura(altura + 16)
      }}
    >
      <span className="h-1 w-12 rounded-full bg-border transition-all group-hover/dv:w-20 group-hover/dv:bg-primary/50 group-focus-visible/dv:bg-primary" />
    </div>
  )
}
