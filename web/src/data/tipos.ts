export type Classe = "A1" | "A2" | "B" | "C" | "D"

export type TipoEvento =
  | "entrada"
  | "pronto_socorro"
  | "internacao"
  | "biopsia"
  | "exame_imagem"
  | "consulta_reavaliacao"
  | "hba1c"
  | "falta"
  | "contato_telefonico"

export type TipoHistorico =
  | "cirurgia_previa"
  | "internacao_previa"
  | "consulta"
  | "exame"
  | "solicitacao_anterior"
  | "alergia"
  | "medicacao_continua"
  | "alteracao_prioridade"

export type OrigemContribuicao =
  | "cid"
  | "sintomas"
  | "eventos"
  | "texto_llm"
  | "fragilidade"
  | "regra_ouro"

export type Paciente = {
  // Só com dados da API: camada da trava, se a classe foi confirmada e se o regulador editou.
  camada?: 1 | 2 | 3
  classe_status?: "sugerida_nao_confirmada" | "confirmada"
  editado_manualmente?: boolean
  solicitacao_id: string
  iniciais: string
  cns_mascarado: string
  idade: number
  sexo: "F" | "M"
  municipio: string
  distancia_hospital_km: number
  procedimento: string
  especialidade: string
  cid: string
  cid_descricao: string
  cid_secundario?: string
  data_entrada_fila: string
  dias_em_fila: number
  posicao_antiga: number
  posicao_nova: number
  classe_antiga: Classe
  classe: Classe
  prazo_consumido_pct: number
  divergencia: boolean
  comorbidades: string[]
  asa: 1 | 2 | 3 | 4
  intensidade_dor_eva: number
  limitacao_funcional: "nenhuma" | "leve" | "moderada" | "grave"
  hba1c?: { valor: number; data: string }
  avaliacao_pre_anestesica: boolean
  exames_pre_op_validos: boolean
  justificativa_clinica: string
  observacoes: string
  confianca: number
  sinais: string[]
  justificativa: string
  evidencias: { fonte: "texto" | "evento" | "cid" | "regra"; trecho: string; data?: string }[]
  parametros_ia: {
    modelo: string
    versao_regras: string
    classe_base_cid: Classe
    contribuicoes: {
      fator: string
      delta_degraus: number
      origem: OrigemContribuicao
      detalhe: string
    }[]
    sinais_texto: { sinal: string; trecho: string; confianca: number }[]
    confianca_detalhe: { componente: string; valor: number }[]
    regras_acionadas: string[]
    contrafactual: string
  }
  falta_para_subir: string
  eventos: { data: string; tipo: TipoEvento; descricao: string }[]
  evolucao: { data: string; classe: Classe; prazo_consumido_pct: number; motivo: string }[]
  historico: { data: string; tipo: TipoHistorico; descricao: string; origem: string }[]
}

export type Fantasma = {
  posicao: number
  classe: Classe
  classe_antiga: Classe
  prazo_consumido_pct: number
}

export type SlotFila = {
  posicao: number
  paciente?: Paciente
  fantasma?: Fantasma
}
