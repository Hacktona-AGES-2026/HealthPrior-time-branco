import { MENSAGEM_GENERICA, mensagemDeErro } from "@/lib/mensagens"
import { useCallback, useEffect, useState } from "react"
import { listarInbox, type Inbox } from "@/api/cliente"

export type EstadoInbox =
  | { tipo: "carregando" }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "ok"; dados: Inbox; atualizando: boolean }

type Resultado = { chave: number; dados?: Inbox; erro?: string }

/** Busca o inbox e refaz a busca em `recarregar`. Mantém a lista antiga como "atualizando" enquanto a nova não chega. */
export function useInbox() {
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [tentativa, setTentativa] = useState(0)

  useEffect(() => {
    const controle = new AbortController()
    listarInbox(controle.signal)
      .then((dados) => setResultado({ chave: tentativa, dados }))
      .catch((e: unknown) => {
        if (controle.signal.aborted) return
        setResultado({ chave: tentativa, erro: mensagemDeErro(e) })
      })
    return () => controle.abort()
  }, [tentativa])

  const recarregar = useCallback(() => setTentativa((t) => t + 1), [])

  let estado: EstadoInbox
  if (resultado === null) estado = { tipo: "carregando" }
  else if (resultado.dados) estado = { tipo: "ok", dados: resultado.dados, atualizando: resultado.chave !== tentativa }
  else if (resultado.chave === tentativa) estado = { tipo: "erro", mensagem: resultado.erro ?? MENSAGEM_GENERICA }
  else estado = { tipo: "carregando" }
  return { estado, recarregar }
}
