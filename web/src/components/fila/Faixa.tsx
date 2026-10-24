import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { EyeOff, ZoomOut } from "lucide-react"
import { FILA, PACIENTES, PACIENTE_POR_ID, TOTAL_FILA } from "@/data/fila"
import type { Paciente, SlotFila } from "@/data/tipos"
import { COR_STATUS, corClasse } from "@/lib/cores"
import { Button } from "@/components/ui/button"
import { ClasseBadge } from "@/components/shared/Basicos"
import { FILTROS_VAZIOS, aplicarFiltros, statusDe } from "@/lib/filtros"
import { useColunas } from "@/store/colunas"
import { useStore } from "@/store/useStore"

const SOBRA_DETALHE = 12

const MAIS_MUDARAM = [...PACIENTES]
  .sort((a, b) => Math.abs(b.posicao_antiga - b.posicao_nova) - Math.abs(a.posicao_antiga - a.posicao_nova))
  .slice(0, 10)

const passoBonito = (span: number) => {
  const alvo = span / 9
  return [1, 2, 5, 10, 20, 25, 50, 100, 200, 250].find((p) => p >= alvo) ?? 250
}

const caminhoArco = (x1: number, x2: number, yArco: number) => {
  const dist = Math.abs(x2 - x1)
  const altura = Math.max(6, Math.min(68, yArco - 6, Math.max(22, dist * 0.42)))
  return { d: `M ${x1} ${yArco} Q ${(x1 + x2) / 2} ${yArco - altura * 2} ${x2} ${yArco}`, topo: yArco - altura }
}

type Tip = { x: number; slot: SlotFila }

