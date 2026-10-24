import type { components } from "./schema"

export type Pendencia = components["schemas"]["PendenciaOut"]
export type Evidencia = components["schemas"]["EvidenciaOut"]
export type StatusPendencia = components["schemas"]["StatusPendencia"]
export type ListaPendencias = components["schemas"]["PendenciasOut"]
export type Resolucao = components["schemas"]["ResolucaoPendencia"]
export type ResolverPendenciaIn = components["schemas"]["ResolverPendenciaIn"]
export type ResultadoResolucao = components["schemas"]["ResolverPendenciaOut"]

export type Inbox = components["schemas"]["InboxOut"]
export type ItemInbox = components["schemas"]["ItemInboxOut"]
export type ResultadoDecisao = components["schemas"]["DecisaoResultadoOut"]

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
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ListaPendencias
}

/** Erros do back vêm como {"erro": "<CODIGO>", "mensagem": "..."}; a validação do FastAPI vem como {"detail": [...]}. */
async function lerErro(resposta: Response): Promise<ErroApi> {
  const corpo = (await resposta.json().catch(() => null)) as { erro?: string; mensagem?: string; detail?: unknown } | null
  const mensagem = corpo?.mensagem ?? (corpo?.detail ? "Os dados enviados são inválidos" : `A API respondeu ${resposta.status}`)
  return new ErroApi(mensagem, corpo?.erro, resposta.status)
}

/** US-07 · POST /pendencias/{id}/resolver. Confirma a resolução e só então a API republica a fila. */
export async function resolverPendencia(pendenciaId: string, corpo: ResolverPendenciaIn): Promise<ResultadoResolucao> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/pendencias/${encodeURIComponent(pendenciaId)}/resolver`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ResultadoResolucao
}

/** US-12 · GET /inbox. Os itens já vêm na ordem em que o regulador deve revisar. */
export async function listarInbox(sinal?: AbortSignal): Promise<Inbox> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/inbox`, { signal: sinal })
  } catch (e) {
    if (sinal?.aborted) throw e
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as Inbox
}

/** US-13 · POST /decisoes (aprovar). Confirma a classe sugerida, registra no log e só então a API republica a fila. */
export async function aprovarProposta(solicitacaoId: string, reguladorId: string): Promise<ResultadoDecisao> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/decisoes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ solicitacao_id: solicitacaoId, regulador_id: reguladorId, acao: "aprovar" }),
    })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ResultadoDecisao
}
