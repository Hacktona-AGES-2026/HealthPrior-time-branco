import type { Classe } from "@/data/tipos"

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://127.0.0.1:8000"

export type ItemFilaApi = {
  posicao: number
  solicitacao_id: string
  camada: 1 | 2 | 3
  classe: Classe | null
  classe_status: "sugerida_nao_confirmada" | "confirmada"
  pct_prazo_consumido: number | null
  dias_em_fila: number
  procedimento: string
  especialidade: string
  cid: string
  oncologico: boolean
  editado_manualmente: boolean
  alertas: string[]
  resumo_justificativa: string
  iniciais: string
  idade: number | null
  sexo: string | null
  municipio: string | null
  cid_descricao: string | null
  intensidade_dor_eva: number | null
  limitacao_funcional: string | null
  posicao_antes: number | null
}

export type MotivoApi = { sinal: string; evidencia: string; fonte: string; ref?: string | null; data?: string | null }

export type ItemInboxApi = {
  solicitacao_id: string
  procedimento: string
  camada: number
  dias_em_fila: number
  classe_atual: Classe | null
  classe_sugerida: Classe
  motivos: MotivoApi[]
  evento_gatilho?: string | null
}

export type MotivoCodificado =
  | "ps_recorrente"
  | "internacao_relacionada"
  | "progressao_imagem"
  | "piora_funcional"
  | "dor_intensa"
  | "biopsia_positiva"
  | "sinal_alarme_texto"
  | "sugestao_exagerada"
  | "dado_desatualizado"
  | "outro"

export const MOTIVOS_CODIFICADOS: Record<MotivoCodificado, string> = {
  ps_recorrente: "PS recorrente",
  internacao_relacionada: "Internação relacionada",
  progressao_imagem: "Progressão em imagem",
  piora_funcional: "Piora funcional",
  dor_intensa: "Dor intensa",
  biopsia_positiva: "Biópsia positiva",
  sinal_alarme_texto: "Sinal de alarme no texto",
  sugestao_exagerada: "Sugestão exagerada",
  dado_desatualizado: "Dado desatualizado",
  outro: "Outro",
}

export type DecisaoIn = {
  solicitacao_id: string
  regulador_id: string
  acao: "aprovar" | "editar" | "manter"
  classe?: Classe
  score?: number
  motivo_codificado?: MotivoCodificado
  justificativa?: string
}

export type DecisaoOut = { decisao_id: string; posicao_anterior: number | null; posicao_nova: number | null; fila_publicada: boolean }

export type EventoIn = {
  solicitacao_id: string
  data_evento: string
  tipo_evento: string
  resultado?: string
  descricao?: string
  origem?: string
}

export type EventoOut = {
  evento_id: string
  desfecho: "registrado" | "enviado_inbox" | "pendencia"
  classe_antes: Classe | null
  classe_depois: Classe | null
  pendencia_id?: string | null
}

export class ErroApi extends Error {
  status: number
  codigo: string

  constructor(status: number, codigo: string, mensagem: string) {
    super(mensagem)
    this.status = status
    this.codigo = codigo
  }
}

async function pedir<T>(caminho: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(`${API_URL}${caminho}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  })
  const corpo = await resp.json().catch(() => ({}))
  if (!resp.ok) {
    const detalhe = Array.isArray(corpo?.detail) ? corpo.detail.map((d: { msg: string }) => d.msg).join("; ") : undefined
    throw new ErroApi(resp.status, corpo?.erro ?? `HTTP_${resp.status}`, corpo?.mensagem ?? detalhe ?? resp.statusText)
  }
  return corpo as T
}

/** Fila publicada inteira (pagina de 200 em 200). */
export async function listarFila(): Promise<{ itens: ItemFilaApi[]; versao_regras: string | null }> {
  const itens: ItemFilaApi[] = []
  let versao: string | null = null
  for (let page = 1; ; page++) {
    const r = await pedir<{ total: number; itens: ItemFilaApi[]; versao_regras: string | null }>(`/fila?page=${page}&page_size=200`)
    versao = r.versao_regras
    itens.push(...r.itens)
    if (itens.length >= r.total || r.itens.length === 0) break
  }
  return { itens, versao_regras: versao }
}

export const listarInbox = () => pedir<{ total: number; itens: ItemInboxApi[] }>("/inbox")

export const decidir = (d: DecisaoIn) => pedir<DecisaoOut>("/decisoes", { method: "POST", body: JSON.stringify(d) })

export const registrarEvento = (e: EventoIn) => pedir<EventoOut>("/eventos", { method: "POST", body: JSON.stringify(e) })
