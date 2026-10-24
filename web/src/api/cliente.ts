import type { components } from "./schema"

export type Pendencia = components["schemas"]["PendenciaOut"]
export type Evidencia = components["schemas"]["EvidenciaOut"]
export type StatusPendencia = components["schemas"]["StatusPendencia"]
export type ListaPendencias = components["schemas"]["PendenciasOut"]

export const URL_API: string = import.meta.env.VITE_API_URL ?? "http://localhost:8000"

export class ErroApi extends Error {
  codigo?: string
  status?: number

  constructor(mensagem: string, codigo?: string, status?: number) {
    super(mensagem)
    this.codigo = codigo
    this.status = status
  }
}

export type FiltrosPendencias = {
  bloqueante?: boolean
  regra?: string
  status: StatusPendencia
}

/** US-06 · GET /pendencias. Sem `bloqueante`/`regra` traz todas; `status` padrão do back é "aberta". */
export async function listarPendencias(filtros: FiltrosPendencias, sinal?: AbortSignal): Promise<ListaPendencias> {
  const consulta = new URLSearchParams({ status: filtros.status })
  if (filtros.bloqueante !== undefined) consulta.set("bloqueante", String(filtros.bloqueante))
  if (filtros.regra) consulta.set("regra", filtros.regra)

  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/pendencias?${consulta}`, { signal: sinal })
  } catch (e) {
    if (sinal?.aborted) throw e
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) {
    // erros do back vêm como {"erro": "<CODIGO>", "mensagem": "..."}
    const corpo = (await resposta.json().catch(() => null)) as { erro?: string; mensagem?: string } | null
    throw new ErroApi(corpo?.mensagem ?? `A API respondeu ${resposta.status}`, corpo?.erro, resposta.status)
  }
  return (await resposta.json()) as ListaPendencias
}
