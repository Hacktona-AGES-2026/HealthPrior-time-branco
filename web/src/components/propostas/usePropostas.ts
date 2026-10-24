import { useCallback, useEffect, useState } from "react"
import { listarPropostas, type ListaPropostas, type StatusProposta } from "@/api/cliente"

export type EstadoPropostas =
  | { tipo: "carregando" }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "ok"; dados: ListaPropostas; atualizando: boolean }

type Resultado = { chave: string; dados?: ListaPropostas; erro?: string }

/** Busca as propostas do status escolhido; refaz ao trocar de aba ou em `recarregar` (mantém a lista antiga como "atualizando"). */
export function usePropostas(status: StatusProposta) {
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [tentativa, setTentativa] = useState(0)
  const chave = `${status}:${tentativa}`

  useEffect(() => {
    const controle = new AbortController()
    listarPropostas(status, controle.signal)
      .then((dados) => setResultado({ chave, dados }))
      .catch((e: unknown) => {
        if (controle.signal.aborted) return
        setResultado({ chave, erro: e instanceof Error ? e.message : "Erro inesperado" })
      })
    return () => controle.abort()
  }, [chave, status])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])

  let estado: EstadoPropostas
  if (resultado === null) estado = { tipo: "carregando" }
  else if (resultado.dados) estado = { tipo: "ok", dados: resultado.dados, atualizando: resultado.chave !== chave }
  else if (resultado.chave === chave) estado = { tipo: "erro", mensagem: resultado.erro ?? "Erro inesperado" }
  else estado = { tipo: "carregando" }
  return { estado, recarregar }
}
