import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { CircleHelp, EyeOff, ZoomIn, ZoomOut } from "lucide-react"
import { FILA, PACIENTES, PACIENTE_POR_ID, TOTAL_FILA } from "@/data/fila"
import type { Classe, Paciente } from "@/data/tipos"
import { COR_STATUS, corClasse } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { ClasseBadge } from "@/components/shared/Basicos"
import { FILTROS_VAZIOS, aplicarFiltros, statusDe } from "@/lib/filtros"
import { useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

const SOBRA_DETALHE = 12

const LARGURA_BLOCO = 10

const CLASSES_ORDEM: Classe[] = ["A1", "A2", "B", "C", "D"]

type Bloco = {
  indice: number
  de: number
  ate: number
  total: number
  porClasse: Record<Classe, number>
  fora: number
  subiram: number
  desceram: number
  saltoMedio: number
  origemMedia: number
  incluidos: number
  revisados: number
  porCamada: Record<1 | 2 | 3, number>
}

const passoBonito = (span: number) => {
  const alvo = span / 9
  return [1, 2, 5, 10, 20, 25, 50, 100, 200, 250].find((p) => p >= alvo) ?? 250
}

const caminhoArco = (x1: number, x2: number, yArco: number) => {
  const dist = Math.abs(x2 - x1)
  const altura = Math.max(6, Math.min(68, yArco - 6, Math.max(22, dist * 0.42)))
  return { d: `M ${x1} ${yArco} Q ${(x1 + x2) / 2} ${yArco - altura * 2} ${x2} ${yArco}`, topo: yArco - altura }
}

type Tip = { x: number; paciente?: Paciente; bloco?: Bloco }

export function Faixa({ aoOcultar }: { aoOcultar?: () => void } = {}) {
  const versaoDados = useStore((s) => s.versaoDados)
  const POR_SALTO = useMemo(() => [...PACIENTES].sort((a, b) => Math.abs(b.posicao_atual - b.posicao) - Math.abs(a.posicao_atual - a.posicao)), [versaoDados])
  const [largura, setLargura] = useState(900)
  const [ajuda, setAjuda] = useState(false)
  const alturaStore = useColunas((c) => c.alturaFaixa)
  const setFaixaOculta = useColunas((c) => c.setFaixaOculta)
  const ALTURA = largura < 480 ? Math.min(alturaStore, 150) : alturaStore
  const TOPO_BARRA = ALTURA - 100
  const BASE_BARRA = TOPO_BARRA + 46
  const Y_ARCO = TOPO_BARRA - SOBRA_DETALHE - 3
  const selecionadoId = useStore((s) => s.selecionadoId)
  const filtros = useStore((s) => s.filtros)
  const zoom = useStore((s) => s.zoom)
  const decisoes = useStore((s) => s.decisoes)
  const setZoom = useStore((s) => s.setZoom)
  const selecionar = useStore((s) => s.selecionar)
  const caixa = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<Tip | null>(null)
  const [arrasto, setArrasto] = useState<{ x0: number; x1: number } | null>(null)
  const inicioArrasto = useRef<number | null>(null)

  useLayoutEffect(() => {
    const el = caixa.current
    if (!el) return
    setLargura(el.clientWidth)
    const obs = new ResizeObserver(() => setLargura(el.clientWidth))
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const [z0, z1] = zoom ?? [1, TOTAL_FILA]
  const span = z1 - z0 + 1
  const slot = largura / span
  const xInicio = useCallback((pos: number) => (pos - z0) * slot, [z0, slot])
  const xCentro = useCallback((pos: number) => Math.min(largura, Math.max(0, (pos - z0 + 0.5) * slot)), [z0, slot, largura])
  const aplicarZoom = useCallback(
    (centro: number, fator: number) => {
      const atual = z1 - z0 + 1
      const novo = Math.round(atual * fator)
      if (novo >= TOTAL_FILA) {
        setZoom(null)
        return
      }
      const tam = Math.max(20, novo)
      const ini = Math.min(TOTAL_FILA - tam + 1, Math.max(1, Math.round(centro - tam / 2)))
      setZoom([ini, ini + tam - 1])
    },
    [z0, z1, setZoom]
  )
  const posDoX = useCallback((x: number) => Math.min(z1, Math.max(z0, Math.floor(x / slot) + z0)), [slot, z0, z1])

  const selecionado: Paciente | undefined = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  const centralizar = () => {
    if (!selecionado) return
    const tam = zoom ? z1 - z0 + 1 : 150
    const ini = Math.min(TOTAL_FILA - tam + 1, Math.max(1, Math.round(selecionado.posicao - tam / 2)))
    setZoom([ini, ini + tam - 1])
  }

  useEffect(() => {
    const el = caixa.current
    if (!el) return
    const aoRolar = (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return
      e.preventDefault()
      const x = e.clientX - el.getBoundingClientRect().left
      aplicarZoom(posDoX(x), e.deltaY < 0 ? 0.8 : 1.25)
    }
    el.addEventListener("wheel", aoRolar, { passive: false })
    return () => el.removeEventListener("wheel", aoRolar)
  }, [aplicarZoom, posDoX])

  const aoTeclar = (e: React.KeyboardEvent) => {
    const alvo = selecionado?.posicao ?? z0
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault()
      e.stopPropagation()
      const prox = Math.min(TOTAL_FILA, Math.max(1, alvo + (e.key === "ArrowRight" ? 1 : -1)))
      selecionar(FILA[prox - 1].id, true)
    } else if (e.key === "+" || e.key === "=") aplicarZoom(alvo, 0.7)
    else if (e.key === "-") aplicarZoom(alvo, 1.4)
    else if (e.key === "Home") setZoom(null)
    else if (e.key.toLowerCase() === "c") centralizar()
  }

  const focados = useMemo(() => {
    if (JSON.stringify(filtros) === JSON.stringify(FILTROS_VAZIOS)) return null
    return new Set(aplicarFiltros(PACIENTES, filtros, decisoes).map((p) => p.id))
  }, [filtros, decisoes])

  const agregado = slot < 3
  const nBlocos = Math.max(10, Math.floor(largura / LARGURA_BLOCO))
  const larguraBloco = largura / nBlocos

  const blocos = useMemo<Bloco[]>(() => {
    if (!agregado) return []
    return Array.from({ length: nBlocos }, (_, i) => {
      const de = z0 + Math.floor((i * span) / nBlocos)
      const ate = Math.max(de, z0 + Math.floor(((i + 1) * span) / nBlocos) - 1)
      const itens = FILA.slice(de - 1, ate)
      const porClasse = { A1: 0, A2: 0, B: 0, C: 0, D: 0 } as Record<Classe, number>
      const porCamada = { 1: 0, 2: 0, 3: 0 } as Record<1 | 2 | 3, number>
      let fora = 0
      let subiram = 0
      let desceram = 0
      let soma = 0
      let revisados = 0
      let somaOrigem = 0
      itens.forEach((p) => {
        if (focados && !focados.has(p.id)) fora++
        else {
          porClasse[p.classe]++
          somaOrigem += p.posicao_atual
        }
        porCamada[p.camada]++
        const delta = p.posicao_atual - p.posicao
        soma += delta
        if (delta > 0) subiram++
        else if (delta < 0) desceram++
        if (decisoes[p.id]) revisados++
      })
      return { indice: i, de, ate, total: itens.length, porClasse, fora, subiram, desceram, saltoMedio: itens.length ? soma / itens.length : 0, origemMedia: itens.length - fora > 0 ? somaOrigem / (itens.length - fora) : 0, incluidos: itens.length - fora, revisados, porCamada }
    })
  }, [agregado, nBlocos, z0, span, focados, decisoes])

  const barras = useMemo(() => {
    if (agregado) return []
    const larg = slot >= 4 ? slot - 1.2 : Math.max(0.9, slot * 0.86)
    const visiveis = FILA.slice(z0 - 1, z1)
    return visiveis.map((p) => {
      const x = xInicio(p.posicao)
      const status = statusDe(decisoes, p.id)
      const cx = x + larg / 2
      const destaque = focados ? focados.has(p.id) : true
      return (
        <g key={p.posicao}>
          <rect
            x={x}
            y={TOPO_BARRA - (destaque ? SOBRA_DETALHE : 0)}
            width={Math.max(larg, destaque ? 2.6 : 1)}
            height={BASE_BARRA - TOPO_BARRA + (destaque ? SOBRA_DETALHE : 0)}
            style={{ fill: destaque ? corClasse(p.classe) : "var(--ghost)" }}
            shapeRendering="crispEdges"
          />
          {status === "pendente" && slot >= 7 && <circle cx={cx} cy={BASE_BARRA + 7} r={2.6} fill="none" strokeWidth={1.2} style={{ stroke: COR_STATUS.pendente }} />}
          {status === "aprovado" && (
            <g style={{ transformBox: "fill-box", transformOrigin: "center" }}>
              <circle cx={cx} cy={BASE_BARRA + 7} r={3.4} style={{ fill: COR_STATUS.aprovado }} />
              <path d={`M ${cx - 1.6} ${BASE_BARRA + 7} l 1.2 1.3 l 2.2 -2.6`} fill="none" stroke="white" strokeWidth={1} />
            </g>
          )}
          {status === "editado" && (
            <g style={{ transformBox: "fill-box", transformOrigin: "center" }}>
              <rect x={cx - 3.2} y={BASE_BARRA + 3.8} width={6.4} height={6.4} rx={1} style={{ fill: "var(--card)", stroke: COR_STATUS.editado }} strokeWidth={1.6} />
              <path d={`M ${cx - 1.6} ${BASE_BARRA + 5.4} l 3.2 3.2 m 0 -3.2 l -3.2 3.2`} style={{ stroke: COR_STATUS.editado }} strokeWidth={1} />
            </g>
          )}
        </g>
      )
    })
  }, [agregado, decisoes, slot, z0, z1, xInicio, TOPO_BARRA, BASE_BARRA, focados])

  const blocoDe = tip?.bloco?.de
  const blocoAte = tip?.bloco?.ate
  const blocoAtivo = tip?.bloco?.indice
  const pacienteAtivo = tip?.paciente?.id
  const arcosVivos = useMemo(() => {
    const vivo = blocoAtivo !== undefined || pacienteAtivo !== undefined
    let base: Paciente[]
    if (blocoAtivo !== undefined && blocoDe !== undefined && blocoAte !== undefined) base = FILA.slice(blocoDe - 1, blocoAte)
    else if (pacienteAtivo) base = [PACIENTE_POR_ID[pacienteAtivo]]
    else if (focados) base = POR_SALTO.filter((p) => focados.has(p.id))
    else base = POR_SALTO
    const limite = vivo ? 14 : focados ? 8 : 5
    const lista = base
      .filter((p) => p.id !== selecionadoId && p.posicao !== p.posicao_atual)
      .sort((a, b) => Math.abs(b.posicao_atual - b.posicao) - Math.abs(a.posicao_atual - a.posicao))
      .slice(0, limite)
    return { vivo, lista }
  }, [blocoAtivo, blocoDe, blocoAte, pacienteAtivo, focados, selecionadoId, POR_SALTO])

  const ticks = useMemo(() => {
    const passo = passoBonito(span)
    const lista: number[] = [z0]
    for (let t = Math.ceil(z0 / passo) * passo; t < z1; t += passo) {
      if (t - z0 > span * 0.04 && z1 - t > span * 0.04) lista.push(t)
    }
    lista.push(z1)
    return lista
  }, [z0, z1, span])

  const arco = useMemo(() => {
    if (!selecionado) return null
    const x1 = xCentro(selecionado.posicao_atual)
    const x2 = xCentro(selecionado.posicao)
    return { ...caminhoArco(x1, x2, Y_ARCO), x1, x2, sobe: selecionado.posicao < selecionado.posicao_atual, igual: selecionado.posicao === selecionado.posicao_atual }
  }, [selecionado, xCentro, Y_ARCO])

  const coordenada = (e: React.PointerEvent) => e.clientX - (caixa.current?.getBoundingClientRect().left ?? 0)

  const aoPressionar = (e: React.PointerEvent) => {
    inicioArrasto.current = coordenada(e)
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const aoMover = (e: React.PointerEvent) => {
    const x = coordenada(e)
    if (inicioArrasto.current !== null && Math.abs(x - inicioArrasto.current) > 5) {
      setArrasto({ x0: inicioArrasto.current, x1: x })
      setTip(null)
      return
    }
    if (agregado) setTip({ x, bloco: blocos[Math.min(nBlocos - 1, Math.floor(x / larguraBloco))] })
    else setTip({ x, paciente: FILA[posDoX(x) - 1] })
  }

  const aoSoltar = (e: React.PointerEvent) => {
    const x = coordenada(e)
    const x0 = inicioArrasto.current
    inicioArrasto.current = null
    setArrasto(null)
    if (x0 === null) return
    if (Math.abs(x - x0) > 5) {
      const a = posDoX(Math.min(x0, x))
      const b = posDoX(Math.max(x0, x))
      if (b - a >= 4) setZoom([a, b])
      return
    }
    if (agregado) {
      const b = blocos[Math.min(nBlocos - 1, Math.floor(x / larguraBloco))]
      const centro = Math.round((b.de + b.ate) / 2)
      const tam = 80
      const ini = Math.min(TOTAL_FILA - tam + 1, Math.max(1, centro - tam / 2))
      setZoom([ini, ini + tam - 1])
      return
    }
    selecionar(FILA[posDoX(x) - 1].id, true)
  }

  const rotuloArco = selecionado ? `${selecionado.posicao_atual} → ${selecionado.posicao}` : ""
  const corArco = arco?.sobe ? "var(--sobe)" : "var(--desce)"
  const chaveArco = `${selecionadoId}-${z0}-${z1}-${Math.round(largura / 40)}`

  return (
    <div className="rounded-xl bg-muted/40 p-2">
      <div className="mb-1 flex items-center justify-between gap-2 px-1">
        <div className="flex min-w-0 items-center gap-1 text-xs text-muted-foreground">
          <span className="truncate">
            <span className="font-semibold text-foreground">Fila proposta</span> · {TOTAL_FILA}
          </span>
          <Button
            size="icon-xs"
            variant="ghost"
            className="text-muted-foreground max-md:size-9"
            onClick={() => setAjuda((v) => !v)}
            aria-expanded={ajuda}
            aria-label="Como ler a faixa"
            title="Como ler a faixa"
          >
            <CircleHelp aria-hidden />
          </Button>
        </div>
        <div className="flex shrink-0 items-center gap-0.5" role="group" aria-label="Controles da faixa">
          <Button size="icon-xs" variant="ghost" className="text-muted-foreground max-md:size-9" onClick={() => aplicarZoom(selecionado?.posicao ?? (z0 + z1) / 2, 0.6)} title="Ampliar (+ ou Ctrl+roda)" aria-label="Ampliar a faixa">
            <ZoomIn aria-hidden />
          </Button>
          <Button size="icon-xs" variant="ghost" className="text-muted-foreground max-md:size-9" onClick={() => aplicarZoom(selecionado?.posicao ?? (z0 + z1) / 2, 1.6)} title="Reduzir (-)" aria-label="Reduzir a faixa">
            <ZoomOut aria-hidden />
          </Button>
          {zoom && (
            <Button size="xs" variant="outline" onClick={() => setZoom(null)} className="gap-1 max-md:h-9" aria-label="Ver a fila inteira (tirar o zoom)">
              <ZoomOut className="size-3" aria-hidden />
              Ver tudo
            </Button>
          )}
          <Button size="xs" variant="ghost" onClick={aoOcultar ?? (() => setFaixaOculta(true))} className="gap-1 text-muted-foreground max-md:h-9" title="Ocultar a faixa da fila" aria-label="Ocultar faixa">
            <EyeOff className="size-3" aria-hidden />
            <span>Ocultar faixa</span>
          </Button>
        </div>
      </div>
      {ajuda && (
        <p className="mb-1 px-1 text-xs text-muted-foreground">
          Cada coluna é um grupo de posições; clique para ampliar.</p>
      )}
      <div ref={caixa} className="relative w-full rounded-lg outline-none select-none focus-visible:ring-2 focus-visible:ring-ring" style={{ height: ALTURA }} tabIndex={0} onKeyDown={aoTeclar} aria-label="Faixa da fila: setas trocam o paciente, + e - dão zoom, C centraliza, Home reseta">
        <svg width={largura} height={ALTURA} role="img" aria-label={`Faixa da fila com ${TOTAL_FILA} posições${selecionado ? `; paciente ${selecionado.id} vai da posição ${selecionado.posicao_atual} para ${selecionado.posicao}` : ""}`} className="block overflow-visible">
          <defs>
            <linearGradient id="gradiente-cometa" x1="0" x2="1">
              <stop offset="0" stopColor="white" stopOpacity="0" />
              <stop offset="1" stopColor="white" stopOpacity="1" />
            </linearGradient>
          </defs>
          <g style={{ transformBox: "fill-box", transformOrigin: "center bottom" }}>
            {barras}
            {blocos.map((b) => {
              const altura = BASE_BARRA - TOPO_BARRA
              const x = b.indice * larguraBloco
              const largBloco = Math.max(1, larguraBloco - 1.5)
              let y = BASE_BARRA
              const segmentos: { cor: string; h: number; chave: string }[] = []
              if (b.fora > 0) segmentos.push({ cor: "var(--ghost)", h: (b.fora / b.total) * altura, chave: "fora" })
              ;[...CLASSES_ORDEM].reverse().forEach((c) => {
                if (b.porClasse[c] > 0) segmentos.push({ cor: corClasse(c), h: (b.porClasse[c] / b.total) * altura, chave: c })
              })
              const selecionadoAqui = selecionado && selecionado.posicao >= b.de && selecionado.posicao <= b.ate
              return (
                <g key={b.indice}>
                  {segmentos.map((sg) => {
                    y -= sg.h
                    return <rect key={sg.chave} x={x} y={y} width={largBloco} height={sg.h} style={{ fill: sg.cor }} shapeRendering="crispEdges" />
                  })}
                  {selecionadoAqui && <rect x={x - 1} y={TOPO_BARRA - 3} width={largBloco + 2} height={altura + 6} fill="none" strokeWidth={1.6} rx={2} style={{ stroke: "var(--foreground)" }} />}
                  <rect x={x} y={BASE_BARRA + 4} width={largBloco} height={4} rx={1} style={{ fill: b.saltoMedio >= 0 ? "var(--sobe)" : "var(--desce)", opacity: 0.12 + 0.88 * Math.min(1, Math.abs(b.saltoMedio) / 300) }} />
                  <rect x={x} y={BASE_BARRA + 11} width={largBloco} height={2} rx={1} style={{ fill: "var(--muted)" }} />
                  {b.revisados > 0 && <rect x={x} y={BASE_BARRA + 11} width={largBloco * (b.revisados / b.total)} height={2} rx={1} style={{ fill: COR_STATUS.aprovado }} />}
                </g>
              )
            })}
          </g>

          {agregado &&
            blocos.map((b) => {
              if (b.incluidos === 0 || Math.abs(b.origemMedia - (b.de + b.ate) / 2) < 12) return null
              const a = xCentro(b.origemMedia)
              const c = b.indice * larguraBloco + larguraBloco / 2
              const { d } = caminhoArco(a, c, Y_ARCO)
              const sobe = b.origemMedia > (b.de + b.ate) / 2
              const forca = Math.min(1, Math.abs(b.origemMedia - (b.de + b.ate) / 2) / 400)
              const ativo = blocoAtivo === b.indice
              return (
                <path
                  key={`fluxo-${b.indice}-${z0}-${z1}`}
                  d={d}
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray="5 9"
                  strokeWidth={ativo ? 2.4 : 0.8 + forca * 1.2}
                  className="pointer-events-none"
                  style={{ stroke: sobe ? "var(--sobe)" : "var(--desce)", opacity: ativo ? 0.9 : 0.14 + forca * 0.3 }}
                />
              )
            })}

          {(!agregado || arcosVivos.vivo ? arcosVivos.lista : []).map((p) => {
            const a = xCentro(p.posicao_atual)
            const b = xCentro(p.posicao)
            const { d } = caminhoArco(a, b, Y_ARCO)
            const cor = p.posicao < p.posicao_atual ? "var(--sobe)" : "var(--desce)"
            return (
              <g key={`${p.id}-${z0}-${z1}-${arcosVivos.vivo}`} className="pointer-events-none">
                <path
                  d={d}
                  pathLength={1}
                  fill="none"
                  strokeWidth={arcosVivos.vivo ? 1.8 : 1.1}
                  opacity={arcosVivos.vivo ? 0.65 : 0.3}
                  strokeLinecap="round"
                  style={{ stroke: cor, strokeDasharray: 1 }}
                />
                {arcosVivos.vivo && (
                  <>
                    <circle cx={b} cy={Y_ARCO + 2} r={2.6} style={{ fill: cor }} />
                  </>
                )}
              </g>
            )
          })}

          {selecionado && !agregado && (
            <rect
              key={`sel-${chaveArco}`}
              x={xInicio(selecionado.posicao) - 1.5}
              y={TOPO_BARRA - SOBRA_DETALHE - 2}
              width={Math.max(slot, 2) + 3}
              height={BASE_BARRA - TOPO_BARRA + SOBRA_DETALHE + 4}
              fill="none"
              strokeWidth={1.6}
             
              style={{ stroke: "var(--foreground)", transformBox: "fill-box", transformOrigin: "center" }}
            />
          )}

          {selecionado && arco && !arco.igual && (
            <g key={`arco-${chaveArco}`} className="pointer-events-none">
              <path d={arco.d} fill="none" strokeWidth={5} opacity={0.14} strokeLinecap="round" style={{ stroke: corArco }} />
              <path d={arco.d} pathLength={1} fill="none" strokeWidth={2.4} strokeLinecap="round" style={{ stroke: corArco, strokeDasharray: 1 }} />
              <polygon points={`${arco.x2 - 6},${Y_ARCO - 10} ${arco.x2 + 6},${Y_ARCO - 10} ${arco.x2},${Y_ARCO + 1}`} style={{ fill: corArco, transformBox: "fill-box", transformOrigin: "center bottom" }} />
              <circle cx={arco.x1} cy={Y_ARCO + 2} r={3} style={{ fill: "var(--card)", stroke: corArco }} strokeWidth={1.6} />
              <g transform={`translate(${Math.min(largura - 50, Math.max(50, (arco.x1 + arco.x2) / 2))}, ${Math.max(14, arco.topo - 12)})`}>
                <g>
                  <rect x={-46} y={-11} width={92} height={22} rx={11} style={{ fill: "var(--card)", stroke: corArco }} strokeWidth={1.5} />
                  <text textAnchor="middle" dy={4.5} fontSize={12} fontWeight={700} style={{ fill: "var(--foreground)" }} className="tabular-nums">
                    {rotuloArco}
                  </text>
                </g>
              </g>
            </g>
          )}

          <line x1={0} x2={largura} y1={BASE_BARRA + 16} y2={BASE_BARRA + 16} style={{ stroke: "var(--border)" }} />
          {ticks.map((t) => {
            const anchor = t === z0 ? "start" : t === z1 ? "end" : "middle"
            const x = t === z0 ? 0 : t === z1 ? largura : xCentro(t)
            return (
              <g key={t}>
                <line x1={x} x2={x} y1={BASE_BARRA + 16} y2={BASE_BARRA + 21} style={{ stroke: "var(--muted-foreground)" }} />
                <text x={x} y={BASE_BARRA + 32} textAnchor={anchor} fontSize={10.5} className="tabular-nums" style={{ fill: "var(--muted-foreground)" }}>
                  {t}
                </text>
              </g>
            )
          })}
          <text x={largura / 2} y={ALTURA - 4} textAnchor="middle" fontSize={10.5} style={{ fill: "var(--muted-foreground)" }}>
            posição na fila proposta
          </text>

          {arrasto && (
            <rect x={Math.min(arrasto.x0, arrasto.x1)} y={TOPO_BARRA - 20} width={Math.abs(arrasto.x1 - arrasto.x0)} height={BASE_BARRA - TOPO_BARRA + 34} rx={3} style={{ fill: "color-mix(in oklab, var(--primary) 20%, transparent)", stroke: "var(--primary)" }} strokeDasharray="4 3" />
          )}
          <rect
            x={0}
            y={0}
            width={largura}
            height={BASE_BARRA + 16}
            fill="transparent"
            className="cursor-crosshair"
            onPointerDown={aoPressionar}
            onPointerMove={aoMover}
            onPointerUp={aoSoltar}
            onPointerLeave={() => setTip(null)}
          />
        </svg>
        {tip && !arrasto && (
          <div className="pointer-events-none absolute z-20 w-56 rounded-md border bg-popover p-2 text-xs shadow-md" style={{ left: Math.min(Math.max(0, tip.x - 112), Math.max(0, largura - 224)), top: BASE_BARRA + 22 }}>
            {tip.paciente && (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{tip.paciente.id}</span>
                  <ClasseBadge classe={tip.paciente.classe} />
                </div>
                <div className="mt-1 text-muted-foreground">
                  {tip.paciente.iniciais} · {tip.paciente.procedimento}
                </div>
                <div className="mt-1 font-medium tabular-nums">
                  Atual #{tip.paciente.posicao_atual} → proposta #{tip.paciente.posicao} · camada {tip.paciente.camada}
                </div>
              </>
            )}
            {tip.bloco && (
              <>
                <div className="font-semibold tabular-nums">
                  Posições {tip.bloco.de}–{tip.bloco.ate} · {tip.bloco.total} solicitações
                </div>
                <div className="mt-1.5 flex flex-wrap gap-1">
                  {CLASSES_ORDEM.filter((c) => tip.bloco!.porClasse[c] > 0).map((c) => (
                    <span key={c} className="inline-flex items-center gap-1">
                      <ClasseBadge classe={c} />
                      <span className="tabular-nums">{tip.bloco!.porClasse[c]}</span>
                    </span>
                  ))}
                </div>
                <div className="mt-1.5 text-muted-foreground tabular-nums">
                  Camadas: {tip.bloco.porCamada[1]} onc · {tip.bloco.porCamada[2]} urg · {tip.bloco.porCamada[3]} demais
                </div>
                <div className="mt-1 tabular-nums">
                  <span style={{ color: "var(--sobe)" }}>▲ {tip.bloco.subiram} subiram</span> · <span style={{ color: "var(--desce)" }}>▼ {tip.bloco.desceram} desceram</span>
                </div>
                <div className="mt-1 text-muted-foreground tabular-nums">Revisados: {tip.bloco.revisados} de {tip.bloco.total}</div>
                <div className="mt-1 text-xs text-muted-foreground">Clique para ampliar</div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
