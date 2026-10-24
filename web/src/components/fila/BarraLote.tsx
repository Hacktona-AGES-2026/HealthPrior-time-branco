import { useEffect, useMemo, useState } from "react"
import { CheckCheck, X } from "lucide-react"
import { PACIENTES } from "@/data/fila"
import { Button } from "@/components/ui/button"
import { aplicarFiltros, filtrosAtivos } from "@/lib/filtros"
import { useStore } from "@/store/useStore"

export function BarraLote() {
  const marcados = useStore((s) => s.marcados)
  const filtros = useStore((s) => s.filtros)
  const decisoes = useStore((s) => s.decisoes)
  const aprovarLote = useStore((s) => s.aprovarLote)
  const limpar = useStore((s) => s.limparMarcados)
  const [confirmando, setConfirmando] = useState<"marcados" | "filtrados" | null>(null)

  const pendentesFiltrados = useMemo(
    () => aplicarFiltros(PACIENTES, { ...filtros, status: "todos" }, decisoes).filter((p) => !decisoes[p.id]).map((p) => p.id),
    [filtros, decisoes]
  )
  const marcadosPendentes = marcados.filter((id) => !decisoes[id])
  const mostrarFiltrados = filtrosAtivos(filtros) && pendentesFiltrados.length > 0

  useEffect(() => {
    setConfirmando(null)
  }, [marcados.length, filtros])

  if (marcados.length === 0 && !mostrarFiltrados) return null

  const executar = (tipo: "marcados" | "filtrados") => {
    if (confirmando !== tipo) {
      setConfirmando(tipo)
      return
    }
    aprovarLote(tipo === "marcados" ? marcadosPendentes : pendentesFiltrados)
    setConfirmando(null)
  }

  return (
    <div className="fx-expand flex flex-wrap items-center gap-2 rounded-xl bg-primary/8 px-3 py-1.5 text-xs" role="region" aria-label="Ações em lote">
      {marcados.length > 0 && (
        <>
          <span className="font-medium tabular-nums">{marcados.length} selecionadas</span>
          <Button size="xs" variant={confirmando === "marcados" ? "default" : "outline"} className="gap-1" disabled={marcadosPendentes.length === 0} onClick={() => executar("marcados")}>
            <CheckCheck aria-hidden />
            {confirmando === "marcados" ? `Confirmar aprovar ${marcadosPendentes.length}?` : `Aprovar sugeridas (${marcadosPendentes.length})`}
          </Button>
          <Button size="xs" variant="ghost" className="gap-1" onClick={limpar}>
            <X aria-hidden /> Limpar seleção
          </Button>
        </>
      )}
      {mostrarFiltrados && (
        <Button size="xs" variant={confirmando === "filtrados" ? "default" : "outline"} className="ml-auto gap-1" onClick={() => executar("filtrados")}>
          <CheckCheck aria-hidden />
          {confirmando === "filtrados" ? `Confirmar aprovar ${pendentesFiltrados.length} do filtro?` : `Aprovar pendentes do filtro (${pendentesFiltrados.length})`}
        </Button>
      )}
    </div>
  )
}
