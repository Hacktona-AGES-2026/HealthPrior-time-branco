import { PACIENTE_POR_ID } from "@/data/fila"

/**
 * Textos de erro para o usuário (médico/equipe), em português simples.
 * O back devolve {erro: "<CODIGO>", mensagem}: o código nunca aparece na tela; o texto sai daqui.
 */
const POR_CODIGO: Record<string, string> = {
  SEM_PROPOSTA: "Este paciente não tem proposta para aprovar: a classe sugerida já é a classe em vigor.",
  ONCOLOGICO_REBAIXADO: "Paciente com câncer não pode ficar atrás de quem não tem urgência. Escolha uma classe mais alta.",
  JUSTIFICATIVA_OBRIGATORIA: "Escreva a justificativa para mudar a classe.",
  OBSERVACAO_OBRIGATORIA: "Escreva uma observação para confirmar a saída do paciente da fila.",
  SOLICITACAO_NAO_ENCONTRADA: "Paciente não encontrado. A lista pode estar desatualizada: atualize a página.",
  PENDENCIA_NAO_ENCONTRADA: "Pendência não encontrada. Atualize a lista.",
  PENDENCIA_JA_RESOLVIDA: "Esta pendência já foi resolvida por outra pessoa.",
  RESOLUCAO_INVALIDA: "Essa ação não vale para este tipo de pendência.",
  PROPOSTA_NAO_ENCONTRADA: "Proposta não encontrada. Atualize a lista.",
  PROPOSTA_JA_DECIDIDA: "Esta proposta já foi decidida por outra pessoa.",
  REGRA_NAO_ENCONTRADA: "Regra não encontrada. Atualize a lista.",
  REGRA_JA_REVERTIDA: "Esta regra já foi revertida.",
  FILA_NAO_PUBLICADA: "Ainda não há fila publicada.",
  DATA_REFERENCIA_INVALIDA: "A data informada não é válida.",
  CARGA_INVALIDA: "Não foi possível ler os dados. Confira o arquivo e tente de novo.",
}

export const MENSAGEM_GENERICA = "Algo deu errado. Tente de novo."
const SEM_CONEXAO = "Sem conexão com o servidor. Confira a internet e tente de novo."
const FALHA_SERVIDOR = "O servidor teve um problema. Tente de novo em instantes; se continuar, avise a equipe técnica."

/** Texto vindo do back só vale se for uma frase em português, não um código nem um erro técnico. */
const parecePortuguesLegivel = (t: string) => t.length > 8 && t.length < 200 && /\s/.test(t) && !/^[A-Z0-9_]+$/.test(t) && !/(undefined|null|TypeError|Exception|Traceback|HTTP \d)/i.test(t)

type ComoErroApi = { message?: unknown; codigo?: unknown; status?: unknown }

/** Traduz qualquer erro (da API, de rede ou inesperado) em uma frase para o usuário. */
export function mensagemDeErro(e: unknown): string {
  const { message, codigo, status } = (e ?? {}) as ComoErroApi
  const texto = typeof message === "string" ? message : ""

  if (typeof codigo === "string" && POR_CODIGO[codigo]) return POR_CODIGO[codigo]

  const semResposta = e instanceof TypeError || /failed to fetch|networkerror|load failed|falar com a api/i.test(texto)
  if (semResposta) return SEM_CONEXAO
  if (e instanceof DOMException && e.name === "AbortError") return "A operação foi cancelada."

  if (typeof status === "number") {
    if (status >= 500) return FALHA_SERVIDOR
    if (status === 409) return "A situação mudou enquanto você olhava. Atualize a lista e tente de novo."
    if (status === 404) return "Não encontramos o que você pediu. Atualize a página."
    if (status === 422 && !parecePortuguesLegivel(texto)) return "Os dados enviados não são válidos. Confira os campos e tente de novo."
  }
  return parecePortuguesLegivel(texto) ? texto : MENSAGEM_GENERICA
}

/** Como chamar o paciente numa mensagem: iniciais quando existem (M.F.V.), senão o número da solicitação. */
export const nomeDoPaciente = (id: string): string => PACIENTE_POR_ID[id]?.iniciais || id

export const plural = (n: number, singular: string, plural: string) => `${n.toLocaleString("pt-BR")} ${n === 1 ? singular : plural}`
