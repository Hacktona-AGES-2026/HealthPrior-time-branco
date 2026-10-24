import type { components } from "./schema"

export type Pendencia = components["schemas"]["PendenciaOut"]
export type Evidencia = components["schemas"]["EvidenciaOut"]
export type StatusPendencia = components["schemas"]["StatusPendencia"]
export type ListaPendencias = components["schemas"]["PendenciasOut"]
export type Resolucao = components["schemas"]["ResolucaoPendencia"]
export type ResolverPendenciaIn = components["schemas"]["ResolverPendenciaIn"]
export type ResultadoResolucao = components["schemas"]["ResolverPendenciaOut"]

export type Inbox = components["schemas"]["InboxOut"]
// `previa` (o que aprovar faria) ainda não está no schema gerado; regenere com `npm run gen:api`.
export type ItemInbox = components["schemas"]["ItemInboxOut"] & { previa?: import("@/lib/api").Previa | null }
export type ResultadoDecisao = components["schemas"]["DecisaoResultadoOut"]


export type Proposta = components["schemas"]["PropostaDetalheOut"]
export type CasoOrigem = components["schemas"]["CasoOrigemOut"]
export type ImpactoProposta = components["schemas"]["ImpactoOut"]
export type ListaPropostas = components["schemas"]["PropostasOut"]
export type StatusProposta = Proposta["status"]
export type ResultadoProposta = components["schemas"]["DecidirPropostaOut"]
export type ResultadoReversao = components["schemas"]["ReverterRegraOut"]

export type Notificacao = components["schemas"]["NotificacaoOut"]
export type ListaNotificacoes = components["schemas"]["NotificacoesOut"]
export type ResultadoEnvios = components["schemas"]["EnviosOut"]

export type ResultadoImportacao = components["schemas"]["ImportacaoOut"]

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

/** US-19 · GET /propostas, com os casos de origem e, nas pendentes, o impacto simulado (shadow run). */
export async function listarPropostas(status: StatusProposta, sinal?: AbortSignal): Promise<ListaPropostas> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/propostas?status=${status}`, { signal: sinal })
  } catch (e) {
    if (sinal?.aborted) throw e
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ListaPropostas
}

/** US-19 · POST /propostas/{id}/decidir. Aprovar abre a versão N+1 das regras; rejeitar exige a observação. */
export async function decidirProposta(
  propostaId: string,
  corpo: { decisao: "aprovar" | "rejeitar"; usuario_id: string; observacao?: string },
): Promise<ResultadoProposta> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/propostas/${encodeURIComponent(propostaId)}/decidir`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ResultadoProposta
}

/** US-19 · POST /regras/{id}/reverter. Desativa a regra e tira do inbox quem só estava lá por ela; o motivo é obrigatório. */
export async function reverterRegra(regraId: string, corpo: { usuario_id: string; motivo: string }): Promise<ResultadoReversao> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/regras/${encodeURIComponent(regraId)}/reverter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ResultadoReversao
}

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

/** Notificações ao paciente (demo): o que foi enfileirado e enviado, e o canal configurado. */
export async function listarNotificacoes(sinal?: AbortSignal): Promise<ListaNotificacoes> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/notificacoes`, { signal: sinal })
  } catch (e) {
    if (sinal?.aborted) throw e
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ListaNotificacoes
}

/** Envia as pendentes pelo canal configurado (no máximo o limite por rodada). */
export async function enviarNotificacoes(): Promise<ResultadoEnvios> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/notificacoes/enviar`, { method: "POST" })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (!resposta.ok) throw await lerErro(resposta)
  return (await resposta.json()) as ResultadoEnvios
}

/**
 * Importa solicitações novas por CSV (uma linha ou várias). Com erro de validação a API responde 422 com o relatório
 * (nada é gravado): aqui isso volta como resultado, não como exceção.
 */
export async function importarSolicitacoes(csv: string, publicar: boolean): Promise<{ ok: boolean; resultado: ResultadoImportacao }> {
  let resposta: Response
  try {
    resposta = await fetch(`${URL_API}/importacao/solicitacoes?publicar=${publicar}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv; charset=utf-8" },
      body: csv,
    })
  } catch {
    throw new ErroApi(`Não foi possível falar com a API em ${URL_API}`)
  }
  if (resposta.ok || resposta.status === 422) {
    const corpo = (await resposta.json().catch(() => null)) as ResultadoImportacao | null
    if (corpo && Array.isArray(corpo.erros)) return { ok: resposta.ok, resultado: corpo }
  }
  throw await lerErro(resposta)
}

export const URL_MODELO_CSV = `${URL_API}/importacao/modelo.csv`
