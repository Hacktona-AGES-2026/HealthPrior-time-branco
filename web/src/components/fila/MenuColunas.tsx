import { useEffect, useRef, useState } from "react"
import { Columns3, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { COLUNAS, useColunas } from "@/store/colunas"

export function MenuColunas() {
  const [aberto, setAberto] = useState(false)
  const caixa = useRef<HTMLDivElement>(null)
  const ocultas = useColunas((c) => c.ocultas)
  const alternar = useColunas((c) => c.alternarColuna)
  const resetarTudo = useColunas((c) => c.resetarTudo)

  useEffect(() => {
    if (!aberto) return
    const fora = (e: PointerEvent) => {
      if (!caixa.current?.contains(e.target as Node)) setAberto(false)
    }
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false)
    document.addEventListener("pointerdown", fora)
    document.addEventListener("keydown", esc)
    return () => {
      document.removeEventListener("pointerdown", fora)
      document.removeEventListener("keydown", esc)
    }
  }, [aberto])

  const escondidas = Object.values(ocultas).filter(Boolean).length

  return (
    <div ref={caixa} className="relative">
      <Button size="sm" variant="outline" className="gap-1.5" aria-expanded={aberto} onClick={() => setAberto((v) => !v)}>
        <Columns3 aria-hidden /> Colunas{escondidas > 0 && <span className="rounded bg-primary/15 px-1 text-xs tabular-nums">-{escondidas}</span>}
      </Button>
      {aberto && (
        <div className="fx-expand absolute right-0 z-40 mt-1 w-56 rounded-xl border bg-popover p-2 shadow-lg" role="menu">
          <ul className="space-y-0.5">
            {COLUNAS.filter((c) => c.id !== "pos" && c.rotulo).map((c) => (
              <li key={c.id}>
                <label className="flex cursor-pointer items-center gap-2 rounded-md px-2 py-1 text-sm hover:bg-muted">
                  <input type="checkbox" checked={!ocultas[c.id]} onChange={() => alternar(c.id)} className="size-3.5 accent-[var(--primary)]" />
                  {c.rotulo}
                </label>
              </li>
            ))}
          </ul>
          <Button size="xs" variant="ghost" className="mt-1 w-full gap-1" onClick={resetarTudo}>
            <RotateCcw className="size-3" aria-hidden /> Restaurar larguras e colunas
          </Button>
        </div>
      )}
    </div>
  )
}
