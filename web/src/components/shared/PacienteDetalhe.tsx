import { daApi } from "@/data/adaptador"
import { useEffect, useRef, useState, type ReactNode } from "react"
import type { Paciente } from "@/data/tipos"
import { CarregandoBloco } from "./Carregando"
import { GraficoCascata } from "./detalhe/GraficoCascata"
import { GraficoComparacao } from "./detalhe/GraficoComparacao"
import { GraficoConfianca } from "./detalhe/GraficoConfianca"
import { GraficoEvolucao } from "./detalhe/GraficoEvolucao"
import { HistoricoPaciente } from "./detalhe/HistoricoPaciente"
import { JustificativaMedico } from "./detalhe/JustificativaMedico"
import { Kpis } from "./detalhe/Kpis"
import { LinhaTempoEventos } from "./detalhe/LinhaTempoEventos"
import { ParametrosIA } from "./detalhe/ParametrosIA"

const ETAPAS = [0, 120, 260, 380, 500, 620, 740, 860, 980]
const JA_CARREGADOS = new Set<string>()

const usarEtapas = (id: string) => {
  const [etapa, setEtapa] = useState(() => (JA_CARREGADOS.has(id) ? ETAPAS.length : 0))
  const anterior = useRef(id)
  useEffect(() => {
    const rapido = JA_CARREGADOS.has(id)
    if (anterior.current !== id) {
      anterior.current = id
      setEtapa(0)
    }
    const escala = rapido ? 0.25 : 1
    const timers = ETAPAS.map((ms, i) => setTimeout(() => setEtapa((e) => Math.max(e, i + 1)), ms * escala))
    const fim = setTimeout(() => JA_CARREGADOS.add(id), ETAPAS[ETAPAS.length - 1] + 50)
    return () => {
      timers.forEach(clearTimeout)
      clearTimeout(fim)
    }
  }, [id])
  return etapa
}

function Etapa({ pronto, rotulo, altura, children, className }: { pronto: boolean; rotulo: string; altura: number; children: ReactNode; className?: string }) {
  if (!pronto) return <CarregandoBloco rotulo={rotulo} altura={altura} className={className} />
  return <>{children}</>
}

export function PacienteDetalhe({ paciente: p }: { paciente: Paciente }) {
  const api = daApi(p)
  const etapa = usarEtapas(p.solicitacao_id)

  return (
    <div className="@container space-y-4" data-paciente={p.solicitacao_id}>
      <div className="space-y-3">
        <Etapa pronto={etapa >= 1} rotulo="Carregando indicadores" altura={120}>
          <Kpis p={p} />
        </Etapa>
        {!api && (
          <Etapa pronto={etapa >= 2} rotulo="Lendo justificativa clínica" altura={180}>
            <JustificativaMedico p={p} />
          </Etapa>
        )}
      </div>

      <div className="grid gap-3 @lg:grid-cols-2">
        <Etapa pronto={etapa >= 3} rotulo="Montando evolução no tempo" altura={310} className="@lg:col-span-2">
          <GraficoEvolucao p={p} />
        </Etapa>
        {/* Cascata, confiança, eventos, parâmetros da IA e histórico ainda não vêm da API (US-21). */}
        {!api && (
          <>
            <Etapa pronto={etapa >= 4} rotulo="Calculando cascata de decisão" altura={330}>
              <GraficoCascata p={p} />
            </Etapa>
            <Etapa pronto={etapa >= 5} rotulo="Medindo confiança" altura={330}>
              <GraficoConfianca p={p} />
            </Etapa>
          </>
        )}
        <Etapa pronto={etapa >= 6} rotulo="Comparando com a classe" altura={300}>
          <GraficoComparacao p={p} />
        </Etapa>
        {!api && (
          <>
            <Etapa pronto={etapa >= 7} rotulo="Reunindo eventos da espera" altura={300}>
              <LinhaTempoEventos p={p} />
            </Etapa>
            <Etapa pronto={etapa >= 8} rotulo="Carregando parâmetros da IA" altura={320} className="@lg:col-span-2">
              <ParametrosIA p={p} />
            </Etapa>
          </>
        )}
      </div>

      {!api && (
        <Etapa pronto={etapa >= 9} rotulo="Buscando histórico do paciente" altura={260}>
          <HistoricoPaciente p={p} />
        </Etapa>
      )}
    </div>
  )
}
