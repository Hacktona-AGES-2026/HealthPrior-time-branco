import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function CartaoGrafico({ titulo, descricao, children, className, atraso = 0 }: { titulo: string; descricao?: string; children: ReactNode; className?: string; atraso?: number }) {
  return (
    <section className={cn("fx-fade-up min-w-0 rounded-xl bg-muted/40 p-3", className)} style={{ animationDelay: `${atraso}ms` }}>
      <header className="mb-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{titulo}</h3>
        {descricao && <p className="text-[11px] text-muted-foreground">{descricao}</p>}
      </header>
      {children}
    </section>
  )
}
