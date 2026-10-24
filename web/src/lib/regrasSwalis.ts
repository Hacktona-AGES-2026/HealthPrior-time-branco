import type { Paciente } from "@/data/tipos"

export type RegraSwalis = { id: string; titulo: string; texto: string; curto: string; ouro?: boolean; vale?: (p: Paciente) => boolean }

export const REGRAS_SWALIS: RegraSwalis[] = [
  { id: "ouro", titulo: "Câncer vem primeiro", texto: "Quem tem CID começado por C nunca fica atrás de quem não tem urgência clínica. Vale o CID, não a marcação do cadastro.", curto: "CID de câncer: nunca fica atrás de quem não tem urgência.", ouro: true, vale: (p) => p.oncologico },
  { id: "decisao", titulo: "Quem decide a classe é você", texto: "Mudar a classe exige decisão do regulador. A classe inicial é só uma sugestão.", curto: "A classe é sugestão até o regulador confirmar." },
  { id: "texto", titulo: "O texto só gera alertas", texto: "A leitura automática do texto do pedido só cita trechos e gera alertas. Nunca muda a classe nem o CID.", curto: "Sinais do texto geram alertas, não mudam a classe.", vale: (p) => p.sinais_texto.length > 0 },
  { id: "historico", titulo: "Antes da entrada é histórico", texto: "O que aconteceu antes de entrar na fila não conta como piora durante a espera.", curto: "Eventos antes da entrada na fila não contam como piora.", vale: (p) => p.eventos.some((e) => e.historico) },
  { id: "alertas", titulo: "Alertas não somam pontos", texto: "HbA1c, risco anestésico, distância, faltas e número de eventos viram alertas, não pontuação.", curto: "Alertas não entram na pontuação.", vale: (p) => p.alertas.length > 0 },
  { id: "apagar", titulo: "Nada é apagado", texto: "Uma solicitação sai da fila por status (suspensa, removida) com motivo, nunca por exclusão.", curto: "Nada é apagado: só muda de status." },
]

export const CRITERIOS_SWALIS = [
  { nome: "Progressão da doença", texto: "CID, biópsia e sinais no texto do pedido." },
  { nome: "Sintomas", texto: "Dor, limitação e complicações." },
]

const TROCAS: [RegExp, string][] = [
  // sufixos técnicos que a API acrescenta ao trecho citado: "(regra)", "(llm)", "(Jev p=0.98)", "→ perda_funcao"
  [/\s*\((?:regra|llm|palavras?-chave|crit[eé]rio|jev[^)]*)\)/gi, ""],
  [/\s*→\s*[a-z_]+/gi, ""],
  [/eixo de progress[ãa]o/gi, "progressão"],
  [/eixo de sintoma/gi, "sintomas"],
  [/palavras?-chave/gi, "termo no texto"],
  [/\bllm\b/gi, "leitura do texto"],
  [/\bregra\b/gi, "critério"],
  [/\bjev\b/gi, "evidência"],
]

/** Encurta e troca jargão dos motivos vindos da API. */
export function limparJargao(m: string): string {
  let t = m.trim()
  for (const [re, nv] of TROCAS) t = t.replace(re, nv)
  return t
}

export function motivoClaro(m: string): string {
  const t = limparJargao(m).replace(/^"+|"+$/g, "").trim()
  return t.length > 110 ? t.slice(0, 107).trimEnd() + "…" : t
}
