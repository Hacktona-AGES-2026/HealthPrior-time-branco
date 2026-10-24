import { ArrowLeft, Printer } from "lucide-react"
import { PACIENTE_POR_ID } from "@/data/fila"
import { Button } from "@/components/ui/button"
import { AcoesDecisao } from "@/components/shared/AcoesDecisao"
import { NovoEvento } from "@/components/shared/NovoEvento"
import { PacienteDetalhe } from "@/components/shared/PacienteDetalhe"
import { useStore } from "@/store/useStore"
import { ListaPacientes } from "./ListaPacientes"

export default function PaginaPacientes() {
  const fichaId = useStore((s) => s.fichaId)
  const fecharFicha = useStore((s) => s.fecharFicha)
  const abrirNaFila = useStore((s) => s.abrirNaFila)
  const paciente = fichaId ? PACIENTE_POR_ID[fichaId] : undefined

  if (!paciente) return <ListaPacientes />

  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto max-w-4xl space-y-4 p-3 md:p-6">
        <div className="no-print flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-x-2">
            <Button variant="ghost" size="sm" className="h-9 gap-1.5 px-2" onClick={fecharFicha}>
              <ArrowLeft aria-hidden /> Pacientes
            </Button>
            <Button variant="link" size="sm" className="h-9 px-1 text-muted-foreground" onClick={() => abrirNaFila(paciente.id)}>
              Voltar à fila
            </Button>
            <Button variant="ghost" size="icon-sm" className="ml-auto size-9 md:hidden" onClick={() => window.print()} title="Imprimir" aria-label="Imprimir ficha">
              <Printer aria-hidden />
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <AcoesDecisao paciente={paciente} variante="barra" />
            <NovoEvento solicitacaoId={paciente.id} />
            <Button variant="ghost" size="icon-sm" className="hidden size-9 md:inline-flex" onClick={() => window.print()} title="Imprimir" aria-label="Imprimir ficha">
              <Printer aria-hidden />
            </Button>
          </div>
        </div>
        <div key={paciente.id} className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold">
              {paciente.iniciais} · {paciente.idade} anos · {paciente.sexo}
            </h2>
            <p className="text-sm text-muted-foreground">{paciente.procedimento}</p>
          </div>
          <PacienteDetalhe paciente={paciente} />
        </div>
      </div>
    </div>
  )
}
