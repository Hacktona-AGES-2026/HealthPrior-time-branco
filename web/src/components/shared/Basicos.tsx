import { ArrowRight, ChevronDown, ChevronUp, Equal, TriangleAlert } from "lucide-react"
import type { Camada, Classe, Paciente, Prioridade } from "@/data/tipos"
import { COR_STATUS, DESCRICAO_CAMADA, NOME_CAMADA, corClasse, corPrazo, corTextoClasse, rotuloPrazo } from "@/lib/cores"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { precisaRevisar, type Decisao } from "@/lib/filtros"

export function ClasseBadge({ classe, className }: { classe: Classe; className?: string }) {
  return (
    <span
      className={cn("inline-flex min-w-9 items-center justify-center rounded-md border px-1.5 py-0.5 text-xs font-semibold tabular-nums", className)}
      style={{
        color: corTextoClasse(classe),
        borderColor: `color-mix(in oklab, ${corClasse(classe)} 45%, transparent)`,
        background: `color-mix(in oklab, ${corClasse(classe)} 14%, transparent)`,
      }}
      aria-label={`Classe ${classe}`}
    >
      {classe}
    </span>
  )
}

export function MudancaClasse({ de, para }: { de: Prioridade | null; para: Classe }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">{de ? `prioridade ${de === "media" ? "média" : de}` : "sem prioridade"}</span>
      <ArrowRight className="size-3.5 text-muted-foreground" aria-hidden />
      <ClasseBadge classe={para} className="fx-pop" />
    </span>
  )
}

export function CamadaBadge({ camada }: { camada: Camada }) {
  const cor = camada === 1 ? "var(--cls-a2)" : camada === 2 ? "var(--cls-b)" : "var(--cls-d)"
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs" style={{ background: `color-mix(in oklab, ${cor} 14%, transparent)` }}>
            <span className="font-semibold tabular-nums">{camada}</span>
            <span className="text-muted-foreground">{NOME_CAMADA[camada]}</span>
          </span>
        }
      />
      <TooltipContent>{DESCRICAO_CAMADA[camada]}</TooltipContent>
    </Tooltip>
  )
}

export function SetaVariacao({ antiga, nova, animada = true }: { antiga: number; nova: number; animada?: boolean }) {
  const delta = antiga - nova
  if (delta === 0) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs font-medium text-muted-foreground" aria-label="Posição inalterada">
        <Equal className="size-3" aria-hidden />
      </span>
    )
  }
  const sobe = delta > 0
  const Icone = sobe ? ChevronUp : ChevronDown
  return (
    <span
      className="inline-flex items-center gap-0.5 text-xs font-semibold tabular-nums"
      style={{ color: sobe ? "var(--sobe)" : "var(--desce)" }}
      aria-label={sobe ? `Subiu ${delta} posições` : `Desceu ${-delta} posições`}
    >
      <span className="relative inline-flex h-4 w-3 flex-col items-center justify-center overflow-visible" aria-hidden>
        {[0, 1, 2].map((i) => (
          <Icone
            key={i}
            className={cn("fx-chevron -my-[5px] size-3.5", sobe ? "fx-chevron-up" : "fx-chevron-down")}
            style={{ animationDelay: `${(sobe ? 2 - i : i) * 0.16}s`, animationPlayState: animada ? "running" : "paused" }}
          />
        ))}
      </span>
      {sobe ? "▲" : "▼"}
      {Math.abs(delta)}
    </span>
  )
}

export const formatarPct = (pct: number) => (pct >= 1000 ? `${(pct / 1000).toFixed(1).replace(".", ",")}k%` : `${Math.round(pct)}%`)

export function PrazoBar({ pct, className, compacto = false }: { pct: number; className?: string; compacto?: boolean }) {
  const largura = Math.min(100, pct)
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className={cn("flex items-center gap-2", className)}>
            <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100} aria-label="Prazo consumido">
              <span className="fx-grow-x absolute inset-y-0 left-0 rounded-full" style={{ width: `${largura}%`, background: corPrazo(pct) }} />
              {pct > 100 && (
                <span
                  className="absolute inset-0 opacity-50"
                  style={{ backgroundImage: "repeating-linear-gradient(135deg, transparent 0 3px, rgb(255 255 255 / 0.55) 3px 5px)" }}
                />
              )}
            </span>
            <span className={cn("shrink-0 text-xs font-semibold tabular-nums", compacto ? "w-9" : "w-11 text-right")} style={{ color: pct > 100 ? "var(--prazo-vencido)" : undefined }}>
              {formatarPct(pct)}
            </span>
          </span>
        }
      />
      <TooltipContent>
        {Math.round(pct).toLocaleString("pt-BR")}% do prazo consumido · {rotuloPrazo(pct)}
      </TooltipContent>
    </Tooltip>
  )
}

export function StatusAprovacao({ decisao }: { decisao?: Decisao }) {
  const status = decisao?.status ?? "pendente"
  const rotulo = status === "pendente" ? "Pendente" : status === "aprovado" ? "Aprovado" : "Editado"
  const marca = status === "pendente" ? "○" : status === "aprovado" ? "✓" : "✎"
  return (
    <span
      className={cn("inline-flex items-center gap-1.5 text-xs", status !== "pendente" && "fx-pop font-medium")}
      style={{ color: status === "pendente" ? "var(--muted-foreground)" : COR_STATUS[status] }}
    >
      <span aria-hidden>{marca}</span>
      {rotulo}
    </span>
  )
}

export function AlertaRevisao({ paciente }: { paciente: Paciente }) {
  if (!precisaRevisar(paciente)) return null
  const motivos = paciente.alertas.join(" · ")
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span className="inline-flex size-6 items-center justify-center rounded-full" style={{ color: "var(--prazo-limite)" }} role="img" aria-label={`Revisar: ${motivos}`}>
            <TriangleAlert className="size-4" />
          </span>
        }
      />
      <TooltipContent>{motivos}</TooltipContent>
    </Tooltip>
  )
}

export function SinalChips({ sinais, max = 3 }: { sinais: string[]; max?: number }) {
  if (sinais.length === 0) return <span className="text-xs text-muted-foreground">—</span>
  const visiveis = sinais.slice(0, max)
  const resto = sinais.length - visiveis.length
  return (
    <span className="flex min-w-0 items-center gap-1 overflow-hidden [mask-image:linear-gradient(to_right,black_82%,transparent)]">
      {visiveis.map((s) => (
        <Badge key={s} variant="secondary" className="shrink-0 bg-muted/70 px-1.5 text-[11px] font-normal whitespace-nowrap text-muted-foreground">
          {s}
        </Badge>
      ))}
      {resto > 0 && (
        <Tooltip>
          <TooltipTrigger render={<Badge variant="outline" className="shrink-0 border-transparent px-1.5 text-[11px] font-normal text-muted-foreground">+{resto}</Badge>} />
          <TooltipContent>{sinais.slice(max).join(", ")}</TooltipContent>
        </Tooltip>
      )}
    </span>
  )
}