export function Faixa() {
  const ALTURA = useColunas((c) => c.alturaFaixa)
  const setFaixaOculta = useColunas((c) => c.setFaixaOculta)
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
  const [largura, setLargura] = useState(900)
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
  const posDoX = useCallback((x: number) => Math.min(z1, Math.max(z0, Math.floor(x / slot) + z0)), [slot, z0, z1])

  const selecionado: Paciente | undefined = selecionadoId ? PACIENTE_POR_ID[selecionadoId] : undefined

  const focados = useMemo(() => {
    if (JSON.stringify(filtros) === JSON.stringify(FILTROS_VAZIOS)) return null
    return new Set(aplicarFiltros(PACIENTES, filtros, decisoes).map((p) => p.solicitacao_id))
  }, [filtros, decisoes])

  const barras = useMemo(() => {
    const larg = slot >= 4 ? slot - 1.2 : Math.max(0.9, slot * 0.86)
    const visiveis = FILA.filter((s) => s.posicao >= z0 && s.posicao <= z1)
    return visiveis.map((s) => {
      const x = xInicio(s.posicao)
      const p = s.paciente
      if (!p) return <rect key={s.posicao} x={x} y={TOPO_BARRA} width={larg} height={BASE_BARRA - TOPO_BARRA} style={{ fill: "var(--ghost)" }} shapeRendering="crispEdges" />
      const status = statusDe(decisoes, p.solicitacao_id)
      const cx = x + larg / 2
      return (
        <g key={s.posicao}>
          <rect x={x} y={TOPO_BARRA - SOBRA_DETALHE} width={Math.max(larg, 2.6)} height={BASE_BARRA - TOPO_BARRA + SOBRA_DETALHE} style={{ fill: corClasse(p.classe), opacity: focados && !focados.has(p.solicitacao_id) ? 0.18 : 1, transition: "opacity 0.3s" }} shapeRendering="crispEdges" />
          {status === "pendente" && <circle cx={cx} cy={BASE_BARRA + 7} r={2.6} fill="none" strokeWidth={1.2} style={{ stroke: COR_STATUS.pendente }} />}
          {status === "aprovado" && (
            <g className="fx-pop" style={{ transformBox: "fill-box", transformOrigin: "center" }}>
              <circle cx={cx} cy={BASE_BARRA + 7} r={3.4} style={{ fill: COR_STATUS.aprovado }} />
              <path d={`M ${cx - 1.6} ${BASE_BARRA + 7} l 1.2 1.3 l 2.2 -2.6`} fill="none" stroke="white" strokeWidth={1} />
            </g>
          )}
          {status === "rejeitado" && (
            <g className="fx-pop" style={{ transformBox: "fill-box", transformOrigin: "center" }}>
              <rect x={cx - 3.2} y={BASE_BARRA + 3.8} width={6.4} height={6.4} rx={1} style={{ fill: "var(--card)", stroke: COR_STATUS.rejeitado }} strokeWidth={1.6} />
              <path d={`M ${cx - 1.6} ${BASE_BARRA + 5.4} l 3.2 3.2 m 0 -3.2 l -3.2 3.2`} style={{ stroke: COR_STATUS.rejeitado }} strokeWidth={1} />
            </g>
          )}
        </g>
      )
    })
  }, [decisoes, slot, z0, z1, xInicio, TOPO_BARRA, BASE_BARRA, focados])

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
    const x1 = xCentro(selecionado.posicao_antiga)
    const x2 = xCentro(selecionado.posicao_nova)
    return { ...caminhoArco(x1, x2, Y_ARCO), x1, x2, sobe: selecionado.posicao_nova < selecionado.posicao_antiga, igual: selecionado.posicao_nova === selecionado.posicao_antiga }
  }, [selecionado, xCentro, Y_ARCO])

  useEffect(() => {
    if (!selecionado || !zoom) return
    const dentro = (p: number) => p >= zoom[0] && p <= zoom[1]
    if (!dentro(selecionado.posicao_nova)) setZoom(null)
  }, [selecionado, zoom, setZoom])

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
    const slotSobre = FILA[posDoX(x) - 1]
    setTip({ x, slot: slotSobre })
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
    const alvo = FILA[posDoX(x) - 1]
    if (alvo.paciente) selecionar(alvo.paciente.solicitacao_id, true)
    else {
      const proximo = FILA.slice(Math.max(0, posDoX(x) - 3), posDoX(x) + 2).find((s) => s.paciente)
      if (proximo?.paciente && slot < 2.5) selecionar(proximo.paciente.solicitacao_id, true)
    }
  }

  const rotuloArco = selecionado ? `${selecionado.posicao_antiga} → ${selecionado.posicao_nova}` : ""
  const corArco = arco?.sobe ? "var(--sobe)" : "var(--desce)"
  const chaveArco = `${selecionadoId}-${z0}-${z1}-${Math.round(largura / 40)}`

  return (
    <div className="rounded-xl bg-muted/40 p-2">
      <div className="mb-1 flex items-center justify-between gap-2 px-1">
        <div className="text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">Fila inteira</span> · {TOTAL_FILA} posições · {PACIENTES.length} com detalhe · arraste para ampliar
        </div>
        <div className="flex items-center gap-1">
        {zoom && (
          <Button size="xs" variant="outline" onClick={() => setZoom(null)} className="fx-pop gap-1">
            <ZoomOut className="size-3" aria-hidden />
            Resetar zoom ({zoom[0]}–{zoom[1]})
          </Button>
        )}
        <Button size="xs" variant="ghost" onClick={() => setFaixaOculta(true)} className="gap-1 text-muted-foreground" title="Ocultar a faixa da fila">
          <EyeOff className="size-3" aria-hidden />
          Ocultar
        </Button>
        </div>
      </div>
      <div ref={caixa} className="relative w-full select-none" style={{ height: ALTURA }}>
        <svg width={largura} height={ALTURA} role="img" aria-label={`Faixa da fila com ${TOTAL_FILA} posições${selecionado ? `; paciente ${selecionado.solicitacao_id} vai da posição ${selecionado.posicao_antiga} para ${selecionado.posicao_nova}` : ""}`} className="block overflow-visible">
          <defs>
            <linearGradient id="gradiente-cometa" x1="0" x2="1">
              <stop offset="0" stopColor="white" stopOpacity="0" />
              <stop offset="1" stopColor="white" stopOpacity="1" />
            </linearGradient>
          </defs>
          <g className="fx-grow-y" style={{ transformBox: "fill-box", transformOrigin: "center bottom" }}>
            {barras}
          </g>

          {MAIS_MUDARAM.filter((p) => p.solicitacao_id !== selecionadoId).map((p, i) => {
            const a = xCentro(p.posicao_antiga)
            const b = xCentro(p.posicao_nova)
            const { d } = caminhoArco(a, b, Y_ARCO)
            return (
              <path
                key={`${p.solicitacao_id}-${z0}-${z1}`}
                d={d}
                pathLength={1}
                fill="none"
                strokeWidth={1.1}
                opacity={0.3}
                className="pointer-events-none"
                style={{ stroke: p.posicao_nova < p.posicao_antiga ? "var(--sobe)" : "var(--desce)", strokeDasharray: 1, "--len": 1, animation: `fx-draw 1.1s ease-out ${0.2 + i * 0.09}s both` } as React.CSSProperties}
              />
            )
          })}

          {selecionado && (
            <rect
              key={`sel-${chaveArco}`}
              x={xInicio(selecionado.posicao_nova) - 1.5}
              y={TOPO_BARRA - SOBRA_DETALHE - 2}
              width={Math.max(slot, 2) + 3}
              height={BASE_BARRA - TOPO_BARRA + SOBRA_DETALHE + 4}
              fill="none"
              strokeWidth={1.6}
              className="fx-pop"
              style={{ stroke: "var(--foreground)", transformBox: "fill-box", transformOrigin: "center" }}
            />
          )}

          {selecionado && arco && !arco.igual && (
            <g key={`arco-${chaveArco}`} className="pointer-events-none">
              <path d={arco.d} fill="none" strokeWidth={5} opacity={0.14} strokeLinecap="round" style={{ stroke: corArco }} />
              <path d={arco.d} pathLength={1} fill="none" strokeWidth={2.4} strokeLinecap="round" style={{ stroke: corArco, strokeDasharray: 1, "--len": 1, animation: "fx-draw 0.9s cubic-bezier(0.3,0.7,0.2,1) both" } as React.CSSProperties} />
              {[0, 0.8].map((atraso) => (
                <path key={atraso} d={arco.d} pathLength={100} fill="none" strokeWidth={4.2} strokeLinecap="round" style={{ stroke: "white", strokeDasharray: "5 95", opacity: 0.85, animation: `fx-comet 1.6s linear ${0.9 + atraso}s infinite` }} />
              ))}
              <path d={arco.d} pathLength={100} fill="none" strokeWidth={1.6} strokeLinecap="round" style={{ stroke: corArco, strokeDasharray: "18 82", filter: "brightness(1.25)", animation: "fx-comet 2.6s linear 0.9s infinite" }} />
              <polygon points={`${arco.x2 - 6},${Y_ARCO - 10} ${arco.x2 + 6},${Y_ARCO - 10} ${arco.x2},${Y_ARCO + 1}`} className="fx-pop" style={{ fill: corArco, transformBox: "fill-box", transformOrigin: "center bottom", animationDelay: "0.8s" }} />
              {[0, 0.7].map((atraso) => (
                <circle key={atraso} cx={arco.x2} cy={Y_ARCO + 2} r={3} fill="none" strokeWidth={1.6} style={{ stroke: corArco, animation: `fx-ripple 1.8s ease-out ${1 + atraso}s infinite` }} />
              ))}
              <circle cx={arco.x1} cy={Y_ARCO + 2} r={3} className="fx-pop" style={{ fill: "var(--card)", stroke: corArco }} strokeWidth={1.6} />
              <g transform={`translate(${Math.min(largura - 50, Math.max(50, (arco.x1 + arco.x2) / 2))}, ${Math.max(12, arco.topo - 11)})`} className="fx-fade-up">
                <rect x={-42} y={-11} width={84} height={22} rx={11} style={{ fill: "var(--card)", stroke: corArco }} strokeWidth={1.5} />
                <text textAnchor="middle" dy={4.5} fontSize={12} fontWeight={700} style={{ fill: "var(--foreground)" }} className="tabular-nums">
                  {rotuloArco}
                </text>
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
            posição atual
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
          <div className="pointer-events-none absolute z-20 w-56 rounded-md border bg-popover p-2 text-xs shadow-md fx-fade-up" style={{ left: Math.min(Math.max(0, tip.x - 112), Math.max(0, largura - 224)), top: 0 }}>
            {tip.slot.paciente ? (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span className="font-semibold">{tip.slot.paciente.solicitacao_id}</span>
                  <ClasseBadge classe={tip.slot.paciente.classe} />
                </div>
                <div className="mt-1 text-muted-foreground">
                  {tip.slot.paciente.iniciais} · {tip.slot.paciente.procedimento}
                </div>
                <div className="mt-1 font-medium tabular-nums">
                  Posição {tip.slot.paciente.posicao_antiga} → {tip.slot.paciente.posicao_nova}
                </div>
              </>
            ) : (
              <div className="text-muted-foreground">
                Posição <span className="font-semibold text-foreground tabular-nums">{tip.slot.posicao}</span> · classe {tip.slot.fantasma?.classe} · sem detalhe
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
