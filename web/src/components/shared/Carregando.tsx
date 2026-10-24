import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

export function CarregandoBloco({ rotulo, altura = 200, className }: { rotulo: string; altura?: number; className?: string }) {
  return (
    <div className={cn("relative overflow-hidden rounded-xl bg-muted/40 p-3", className)} style={{ minHeight: altura }} role="status" aria-live="polite">
      <div className="mb-3 flex items-center gap-2">
        <Skeleton className="h-3.5 w-28" />
        <span className="fx-loading-dots text-xs text-muted-foreground">{rotulo}</span>
      </div>
      <div className="flex h-[calc(100%-2rem)] items-end gap-1.5" style={{ height: altura - 52 }}>
        {[40, 62, 35, 78, 55, 88, 45, 70, 30, 60, 82, 50].map((h, i) => (
          <div key={i} className="fx-shimmer flex-1 rounded-t bg-muted" style={{ height: `${h}%`, animationDelay: `${i * 0.09}s` }} />
        ))}
      </div>
      <div className="fx-wave-line absolute inset-x-0 bottom-0 h-0.5" aria-hidden />
    </div>
  )
}

export function CarregandoPagina({ rotulo }: { rotulo: string }) {
  return (
    <div className="flex flex-1 flex-col gap-3 p-4" role="status" aria-live="polite">
      <div className="fx-loading-dots text-sm text-muted-foreground">{rotulo}</div>
      <div className="grid gap-3 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-24 fx-shimmer" style={{ animationDelay: `${i * 0.15}s` }} />
        ))}
      </div>
      <Skeleton className="h-64 fx-shimmer" />
      <Skeleton className="h-40 fx-shimmer" />
    </div>
  )
}
