import { useEffect, useLayoutEffect, useRef, useState } from "react"
import { Faixa } from "./Faixa"
import { FiltrosFila } from "./FiltrosFila"
import { PainelAprovacao } from "./PainelAprovacao"
import { Eye } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useColunas } from "@/store/colunas"
import { PainelDrawer } from "./PainelDrawer"
import { useStore } from "@/store/useStore"
import { BarraSelecao } from "./BarraSelecao"
import { CabecalhoTabela, CorpoTabela, useTabela } from "./TabelaFila"

const useMd = () => {
  const consulta = "(min-width: 768px)"
  const [md, setMd] = useState(() => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(consulta).matches : true))
  useEffect(() => {
    const m = window.matchMedia(consulta)
    const aoMudar = () => setMd(m.matches)
    m.addEventListener("change", aoMudar)
    return () => m.removeEventListener("change", aoMudar)
  }, [])
  return md
}

export default function PaginaFila() {
  const rolagem = useRef<HTMLDivElement>(null)
  const fixo = useRef<HTMLDivElement>(null)
  const [alturaFixa, setAlturaFixa] = useState(300)
  const { table, total, visiveis } = useTabela()
  const oculta = useColunas((c) => c.faixaOculta)
  const setOculta = useColunas((c) => c.setFaixaOculta)
  const filtros = useStore((s) => s.filtros)
  const md = useMd()
  const [abertaMobile, setAbertaMobile] = useState(false)
  const escondida = md ? oculta : !abertaMobile
  const mostrar = () => (md ? setOculta(false) : setAbertaMobile(true))
  const esconder = () => (md ? setOculta(true) : setAbertaMobile(false))

  useLayoutEffect(() => {
    const el = fixo.current
    if (!el) return
    setAlturaFixa(el.offsetHeight)
    const obs = new ResizeObserver(() => setAlturaFixa(el.offsetHeight))
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <div className="flex min-h-0 flex-1">
      <div ref={rolagem} className="relative min-w-0 flex-1 overflow-y-auto">
        <div>
          <div className="px-3 pt-3">
            {escondida ? (
              <div className="flex items-center justify-between rounded-xl bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
                <span>Gráfico da fila</span>
                <Button size="xs" variant="ghost" className="gap-1 max-md:h-9" onClick={mostrar}>
                  <Eye className="size-3" aria-hidden />
                  Mostrar gráfico
                </Button>
              </div>
            ) : (
              <Faixa aoOcultar={esconder} />
            )}
          </div>
          <div ref={fixo} className="sticky top-0 z-10 space-y-1 bg-background px-3 pt-2 pb-0">
            <FiltrosFila total={total} visiveis={visiveis} />
            <BarraSelecao />
            <CabecalhoTabela table={table} />
          </div>
          <div className="px-3 pb-8 max-lg:pb-20">
            <CorpoTabela key={`${visiveis}-${JSON.stringify(filtros)}`} table={table} rolagemRef={rolagem} alturaFixa={alturaFixa} />
          </div>
          <BarraSelecao rodape />
        </div>
      </div>
      <PainelAprovacao className="hidden lg:flex" />
      <PainelDrawer />
    </div>
  )
}
