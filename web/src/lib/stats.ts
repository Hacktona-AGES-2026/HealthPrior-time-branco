import { PACIENTES, TOTAL_FILA } from "@/data/fila"

export const metricasGlobais = (decisoes: Record<string, { status: string }>) => ({
  total: TOTAL_FILA,
  oncologicos: PACIENTES.filter((p) => p.camada === 1).length,
  urgentes: PACIENTES.filter((p) => p.camada === 2).length,
  vencidos: PACIENTES.filter((p) => p.pct > 100).length,
  comAlertas: PACIENTES.filter((p) => p.alertas.length > 0).length,
  revisados: PACIENTES.filter((p) => decisoes[p.id]).length,
  totalDetalhados: TOTAL_FILA,
})
