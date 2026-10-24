import { Crown, Scale } from "lucide-react"
import { cn } from "@/lib/utils"

export const ehRegraDeOuro = (regra: string) => regra.startsWith("R01")

export function RegrasChips({ regras, compacto = false }: { regras: string[]; compacto?: boolean }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {regras.map((r, i) => {
        const ouro = ehRegraDeOuro(r)
        const [codigo, ...resto] = r.split(" · ")
        return (
          <span
            key={r}
            className={cn(
              "fx-fade-up inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[11px] font-medium",
              ouro && "fx-glow"
            )}
            style={{
              animationDelay: `${i * 140}ms`,
              borderColor: ouro ? "var(--ouro)" : undefined,
              background: ouro ? "color-mix(in oklab, var(--ouro) 22%, transparent)" : "var(--muted)",
            }}
            title={r}
          >
            {ouro ? <Crown className="size-3" style={{ color: "var(--ouro)" }} aria-hidden /> : <Scale className="size-3 text-muted-foreground" aria-hidden />}
            <span className="font-bold">{codigo}</span>
            {!compacto && <span className="text-muted-foreground">{resto.join(" · ")}</span>}
          </span>
        )
      })}
    </div>
  )
}
