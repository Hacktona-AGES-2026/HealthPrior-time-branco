import { useEffect, useRef, useState, type ReactNode } from "react"
import { ORIGEM_DADOS } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { DetalheApiPaciente } from "./detalhe/DetalheApi"
import { CarregandoBloco } from "./Carregando"
import { CartaCamada } from "./detalhe/CartaCamada"
import { DadosSistema } from "./detalhe/DadosSistema"
import { GraficoEspera } from "./detalhe/GraficoEspera"
import { HistoricoPaciente } from "./detalhe/HistoricoPaciente"
import { JustificativaMedico } from "./detalhe/JustificativaMedico"
import { Kpis } from "./detalhe/Kpis"

const ETAPAS = [0, 120, 260, 400, 540, 680]
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
  const etapa = usarEtapas(p.id)

  return (
    <div className="@container space-y-4" data-paciente={p.id}>
      <div className="space-y-3">
        <Etapa pronto={etapa >= 1} rotulo="Carregando indicadores" altura={120}>
          <Kpis p={p} />
        </Etapa>
        <Etapa pronto={etapa >= 2} rotulo="Lendo justificativa clínica" altura={180}>
          <JustificativaMedico p={p} />
        </Etapa>
      </div>

      <div className="grid gap-3 @lg:grid-cols-2">
        <Etapa pronto={etapa >= 3} rotulo="Montando espera × prazo" altura={290} className="@lg:col-span-2">
          <GraficoEspera p={p} />
        </Etapa>
        <Etapa pronto={etapa >= 4} rotulo="Calculando camada e posição" altura={260} className="@lg:col-span-2">
          <CartaCamada p={p} />
        </Etapa>
        <Etapa pronto={etapa >= 5} rotulo="Carregando dados do sistema" altura={320} className="@lg:col-span-2">
          <DadosSistema p={p} />
        </Etapa>
      </div>

      {ORIGEM_DADOS === "api" ? (
        <DetalheApiPaciente key={p.id} p={p} />
      ) : (
        <Etapa pronto={etapa >= 6} rotulo="Buscando eventos do paciente" altura={260}>
          <HistoricoPaciente p={p} />
        </Etapa>
      )}
    </div>
  )
}
