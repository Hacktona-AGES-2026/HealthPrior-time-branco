import { useRef } from "react"
import { useColunas } from "@/store/colunas"

export function AlcaColuna({ id }: { id: string }) {
  const largura = useColunas((s) => s.larguras[id])
  const setLargura = useColunas((s) => s.setLargura)
  const resetar = useColunas((s) => s.resetar)
  const origem = useRef<{ x: number; w: number } | null>(null)

  return (
    <span
      role="separator"
      aria-orientation="vertical"
      aria-label="Redimensionar coluna (duplo clique restaura)"
      tabIndex={0}
      className="group/alca absolute top-0 -right-2 z-10 flex h-full w-4 cursor-col-resize touch-none items-center justify-center outline-none"
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={() => resetar(id)}
      onPointerDown={(e) => {
        e.preventDefault()
        e.stopPropagation()
        origem.current = { x: e.clientX, w: largura }
        e.currentTarget.setPointerCapture(e.pointerId)
      }}
      onPointerMove={(e) => {
        if (origem.current) setLargura(id, origem.current.w + e.clientX - origem.current.x)
      }}
      onPointerUp={() => {
        origem.current = null
      }}
      onKeyDown={(e) => {
        if (e.key === "ArrowLeft") setLargura(id, largura - 12)
        if (e.key === "ArrowRight") setLargura(id, largura + 12)
      }}
    >
      <span className="h-4 w-px rounded bg-border transition-all group-hover/alca:h-full group-hover/alca:w-0.5 group-hover/alca:bg-primary/60 group-focus-visible/alca:h-full group-focus-visible/alca:w-0.5 group-focus-visible/alca:bg-primary" />
    </span>
  )
}
