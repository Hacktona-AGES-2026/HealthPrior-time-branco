export const HOJE = "2026-10-23"

const DIA_MS = 86_400_000

const paraUtc = (iso: string) => {
  const [a, m, d] = iso.split("-").map(Number)
  return Date.UTC(a, m - 1, d)
}

export const addDias = (iso: string, dias: number) =>
  new Date(paraUtc(iso) + dias * DIA_MS).toISOString().slice(0, 10)

export const diffDias = (de: string, ate: string) => Math.round((paraUtc(ate) - paraUtc(de)) / DIA_MS)

export const formatarData = (iso: string) => {
  const [a, m, d] = iso.split("-")
  return `${d}/${m}/${a}`
}

export const formatarDataCurta = (iso: string) => {
  const [, m, d] = iso.split("-")
  return `${d}/${m}`
}
