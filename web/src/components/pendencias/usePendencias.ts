import { MENSAGEM_GENERICA, mensagemDeErro } from "@/lib/mensagens"
import { useCallback, useEffect, useState } from "react"
import { listarPendencias, type FiltrosPendencias, type ListaPendencias } from "@/api/cliente"

export type EstadoPendencias =
  | { tipo: "carregando" }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "ok"; dados: ListaPendencias; atualizando: boolean }

type Resultado = { chave: string; dados?: ListaPendencias; erro?: string }

/**
 * Busca as pendências na API e refaz a busca quando os filtros mudam (cancela a anterior).
 * O estado é derivado da chave da busca: enquanto a nova não responde, mostra a lista antiga
 * como "atualizando", ou "carregando" se ainda não havia lista.
 */
export function usePendencias({ bloqueante, regra, status }: FiltrosPendencias) {
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [tentativa, setTentativa] = useState(0)
  const chave = JSON.stringify([bloqueante, regra, status, tentativa])

  useEffect(() => {
    const controle = new AbortController()
    listarPendencias({ bloqueante, regra, status }, controle.signal)
      .then((dados) => setResultado({ chave, dados }))
      .catch((e: unknown) => {
        if (controle.signal.aborted) return
        setResultado({ chave, erro: mensagemDeErro(e) })
      })
    return () => controle.abort()
  }, [chave, bloqueante, regra, status])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])

  let estado: EstadoPendencias
  if (resultado === null) estado = { tipo: "carregando" }
  else if (resultado.dados) estado = { tipo: "ok", dados: resultado.dados, atualizando: resultado.chave !== chave }
  else if (resultado.chave === chave) estado = { tipo: "erro", mensagem: resultado.erro ?? MENSAGEM_GENERICA }
  else estado = { tipo: "carregando" }
  return { estado, recarregar }
}
