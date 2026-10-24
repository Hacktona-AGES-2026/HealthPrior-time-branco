import { CLASSES, PRAZO_MAX, indiceClasse } from "@/lib/cores"
import { HOJE, addDias, diffDias } from "@/lib/datas"
import { LINHAS, MUNICIPIOS, type Linha } from "./linhas"
import { MODELOS, type Modelo } from "./modelos"
import type { Classe, Paciente, TipoHistorico } from "./tipos"

export const criarRng = (semente: number) => {
  let a = semente >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

type Rng = () => number

const escolher = <T,>(rng: Rng, lista: T[]) => lista[Math.floor(rng() * lista.length)]

const embaralhar = <T,>(rng: Rng, lista: T[]) => {
  const copia = [...lista]
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1))
    ;[copia[i], copia[j]] = [copia[j], copia[i]]
  }
  return copia
}

const arredondar = (n: number, casas = 2) => Math.round(n * 10 ** casas) / 10 ** casas

const LIMITACAO = { n: "nenhuma", l: "leve", m: "moderada", g: "grave" } as const

const PRIORIDADE_HUMANA: Record<Classe, string> = { A1: "alta", A2: "alta", B: "média", C: "baixa", D: "baixa" }

const UBS = ["UBS Centro", "UBS Vila Nova", "UBS Santa Rosa", "UBS Jardim Botânico", "UBS Restinga", "UBS Mathias Velho"]
const HOSPITAIS = ["Hospital São Lucas", "Hospital Santa Rita", "Hospital Conceição", "Hospital Ernesto Dornelles", "Hospital Nossa Senhora das Graças"]
const ALERGIAS = ["Dipirona (urticária)", "Penicilina (exantema)", "Látex", "AAS (broncoespasmo)", "Contraste iodado", "Sulfa (rash cutâneo)"]
const INTERNACOES = [
  "Internação de 4 dias por pneumonia comunitária",
  "Internação de 3 dias por crise hipertensiva",
  "Internação de 6 dias por descompensação de diabetes",
  "Internação de 2 dias por infecção urinária complicada",
  "Internação de 5 dias por insuficiência cardíaca descompensada",
]
const EXAMES = [
  "ECG de repouso sem alterações agudas",
  "Hemograma e creatinina dentro da normalidade",
  "Radiografia de tórax sem alterações",
  "Ecocardiograma com fração de ejeção preservada",
  "Glicemia de jejum e perfil lipídico solicitados",
]
const OBSERVACOES = [
  "Paciente relata piora de sintomas por telefone.",
  "Contato telefônico sem sucesso em duas tentativas.",
  "Necessita acompanhante por mobilidade reduzida.",
  "Aguardando liberação de exames pré-operatórios.",
  "Sem intercorrências desde a última revisão.",
  "Reside em área rural; transporte depende de agendamento municipal.",
  "Paciente ansioso quanto ao procedimento; orientado pela equipe.",
]
const MEDICACOES: Record<string, string> = {
  HAS: "Losartana 50 mg 2x/dia",
  DM2: "Metformina 850 mg 2x/dia",
  dislipidemia: "Sinvastatina 20 mg à noite",
  ICC: "Carvedilol 12,5 mg 2x/dia e furosemida 40 mg",
  DPOC: "Formoterol + budesonida inalatória 2x/dia",
  hipotireoidismo: "Levotiroxina 75 mcg em jejum",
  "fibrilação atrial": "Varfarina 5 mg (INR alvo 2–3)",
  anemia: "Sulfato ferroso 40 mg/dia",
  glaucoma: "Timolol 0,5% colírio 2x/dia",
  gota: "Alopurinol 100 mg/dia",
  osteoporose: "Alendronato 70 mg semanal",
  "doença renal crônica": "Carbonato de cálcio e sevelâmer",
  enfisema: "Tiotrópio inalatório 1x/dia",
}

const rotuloSinalMaiusculo = (s: string) => s.charAt(0).toUpperCase() + s.slice(1)

