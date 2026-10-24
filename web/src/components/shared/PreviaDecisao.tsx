import { useEffect, useState } from "react"
import type { Classe } from "@/data/tipos"
import { type Previa, preverDecisao } from "@/lib/api"
import { MENSAGEM_GENERICA, mensagemDeErro } from "@/lib/mensagens"
import { cn } from "@/lib/utils"

const fmtPct = (n: number) => `${Math.round(n).toLocaleString("pt-BR")}%`

/** "Se aprovar A2: posição 360 → 298 · 267% do prazo" — o que a decisão faria, antes de gravar. */
export function PreviaDecisao({ previa, rotulo, className }: { previa: Previa; rotulo: string; className?: string }) {
  const { posicao_atual: de, posicao_estimada: para } = previa
  const sobe = de != null && para != null && para < de
  const desce = de != null && para != null && para > de
  return (
    <p className={cn("text-xs text-muted-foreground", className)} aria-live="polite">
      <span className="font-medium text-foreground">{rotulo}:</span>{" "}
      {para == null ? (
        "fora da fila publicada (suspensa ou sem publicação)"
      ) : (
        <>
          posição {de ?? "—"} →{" "}
          <span className={cn("font-semibold tabular-nums", sobe && "text-[var(--sobe)]", desce && "text-[var(--desce)]")}>{para}</span>
          {de === para && " (sem mudança)"}
        </>
      )}{" "}
      · {fmtPct(previa.pct_prazo_consumido)} do prazo
    </p>
  )
}

type Estado = { chave: string; previa?: Previa; erro?: string }

/** Busca a prévia na API quando `ativo`; refaz ao trocar a classe. */
export function usePrevia(id: string, acao: "aprovar" | "editar" | "manter", classe: Classe | undefined, ativo: boolean) {
  const chave = `${id}:${acao}:${classe ?? ""}`
  const [estado, setEstado] = useState<Estado | null>(null)
  useEffect(() => {
    if (!ativo) return
    let vivo = true
    preverDecisao(id, acao, classe)
      .then((previa) => vivo && setEstado({ chave, previa }))
      .catch((e: unknown) => vivo && setEstado({ chave, erro: (mensagemDeErro(e) === MENSAGEM_GENERICA ? "Não foi possível calcular a nova posição." : mensagemDeErro(e)) }))
    return () => {
      vivo = false
    }
  }, [ativo, chave, id, acao, classe])
  return estado && estado.chave === chave ? estado : null
}
