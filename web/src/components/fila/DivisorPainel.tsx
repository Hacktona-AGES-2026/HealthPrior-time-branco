import { useRef } from "react"
import { useColunas } from "@/store/colunas"

export function DivisorPainel() {
  const painel = useColunas((c) => c.painel)
  const setPainel = useColunas((c) => c.setPainel)
  const oculto = useColunas((c) => c.painelOculto)
  const origem = useRef<{ x: number; w: number } | null>(null)
  if (oculto) return null
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Redimensionar painel de aprovação"
      tabIndex={0}
      className="group/div relative hidden w-0 cursor-col-resize touch-none outline-none lg:block"
      onDoubleClick={() => setPainel(340)}
      onPointerDown={(e) => {
        origem.current = { x: e.clientX, w: painel }
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (origem.current) setPainel(origem.current.w - (e.clientX - origem.current.x))
      }}
      onPointerUp={() => {
        origem.current = null
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") setPainel(painel + 16)
        if (e.key === "ArrowRight") setPainel(painel - 16)
      }}
    >
      <span className="absolute inset-y-0 -left-1.5 w-3 transition-colors group-hover/div:bg-primary/10 group-focus-visible/div:bg-primary/15" />
      <span className="absolute inset-y-0 -left-px w-0.5 transition-colors group-hover/div:bg-primary/50" />
    </div>
  )
}
