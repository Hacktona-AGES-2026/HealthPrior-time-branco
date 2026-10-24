import { CLASSES, indiceClasse } from "@/lib/cores"
import { criarRng, gerarPacientesBase } from "./gerador"
import { ID_DESTAQUE, enriquecerDestaque } from "./destaque"
import type { Classe, Fantasma, Paciente, SlotFila } from "./tipos"

export const TOTAL_FILA = 941

export const BANDAS: Record<Classe, [number, number]> = {
  A1: [1, 28],
  A2: [29, 124],
  B: [125, 365],
  C: [366, 685],
  D: [686, 941],
}

const TOPO: Record<Classe, number> = { A1: 99, A2: 96, B: 104, C: 98, D: 90 }
const FUNDO: Record<Classe, number> = { A1: 20, A2: 18, B: 12, C: 8, D: 4 }

const limitar = (n: number, min: number, max: number) => Math.min(max, Math.max(min, n))

const posicaoNaBanda = (classe: Classe, pct: number) => {
  const [ini, fim] = BANDAS[classe]
  const frac = (TOPO[classe] - pct) / (TOPO[classe] - FUNDO[classe])
  return limitar(ini + Math.round(frac * (fim - ini)), ini, fim)
}

const pctNaPosicao = (classe: Classe, posicao: number) => {
  const [ini, fim] = BANDAS[classe]
  const frac = (posicao - ini) / (fim - ini)
  return TOPO[classe] - frac * (TOPO[classe] - FUNDO[classe])
}

const classePorPosicao = (posicao: number): Classe =>
  CLASSES.find((c) => posicao >= BANDAS[c][0] && posicao <= BANDAS[c][1]) ?? "D"

const construirPacientes = () => {
  const base = gerarPacientesBase().map((p) => (p.solicitacao_id.length > 0 && p.iniciais === "C.A." ? enriquecerDestaque(p) : p))
  const rng = criarRng(4242)
  const ocupadas = new Set<number>()

  CLASSES.forEach((classe) => {
    const grupo = base.filter((p) => p.classe === classe).sort((a, b) => b.prazo_consumido_pct - a.prazo_consumido_pct)
    let anterior = BANDAS[classe][0] - 1
    grupo.forEach((p) => {
      let pos = posicaoNaBanda(classe, p.prazo_consumido_pct)
      if (p.solicitacao_id === ID_DESTAQUE) pos = 9
      pos = Math.max(pos, anterior + 1)
      pos = Math.min(pos, BANDAS[classe][1])
      p.posicao_nova = pos
      anterior = pos
      ocupadas.add(pos)
    })
  })

  base.forEach((p) => {
    if (p.solicitacao_id === ID_DESTAQUE) {
      p.posicao_antiga = 412
      return
    }
    const [ini, fim] = BANDAS[p.classe_antiga]
    if (p.classe_antiga !== p.classe) {
      p.posicao_antiga = limitar(posicaoNaBanda(p.classe_antiga, p.prazo_consumido_pct) + Math.round((rng() - 0.5) * 8), ini, fim)
      return
    }
    const sorteio = rng()
    const salto = sorteio < 0.4 ? 0 : Math.round((rng() - 0.5) * 14)
    p.posicao_antiga = limitar(p.posicao_nova + salto, ini, fim)
  })

  return { pacientes: base.sort((a, b) => a.posicao_nova - b.posicao_nova), ocupadas }
}

const construirFantasmas = (ocupadas: Set<number>) => {
  const rng = criarRng(777)
  const fantasmas: Fantasma[] = []
  for (let posicao = 1; posicao <= TOTAL_FILA; posicao++) {
    if (ocupadas.has(posicao)) continue
    const classe = classePorPosicao(posicao)
    const idx = indiceClasse(classe)
    const sorteio = rng()
    let antiga = classe
    if (sorteio > 0.85 && sorteio <= 0.95) antiga = CLASSES[Math.min(4, idx + 1)]
    else if (sorteio > 0.95) antiga = CLASSES[Math.max(0, idx - 1)]
    const pct = limitar(pctNaPosicao(classe, posicao) + (rng() - 0.5) * 6, 1, 160)
    fantasmas.push({ posicao, classe, classe_antiga: antiga, prazo_consumido_pct: Math.round(pct * 10) / 10 })
  }
  return fantasmas
}

const { pacientes, ocupadas } = construirPacientes()

export const PACIENTES: Paciente[] = pacientes

export const FANTASMAS: Fantasma[] = construirFantasmas(ocupadas)

export const PACIENTE_POR_ID: Record<string, Paciente> = Object.fromEntries(PACIENTES.map((p) => [p.solicitacao_id, p]))

export const FILA: SlotFila[] = (() => {
  const slots: SlotFila[] = Array.from({ length: TOTAL_FILA }, (_, i) => ({ posicao: i + 1 }))
  PACIENTES.forEach((p) => {
    slots[p.posicao_nova - 1].paciente = p
  })
  FANTASMAS.forEach((f) => {
    slots[f.posicao - 1].fantasma = f
  })
  return slots
})()

export const ESPECIALIDADES = [...new Set(PACIENTES.map((p) => p.especialidade))].sort()