const gerarEventos = (l: Linha, m: Modelo, entrada: string, dias: number, tem: { dm: boolean; hba1c?: number }) => {
  const dataEm = (fracao: number) => addDias(entrada, Math.min(dias, Math.max(1, Math.round(fracao * dias))))
  const eventos: Paciente["eventos"] = [
    { data: entrada, tipo: "entrada", descricao: `Entrada na fila cirúrgica com prioridade ${PRIORIDADE_HUMANA[l.via ?? l.ca]}` },
  ]
  const plano = [...m.eventos, ...(l.extra?.ev ?? [])]
  plano.forEach((e) => eventos.push({ data: dataEm(e.fracao), tipo: e.tipo, descricao: e.descricao }))
  if (l.via) {
    eventos.push({
      data: dataEm(0.55),
      tipo: "consulta_reavaliacao",
      descricao: `Reavaliação da regulação: prioridade de ${PRIORIDADE_HUMANA[l.via]} para ${PRIORIDADE_HUMANA[l.ca]}`,
    })
  }
  if (tem.dm && tem.hba1c !== undefined) {
    eventos.push({ data: dataEm(0.35), tipo: "hba1c", descricao: `HbA1c ${String(tem.hba1c).replace(".", ",")}%` })
  }
  return eventos.sort((a, b) => a.data.localeCompare(b.data))
}

const gerarEvolucao = (l: Linha, entrada: string, dias: number, eventos: Paciente["eventos"], dataMudanca: string | null) => {
  const classeEm = (dia: number): Classe => (l.via && dia < 0.55 * dias ? l.via : l.ca)
  const dataParaDia = (data: string) => diffDias(entrada, data)
  const diasMarcados = new Set<number>([0, dias])
  const passo = Math.max(3, Math.round(dias / 9))
  for (let d = passo; d < dias; d += passo) diasMarcados.add(d)
  const motivoPorDia = new Map<number, string>()
  eventos.forEach((e) => {
    const d = dataParaDia(e.data)
    diasMarcados.add(d)
    motivoPorDia.set(d, e.descricao)
  })
  if (dataMudanca) diasMarcados.add(dataParaDia(dataMudanca))
  const ordenados = [...diasMarcados].sort((a, b) => a - b)
  const acumulado = (dia: number) => {
    let total = 0
    for (let d = 0; d < dia; d++) total += 1 / PRAZO_MAX[classeEm(d + 0.5)]
    return total * 100
  }
  const bruto = acumulado(dias)
  const escala = bruto > 0 ? l.pct / bruto : 1
  const pontos: Paciente["evolucao"] = ordenados.map((d) => ({
    data: addDias(entrada, d),
    classe: classeEm(d),
    prazo_consumido_pct: arredondar(Math.min(acumulado(d) * escala, l.pct), 1),
    motivo:
      d === 0
        ? `Entrada na fila: classe ${classeEm(d)}`
        : motivoPorDia.get(d) ?? (d === dias ? "Situação atual (hoje)" : "Acúmulo do prazo na classe vigente"),
  }))
  if (l.cn !== l.ca) {
    const projecao = Math.min(14, Math.max(3, Math.round(PRAZO_MAX[l.cn] * 0.25)))
    pontos.push({
      data: HOJE,
      classe: l.cn,
      prazo_consumido_pct: arredondar(l.pct, 1),
      motivo: `Proposta da IA: ${l.ca} → ${l.cn} (percentual acumulado preservado)`,
    })
    pontos.push({
      data: addDias(HOJE, projecao),
      classe: l.cn,
      prazo_consumido_pct: arredondar(l.pct + (projecao / PRAZO_MAX[l.cn]) * 100, 1),
      motivo: `Projeção em ${projecao} dias na nova classe (não realizado)`,
    })
  }
  return pontos
}

