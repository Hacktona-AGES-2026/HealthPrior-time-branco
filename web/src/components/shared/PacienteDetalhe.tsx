import { ORIGEM_DADOS } from "@/data/fila"
import type { Paciente } from "@/data/tipos"
import { motivosClinicos } from "@/lib/motivos"
import { DetalheApiPaciente, PendenciasAlertas } from "./detalhe/DetalheApi"
import { GraficoEspera } from "./detalhe/GraficoEspera"
import { HistoricoPaciente } from "./detalhe/HistoricoPaciente"
import { DadosPedido } from "./detalhe/DadosPedido"
import { QuadroClinico } from "./detalhe/JustificativaMedico"
import { ComoClasse } from "./detalhe/ComoClasse"
import { Resumo } from "./detalhe/Kpis"

export function PacienteDetalhe({ paciente: p }: { paciente: Paciente }) {
  const motivos = motivosClinicos(p, 4)

  return (
    <div className="@container space-y-6" data-paciente={p.id}>
      <Resumo p={p} />
      <QuadroClinico p={p} />

      {motivos.length > 0 && (
        <section aria-labelledby="motivo-ficha" className="space-y-1">
          <h3 id="motivo-ficha" className="text-sm font-semibold">
            Motivo
          </h3>
          <ul className="list-disc space-y-0.5 pl-4 text-sm">
            {motivos.map((m) => (
              <li key={m}>{m}</li>
            ))}
          </ul>
        </section>
      )}

      <ComoClasse p={p} />

      <section aria-labelledby="espera" className="space-y-2">
        <h3 id="espera" className="text-sm font-semibold">
          Tempo de espera
        </h3>
        <GraficoEspera p={p} />
      </section>

      {ORIGEM_DADOS === "api" ? (
        <DetalheApiPaciente key={p.id} p={p} />
      ) : (
        <>
          <HistoricoPaciente p={p} />
          <PendenciasAlertas alertas={p.alertas} />
        </>
      )}

      {p.outras.length > 0 && (
        <section aria-labelledby="outras" className="space-y-1">
          <h3 id="outras" className="text-sm font-semibold">
            Outras solicitações do paciente
          </h3>
          <ul className="space-y-0.5 text-sm">
            {p.outras.map((o) => (
              <li key={o.id} className="break-words">
                {o.procedimento} — posição #{o.posicao}
              </li>
            ))}
          </ul>
        </section>
      )}

      <DadosPedido p={p} />
    </div>
  )
}
