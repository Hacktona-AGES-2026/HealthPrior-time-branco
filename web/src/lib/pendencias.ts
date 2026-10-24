import { Ban, GitMerge, LogOut, RotateCcw, type LucideIcon } from "lucide-react"
import type { Resolucao, StatusPendencia } from "@/api/cliente"

/** Nome curto de cada regra de pré-processamento que abre pendência (docs/fluxo-sistema.md C-05). */
export const REGRAS_PENDENCIA: Record<string, string> = {
  "PRE-10": "Contato perdido",
  "PRE-11": "Contato via ACS",
  "PRE-12": "Câncer escondido",
  "PRE-13": "Diabetes fora do cadastro",
  "PRE-20": "Solicitação duplicada",
  "PRE-21": "Operou em outro serviço",
  "PRE-22": "Operou pelo convênio",
  "PRE-23": "Desistência",
  "PRE-24": "Evento órfão",
  "PRE-25": "Fontes contraditórias",
}

export const STATUS_PENDENCIA: Record<StatusPendencia, string> = {
  aberta: "Abertas",
  resolvida: "Resolvidas",
  descartada: "Descartadas",
}

/** De onde veio a evidência (campo `fonte` do contrato). */
export const ROTULO_FONTE: Record<string, string> = {
  evento: "Evento",
  observacoes: "Observação",
  justificativa_clinica: "Justificativa clínica",
  cid: "CID",
  solicitacao: "Solicitação",
  cadastro: "Cadastro",
}

export const rotuloFonte = (fonte: string) => ROTULO_FONTE[fonte] ?? fonte

export type Acao = {
  resolucao: Resolucao
  rotulo: string
  icone: LucideIcon
  /** o que acontece, em uma frase, antes de confirmar */
  dica: (regra: string) => string
  exigeObservacao: boolean
}

export const ACOES: Record<Resolucao, Acao> = {
  confirmar_saida: {
    resolucao: "confirmar_saida",
    rotulo: "Confirmar saída",
    icone: LogOut,
    dica: (regra) => `A solicitação sai da fila (removida) com o motivo ${regra}. Nada é apagado.`,
    exigeObservacao: true,
  },
  fundir: {
    resolucao: "fundir",
    rotulo: "Fundir duplicata",
    icone: GitMerge,
    dica: () => "Uma sai da fila; a que fica herda a data de entrada mais antiga e os eventos das duas.",
    exigeObservacao: false,
  },
  reativar: {
    resolucao: "reativar",
    rotulo: "Reativar",
    icone: RotateCcw,
    dica: () => "A solicitação volta ao fluxo normal da fila.",
    exigeObservacao: false,
  },
  descartar: {
    resolucao: "descartar",
    rotulo: "Descartar",
    icone: Ban,
    dica: () => "O achado não procede: a pendência é descartada e a solicitação segue na fila.",
    exigeObservacao: false,
  },
}

/**
 * Quais resoluções cada regra aceita. Espelha `RESOLUCOES_POR_REGRA` do back (D-67): serve só para
 * mostrar os botões certos; quem valida de verdade é a API.
 */
const SAIDA: Resolucao[] = ["confirmar_saida", "reativar", "descartar"]
const SO_ALERTAM: Resolucao[] = ["reativar", "descartar"]
export const RESOLUCOES_POR_REGRA: Record<string, Resolucao[]> = {
  "PRE-10": SO_ALERTAM,
  "PRE-11": SO_ALERTAM,
  "PRE-12": SO_ALERTAM,
  "PRE-13": SO_ALERTAM,
  "PRE-20": ["fundir", "reativar", "descartar"],
  "PRE-21": SAIDA,
  "PRE-22": SAIDA,
  "PRE-23": SAIDA,
  "PRE-24": ["descartar"],
  "PRE-25": SAIDA,
}

export const acoesDaRegra = (regra: string): Acao[] => (RESOLUCOES_POR_REGRA[regra] ?? []).map((r) => ACOES[r])

/** Frase sobre o que ficou da solicitação depois de resolver (status que a API devolve). */
export const rotuloDesfecho = (statusFila: string | null | undefined) =>
  ({
    removida: "A solicitação saiu da fila.",
    ativa: "A solicitação segue na fila.",
    suspensa: "A solicitação continua suspensa: há outra pendência bloqueante aberta.",
  })[statusFila ?? ""] ?? ""