const gerarHistorico = (
  rng: Rng,
  l: Linha,
  m: Modelo,
  entrada: string,
  dias: number,
  comorbidades: string[]
): Paciente["historico"] => {
  const hosp = () => escolher(rng, HOSPITAIS)
  const itens: { data: string; tipo: TipoHistorico; descricao: string; origem: string; essencial: boolean }[] = []
  const ubs = escolher(rng, UBS)
  itens.push({
    data: addDias(entrada, -Math.round(25 + rng() * 45)),
    tipo: "consulta",
    descricao: `Consulta na atenção básica: ${m.desc.toLowerCase()}; encaminhado para avaliação cirúrgica`,
    origem: ubs,
    essencial: true,
  })
  itens.push({
    data: addDias(entrada, -Math.round(4 + rng() * 10)),
    tipo: "consulta",
    descricao: `Consulta ambulatorial de ${m.esp}: indicada cirurgia (${m.proc.toLowerCase()})`,
    origem: hosp(),
    essencial: true,
  })
  itens.push({
    data: addDias(HOJE, -Math.round(15 + rng() * Math.max(10, dias))),
    tipo: "exame",
    descricao: escolher(rng, EXAMES),
    origem: hosp(),
    essencial: true,
  })
  const medicadas = comorbidades.filter((c) => MEDICACOES[c]).slice(0, 2)
  medicadas.forEach((c) =>
    itens.push({
      data: addDias(HOJE, -Math.round(250 + rng() * 1800)),
      tipo: "medicacao_continua",
      descricao: MEDICACOES[c],
      origem: ubs,
      essencial: true,
    })
  )
  if (rng() < 0.55) {
    itens.push({
      data: addDias(HOJE, -Math.round(600 + rng() * 5000)),
      tipo: "alergia",
      descricao: escolher(rng, ALERGIAS),
      origem: "Cadastro CNS",
      essencial: true,
    })
  }
  const procLower = m.proc.toLowerCase()
  const cirurgias = m.cirurgiasPrevias.filter((c) => {
    if (l.sexo === "M" && /cesariana|histerectomia|laqueadura|miomectomia/i.test(c)) return false
    if (l.sexo === "F" && /vasectomia/i.test(c)) return false
    return !procLower.includes(c.toLowerCase().split(" ")[0])
  })
  if (cirurgias.length > 0 && rng() < 0.7) {
    itens.push({
      data: addDias(HOJE, -Math.round(900 + rng() * 5000)),
      tipo: "cirurgia_previa",
      descricao: escolher(rng, cirurgias),
      origem: hosp(),
      essencial: false,
    })
  }
  if (rng() < 0.35) {
    itens.push({
      data: addDias(HOJE, -Math.round(400 + rng() * 2500)),
      tipo: "internacao_previa",
      descricao: escolher(rng, INTERNACOES),
      origem: hosp(),
      essencial: false,
    })
  }
  if (rng() < 0.3) {
    itens.push({
      data: addDias(entrada, -Math.round(180 + rng() * 220)),
      tipo: "solicitacao_anterior",
      descricao: `Solicitação anterior de ${procLower} cancelada: exames pré-operatórios vencidos`,
      origem: "Central de Regulação",
      essencial: false,
    })
  }
  if (l.via) {
    itens.push({
      data: addDias(entrada, Math.round(0.55 * dias)),
      tipo: "alteracao_prioridade",
      descricao: `Prioridade alterada de ${PRIORIDADE_HUMANA[l.via]} para ${PRIORIDADE_HUMANA[l.ca]} após reavaliação`,
      origem: "Regulação",
      essencial: false,
    })
  } else if (rng() < 0.3) {
    itens.push({
      data: addDias(entrada, Math.round(0.5 * dias)),
      tipo: "alteracao_prioridade",
      descricao: `Prioridade revisada pela regulação e mantida como ${PRIORIDADE_HUMANA[l.ca]}`,
      origem: "Regulação",
      essencial: false,
    })
  }
  let selecionados = itens
  if (selecionados.length > 8) {
    const essenciais = selecionados.filter((i) => i.essencial)
    const opcionais = selecionados.filter((i) => !i.essencial)
    selecionados = [...essenciais, ...opcionais].slice(0, 8)
  }
  return selecionados
    .sort((a, b) => b.data.localeCompare(a.data))
    .map(({ data, tipo, descricao, origem }) => ({ data, tipo, descricao, origem }))
}

