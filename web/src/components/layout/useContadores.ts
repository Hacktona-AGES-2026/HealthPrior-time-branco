import { useEffect, useMemo, useState } from "react"
import { listarPendencias } from "@/api/cliente"
import { ORIGEM_DADOS, PACIENTES } from "@/data/fila"
import { useStore } from "@/store/useStore"

export type Contadores = { paraRevisar: number | null; pendencias: number | null; pendenciasBloqueantes: boolean }

/** Contadores discretos da sidebar. Só existem com dados vindos da API; erros ficam silenciosos (sem contador). */
export function useContadores(): Contadores {
  const decisoes = useStore((s) => s.decisoes)
  const pagina = useStore((s) => s.pagina)
  const versaoDados = useStore((s) => s.versaoDados)
  const [pend, setPend] = useState<{ total: number; bloqueantes: number } | null>(null)

  const paraRevisar = useMemo(() => {
    if (ORIGEM_DADOS !== "api") return null
    return PACIENTES.filter((p) => p.inbox && !decisoes[p.id]).length
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [decisoes, versaoDados])

  useEffect(() => {
    if (ORIGEM_DADOS !== "api") return
    const ctrl = new AbortController()
    Promise.all([
      listarPendencias({ status: "aberta" }, ctrl.signal),
      listarPendencias({ status: "aberta", bloqueante: true }, ctrl.signal),
    ])
      .then(([todas, bloq]) => setPend({ total: todas.total ?? todas.itens.length, bloqueantes: bloq.total ?? bloq.itens.length }))
      .catch(() => { if (!ctrl.signal.aborted) setPend(null) })
    return () => ctrl.abort()
  }, [pagina, versaoDados])

  return { paraRevisar, pendencias: pend ? pend.total : null, pendenciasBloqueantes: (pend?.bloqueantes ?? 0) > 0 }
}

export const formatarContador = (n: number) => (n > 999 ? "999+" : n.toLocaleString("pt-BR"))
