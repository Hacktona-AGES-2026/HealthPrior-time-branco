import type { StatusPendencia } from "@/api/cliente"

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