const gerarContribuicoes = (l: Linha, m: Modelo, eventos: Paciente["eventos"], fragil: boolean) => {
  const baseIdx = indiceClasse(l.base ?? m.base)
  const novaIdx = indiceClasse(l.cn)
  const necessario = baseIdx - novaIdx
  const finais: Paciente["parametros_ia"]["contribuicoes"] = []
  const pisoIdx = m.cid.startsWith("C44") ? 2 : 1
  const ruleShare = m.onc && l.ouro ? Math.max(0, Math.min(necessario, baseIdx - pisoIdx)) : 0
  let restante = necessario - ruleShare

  const textos = m.dest.map((d, i) => ({
    fator: rotuloSinalMaiusculo(d.sinal),
    origem: "texto_llm" as const,
    detalhe: `Trecho "${d.trecho}" (confiança ${Math.round(d.confianca * 100)}%)`,
    hi: i === 0 ? 2 : 1,
    delta: 0,
  }))
  const sintomas = {
    fator: `Sintomas: dor ${l.dor}/10, limitação ${LIMITACAO[l.lim]}`,
    origem: "sintomas" as const,
    detalhe: l.dor >= 7 || l.lim === "g" ? "Dor intensa e limitação funcional elevam a urgência" : "Sintomas moderados, sem agravante isolado",
    hi: l.dor >= 7 || l.lim === "g" ? 1 : 0,
    delta: 0,
  }
  const temEventoGrave = eventos.some((e) => ["pronto_socorro", "internacao", "biopsia"].includes(e.tipo))
  const psCount = eventos.filter((e) => e.tipo === "pronto_socorro").length
  const eventosC = {
    fator: psCount > 0 ? `Eventos na espera (PS x${psCount})` : "Eventos na espera",
    origem: "eventos" as const,
    detalhe: temEventoGrave
      ? "Pronto-socorro, internação ou biópsia durante a espera reforçam a prioridade"
      : "Sem eventos agudos durante a espera",
    hi: temEventoGrave ? 1 : 0,
    delta: 0,
  }
  const fragilidade = {
    fator: "Fragilidade (idade e ASA)",
    origem: "fragilidade" as const,
    detalhe: `Idade ${l.idade} e ASA ${l.asa}: a fragilidade só sobe a classe, nunca desce`,
    hi: 1,
    delta: 0,
  }

  if (restante > 0) {
    const ordem = [textos[0], sintomas, eventosC, ...textos.slice(1), ...(fragil ? [fragilidade] : [])]
    for (const c of ordem) {
      const d = Math.min(c.hi, restante)
      c.delta = d
      restante -= d
    }
    if (restante > 0) textos[0].delta += restante
  } else if (restante < 0) {
    sintomas.delta = restante
    sintomas.fator = `Ausência de sinais de gravidade: dor ${l.dor}/10, limitação ${LIMITACAO[l.lim]}`
    sintomas.detalhe = "Sintomas leves e sem eventos agudos desaconselham a prioridade humana atual"
  }

  const comDelta = [sintomas, ...textos, eventosC, ...(fragil ? [fragilidade] : [])]
  comDelta.forEach((c) => finais.push({ fator: c.fator, delta_degraus: c.delta, origem: c.origem, detalhe: c.detalhe }))
  if (m.onc) {
    finais.push({
      fator: "Regra de ouro (câncer)",
      delta_degraus: ruleShare,
      origem: "regra_ouro",
      detalhe:
        ruleShare > 0
          ? `Neoplasia maligna não pode ficar abaixo de ${m.cid.startsWith("C44") ? "B (pele não melanoma)" : "A2"}: piso aplicado`
          : `Piso oncológico (${m.cid.startsWith("C44") ? "B" : "A2"}) verificado: classe já cumpre a regra`,
    })
  }
  return finais
}

