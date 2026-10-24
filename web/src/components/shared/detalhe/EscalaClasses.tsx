import { useMemo } from "react"
import { PACIENTES } from "@/data/fila"
import type { Classe, Paciente } from "@/data/tipos"
import { CLASSES, PRAZO_MAX } from "@/lib/cores"
import { cn } from "@/lib/utils"
import { ClasseBadge } from "@/components/shared/Basicos"
import { useStore } from "@/store/useStore"

/** Quantos pacientes há em cada classe e em que lugar da classe o paciente está (ordem da fila). */
export function resumoEscala(p: Paciente, todos: Paciente[]) {
  const porClasse = Object.fromEntries(CLASSES.map((c) => [c, 0])) as Record<Classe, number>
  for (const x of todos) porClasse[x.classe] = (porClasse[x.classe] ?? 0) + 1
  const daClasse = todos.filter((x) => x.classe === p.classe).sort((a, b) => a.posicao - b.posicao)
  const indice = daClasse.findIndex((x) => x.id === p.id)
  return { porClasse, totalDaClasse: daClasse.length, lugar: indice >= 0 ? indice + 1 : null }
}

/** As cinco classes lado a lado, com a do paciente em destaque: prazo máximo e pacientes na fila. */
export function EscalaClasses({ p }: { p: Paciente }) {
  const versaoDados = useStore((s) => s.versaoDados) // a fila é recarregada depois de cada decisão
  const { porClasse, totalDaClasse, lugar } = useMemo(() => resumoEscala(p, PACIENTES), [p, versaoDados])
  const fmt = (n: number) => n.toLocaleString("pt-BR")

  return (
    <div className="space-y-1.5">
      <ol className="grid grid-cols-5 gap-1.5">
        {CLASSES.map((c) => {
          const atual = c === p.classe
          return (
            <li
              key={c}
              aria-current={atual ? "true" : undefined}
              className={cn("rounded-lg border px-1 py-2 text-center", atual ? "border-primary bg-primary/10" : "border-border/60 text-muted-foreground")}
            >
              <span className="sr-only">
                Classe {c}: prazo máximo de {PRAZO_MAX[c]} dias, {fmt(porClasse[c])} pacientes na fila{atual ? " (a deste paciente)" : ""}
              </span>
              <div aria-hidden className="flex flex-col items-center gap-0.5">
                <ClasseBadge classe={c} />
                <span className="text-xs tabular-nums">{PRAZO_MAX[c]} dias</span>
                <span className={cn("text-xs tabular-nums", atual && "font-semibold text-foreground")}>{fmt(porClasse[c])}</span>
              </div>
            </li>
          )
        })}
      </ol>
      <p className="text-xs text-muted-foreground">Em cada classe: prazo máximo e pacientes na fila.</p>
      {lugar !== null && (
        <p className="text-sm">
          Ocupa o {lugar}º lugar entre os {fmt(totalDaClasse)} pacientes da classe {p.classe}, na ordem da fila.
        </p>
      )}
    </div>
  )
}
