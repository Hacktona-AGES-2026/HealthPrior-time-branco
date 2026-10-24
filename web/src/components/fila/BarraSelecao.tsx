import { useState } from "react"
import { Button } from "@/components/ui/button"
import { DialogoConfirmacao } from "@/components/shared/DialogoConfirmacao"
import { ORIGEM_DADOS, PACIENTE_POR_ID } from "@/data/fila"
import { cn } from "@/lib/utils"
import { useStore } from "@/store/useStore"

const LIMITE_LOTE = 40

// Toda ação em lote deve passar por DialogoConfirmacao: adicione novas ações em `acao`.
type Acao = "aprovar" | null

export function BarraSelecao({ rodape = false }: { rodape?: boolean }) {
  const marcados = useStore((s) => s.marcados)
  const decisoes = useStore((s) => s.decisoes)
  const aprovarLote = useStore((s) => s.aprovarLote)
  const limparMarcados = useStore((s) => s.limparMarcados)
  const [acao, setAcao] = useState<Acao>(null)

  if (marcados.length === 0 && !acao) return null

  const elegiveis = marcados.filter((id) => !decisoes[id] && (ORIGEM_DADOS !== "api" || PACIENTE_POR_ID[id]?.inbox))
  const E = elegiveis.length
  const ignorados = marcados.length - E
  const fechar = () => setAcao(null)
  const confirmar = () => {
    if (acao === "aprovar") aprovarLote(marcados)
    fechar()
  }

  return (
    <>
      {marcados.length > 0 && (
        <div
          role="region"
          aria-label="Seleção"
          className={cn(
            "flex items-center gap-2 rounded-lg bg-[color-mix(in_oklab,var(--primary)_10%,var(--background))] px-3 py-1.5 text-sm",
            rodape ? "sticky bottom-16 z-10 mx-3 mb-2 border border-primary/30 shadow-md md:hidden" : "max-md:hidden"
          )}
        >
          <span className="font-medium whitespace-nowrap tabular-nums">{marcados.length} selecionados</span>
          <Button className="h-9" disabled={E === 0} title={E === 0 ? "Nenhum dos selecionados pode ser aprovado em lote" : undefined} onClick={() => setAcao("aprovar")}>
            Aprovar
          </Button>
          <Button variant="ghost" className="h-9 whitespace-nowrap" onClick={limparMarcados}>
            Limpar seleção
          </Button>
        </div>
      )}
      <DialogoConfirmacao
        aberto={acao === "aprovar"}
        titulo={`Aprovar ${E} ${E === 1 ? "paciente" : "pacientes"}?`}
        descricao={
          <>
            Confirma a classe sugerida para cada um.
            {ignorados > 0 && ` Outros ${ignorados} serão ignorados (já revisados ou sem proposta).`}
            {ORIGEM_DADOS === "api" && E > LIMITE_LOTE && ` Serão aprovados ${LIMITE_LOTE} por vez.`}
          </>
        }
        rotuloConfirmar={`Aprovar ${E}`}
        aoConfirmar={confirmar}
        aoCancelar={fechar}
      />
    </>
  )
}