const gerarPaciente = (l: Linha, indice: number): Paciente => {
  const rng = criarRng(9000 + indice * 131)
  const m = MODELOS[l.m]
  const pa = PRAZO_MAX[l.ca]
  let dias: number
  if (l.via) {
    const pv = PRAZO_MAX[l.via]
    dias = Math.round(l.pct / 100 / (0.55 / pv + 0.45 / pa))
  } else {
    dias = Math.round((l.pct / 100) * pa)
  }
  dias = Math.max(6, dias)
  const entrada = addDias(HOJE, -dias)

  const textoClinico = m.texto(indice)
  const forcadas = /Diabético/.test(textoClinico) ? ["DM2"] : []
  const nComorb = Math.min(m.comorb.length, l.asa === 1 ? (rng() < 0.5 ? 0 : 1) : l.asa === 2 ? 1 + Math.round(rng()) : l.asa === 3 ? 2 + Math.round(rng()) : 3 + Math.round(rng()))
  const comorbidades = [...new Set([...forcadas, ...embaralhar(rng, m.comorb)])].slice(0, Math.max(nComorb, forcadas.length))
  const dm = comorbidades.includes("DM2")
  const hba1cValor = dm ? arredondar(6.1 + rng() * 4.6, 1) : undefined
  const fragil = l.idade >= 70 && l.asa >= 3

  const eventos = gerarEventos(l, m, entrada, dias, { dm, hba1c: hba1cValor })
  const dataMudanca = null
  const evolucao = gerarEvolucao(l, entrada, dias, eventos, dataMudanca)
  const contribuicoes = gerarContribuicoes(l, m, eventos, fragil)

  const psCount = eventos.filter((e) => e.tipo === "pronto_socorro").length
  const sinaisSet = new Set<string>([...m.sinais, ...(l.extra?.sinais ?? [])])
  if (psCount >= 2) sinaisSet.add(`PS x${psCount}`)
  if (l.dor >= 8) sinaisSet.add(`dor ${l.dor}/10`)
  if (fragil) sinaisSet.add("frágil")
  if (l.pct > 100) sinaisSet.add("prazo vencido")
  if (dm && hba1cValor !== undefined && hba1cValor >= 8) sinaisSet.add("HbA1c alta")
  const sinais = [...sinaisSet]

  const maiorContrib = [...contribuicoes].sort((a, b) => b.delta_degraus - a.delta_degraus)[0]
  const semMaior = CLASSES[Math.min(4, indiceClasse(l.cn) + maiorContrib.delta_degraus)]
  const contrafactual =
    maiorContrib.delta_degraus > 0
      ? `Sem "${maiorContrib.fator}" (+${maiorContrib.delta_degraus} ${maiorContrib.delta_degraus === 1 ? "degrau" : "degraus"}), a classe proposta cairia de ${l.cn} para ${semMaior}.`
      : `Nenhuma contribuição isolada altera a classe: ${l.cn} é estável para pequenas mudanças nos sinais.`

  const regras = ["R02 · O LLM propõe, as regras decidem", "R06 · Idade apenas como modificador"]
  if (m.onc) regras.unshift("R01 · Regra de ouro oncológica (C* ≥ B; demais ≥ A2)")
  if (psCount >= 2) regras.push("R03 · Pronto-socorro recorrente sobe 1 degrau")
  if (fragil) regras.push("R05 · Fragilidade só sobe a classe, nunca desce")
  if (l.div) regras.push("R07 · Divergência com a prioridade humana sinalizada para revisão")
  if (l.pct > 100) regras.push("R08 · Prazo vencido: desempate pelo % consumido")

  const variacao = () => (rng() - 0.5) * 0.12
  const confDetalhe = [
    { componente: "Clareza do texto clínico", valor: arredondar(Math.min(0.99, Math.max(0.2, l.conf + 0.03 + variacao()))) },
    { componente: "Concordância CID × sintomas", valor: arredondar(Math.min(0.99, Math.max(0.2, l.conf - 0.04 + variacao()))) },
    { componente: "Eventos corroborantes", valor: arredondar(Math.min(0.99, Math.max(0.2, l.conf + variacao()))) },
    { componente: "Cobertura de dados", valor: arredondar(Math.min(0.99, Math.max(0.2, l.conf - 0.02 + variacao()))) },
  ]

  const evidencias: Paciente["evidencias"] = m.dest.map((d) => ({ fonte: "texto", trecho: d.trecho }))
  evidencias.push({ fonte: "cid", trecho: `${m.cid} · ${m.desc}` })
  eventos
    .filter((e) => ["biopsia", "pronto_socorro", "internacao", "exame_imagem"].includes(e.tipo))
    .slice(0, 3)
    .forEach((e) => evidencias.push({ fonte: "evento", trecho: e.descricao, data: e.data }))
  if (m.onc) evidencias.push({ fonte: "regra", trecho: "R01 · Regra de ouro oncológica" })

  const mudou = l.ca !== l.cn
  const justificativa = `${m.resumo} ${mudou ? `Proposta: ${l.ca} → ${l.cn}.` : `Classe ${l.cn} mantida.`}${l.div ? " Discorda da prioridade humana atual; revisar." : ""}`

  const comorbidadesFinal = comorbidades
  const km = MUNICIPIOS[l.mun] ?? 30
  const cnsFim = String(1000 + Math.floor(rng() * 8999))
  const sol = 100 + indice * 17 + Math.floor(rng() * 9)
  const ano = entrada.slice(0, 4)

  return {
    solicitacao_id: `SOL-${ano}-${String(sol).padStart(5, "0")}`,
    iniciais: l.ini,
    cns_mascarado: `7${Math.floor(rng() * 90 + 10)} •••• •••• ${cnsFim}`,
    idade: l.idade,
    sexo: l.sexo,
    municipio: l.mun,
    distancia_hospital_km: km + Math.floor(rng() * 4),
    procedimento: m.proc,
    especialidade: m.esp,
    cid: m.cid,
    cid_descricao: m.desc,
    cid_secundario: m.sec ? `${m.sec[0]} · ${m.sec[1]}` : undefined,
    data_entrada_fila: entrada,
    dias_em_fila: dias,
    posicao_antiga: 0,
    posicao_nova: 0,
    classe_antiga: l.ca,
    classe: l.cn,
    prazo_consumido_pct: l.pct,
    divergencia: !!l.div,
    comorbidades: comorbidadesFinal,
    asa: l.asa,
    intensidade_dor_eva: l.dor,
    limitacao_funcional: LIMITACAO[l.lim],
    hba1c: dm && hba1cValor !== undefined ? { valor: hba1cValor, data: addDias(HOJE, -Math.round(30 + rng() * 270)) } : undefined,
    avaliacao_pre_anestesica: rng() < 0.65,
    exames_pre_op_validos: rng() < 0.55,
    justificativa_clinica: textoClinico,
    observacoes: l.extra?.obs ?? escolher(rng, OBSERVACOES),
    confianca: l.conf,
    sinais,
    justificativa,
    evidencias,
    parametros_ia: {
      modelo: "claude-sonnet",
      versao_regras: "regras-v0.3",
      classe_base_cid: l.base ?? m.base,
      contribuicoes,
      sinais_texto: m.dest.map((d) => ({ sinal: d.sinal, trecho: d.trecho, confianca: d.confianca })),
      confianca_detalhe: confDetalhe,
      regras_acionadas: regras,
      contrafactual,
    },
    falta_para_subir: l.cn === "A1" ? "Já está na classe máxima (A1): cirurgia em até 15 dias." : m.proximo,
    eventos,
    evolucao,
    historico: gerarHistorico(rng, l, m, entrada, dias, comorbidades),
  }
}

export const gerarPacientesBase = () => LINHAS.map((l, i) => gerarPaciente(l, i + 1))
