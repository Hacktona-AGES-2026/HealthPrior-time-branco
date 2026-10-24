export type Classe = "A1" | "A2" | "B" | "C" | "D"

export type Prioridade = "alta" | "media" | "baixa"

export type Camada = 1 | 2 | 3

export type TipoEvento =
  | "biopsia"
  | "hba1c"
  | "pronto_socorro"
  | "internacao"
  | "exame_imagem"
  | "consulta_reavaliacao"
  | "contato_telefonico"
  | "falta"

export type Evento = {
  id: string
  data: string
  tipo: TipoEvento
  resultado: string | null
  valor: number | null
  descricao: string
  origem: string | null
  historico: boolean
}

export type SinalTexto = {
  categoria: "risco_vida" | "suspeita_malignidade" | "sintoma_grave"
  termo: string
  trecho: string
  fonte: "justificativa_clinica" | "observacoes"
  origem: "regra" | "llm"
}

export type Eixo = { nivel: number; motivos: string[] }

export type Paciente = {
  classe_status?: "sugerida_nao_confirmada" | "confirmada"
  editado_manualmente?: boolean
  classe_vigente?: Classe | null
  inbox?: { motivos: string[]; gatilho?: string | null }
  id: string
  iniciais: string
  idade: number
  sexo: "F" | "M"
  municipio: string
  uf: string
  distancia_km: number | null
  procedimento: string
  especialidade: string
  cid: string
  cid_norm: string
  cid_descricao: string
  cid_secundario: string | null
  asa: number | null
  comorbidades: string[]
  dor: number | null
  limitacao: "nenhuma" | "leve" | "moderada" | "grave" | null
  justificativa_clinica: string
  observacoes: string
  sinais_texto: SinalTexto[]
  eixos: { progressao: Eixo; sintoma: Eixo }
  data_entrada: string
  dias_em_fila: number
  prioridade_atual: Prioridade | null
  data_revisao_prioridade: string | null
  oncologico: boolean
  flag_diabetico: boolean
  hba1c: { valor: number; data: string | null } | null
  pre_anestesica: "realizada" | "pendente" | "vencida" | null
  exames_pre_op: boolean
  posicao_atual: number
  posicao: number
  camada: Camada
  classe: Classe
  pct: number
  justificativa: string
  versao_regras: string
  motivos: string[]
  sintomas: string[]
  alertas: string[]
  eventos: Evento[]
  outras: { id: string; procedimento: string; posicao: number }[]
}

export type ClasseSwalis = { classe: Classe; descricao: string; prazo: number; exemplos: string }
