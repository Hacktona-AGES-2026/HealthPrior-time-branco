import type { Classe, EventoPlanoExtra } from "./tipos-internos"

export type Linha = {
  m: string
  ini: string
  idade: number
  sexo: "F" | "M"
  mun: string
  ca: Classe
  cn: Classe
  pct: number
  conf: number
  dor: number
  lim: "n" | "l" | "m" | "g"
  asa: 1 | 2 | 3 | 4
  div?: true
  ouro?: true
  base?: Classe
  via?: Classe
  extra?: EventoPlanoExtra
}

export const MUNICIPIOS: Record<string, number> = {
  "Porto Alegre": 12,
  Canoas: 18,
  Gravataí: 24,
  Viamão: 31,
  "Novo Hamburgo": 42,
  "São Leopoldo": 36,
  Cachoeirinha: 21,
  Alvorada: 27,
  Guaíba: 29,
  Camaquã: 129,
  "Santa Cruz do Sul": 155,
  Pelotas: 260,
  Lajeado: 115,
  Montenegro: 60,
  Taquara: 70,
}

const ps = (fracao: number, descricao: string) => ({ fracao, tipo: "pronto_socorro" as const, descricao })

export const LINHAS: Linha[] = [
  { m: "herniaObstr", ini: "C.A.", idade: 71, sexo: "F", mun: "Canoas", ca: "C", cn: "A1", pct: 88, conf: 0.94, dor: 9, lim: "g", asa: 3 },
  { m: "isquemia", ini: "J.R.", idade: 67, sexo: "M", mun: "Canoas", ca: "B", cn: "A1", pct: 62, conf: 0.91, dor: 9, lim: "g", asa: 4, extra: { sinais: ["PS x2"], ev: [ps(0.92, "Segundo PS em 10 dias: dor intensa e extremidade fria")] } },
  { m: "aneurisma", ini: "A.L.", idade: 72, sexo: "M", mun: "Novo Hamburgo", ca: "B", cn: "A1", pct: 34, conf: 0.88, dor: 6, lim: "m", asa: 3, extra: { sinais: ["PS recente"], ev: [ps(0.9, "PS por dor abdominal; angio-TC sem ruptura")] } },
  { m: "revasc", ini: "E.P.", idade: 61, sexo: "M", mun: "Gravataí", ca: "B", cn: "A1", pct: 71, conf: 0.93, dor: 7, lim: "m", asa: 4, extra: { sinais: ["angina instável"], ev: [{ fracao: 0.92, tipo: "internacao", descricao: "Internação por angina instável" }] } },
  { m: "colon", ini: "R.M.", idade: 58, sexo: "F", mun: "Porto Alegre", ca: "A2", cn: "A1", pct: 40, conf: 0.86, dor: 8, lim: "g", asa: 3, extra: { sinais: ["suboclusão"], ev: [ps(0.88, "PS por vômitos e distensão abdominal: suboclusão intestinal")], obs: "Paciente relata por telefone ausência de evacuação há 4 dias." } },
  { m: "mama", ini: "M.S.", idade: 52, sexo: "F", mun: "Porto Alegre", ca: "C", cn: "A2", pct: 38, conf: 0.94, dor: 3, lim: "l", asa: 2 },
  { m: "mama", ini: "L.F.", idade: 47, sexo: "F", mun: "Viamão", ca: "D", cn: "A2", pct: 22, conf: 0.58, dor: 2, lim: "n", asa: 2, ouro: true, base: "C" },
  { m: "mama", ini: "T.B.", idade: 63, sexo: "F", mun: "Canoas", ca: "B", cn: "A2", pct: 55, conf: 0.92, dor: 3, lim: "l", asa: 3 },
  { m: "mama", ini: "S.G.", idade: 58, sexo: "F", mun: "Cachoeirinha", ca: "A2", cn: "A2", pct: 90, conf: 0.96, dor: 2, lim: "l", asa: 2 },
  { m: "prostata", ini: "O.N.", idade: 69, sexo: "M", mun: "Porto Alegre", ca: "C", cn: "A2", pct: 44, conf: 0.9, dor: 1, lim: "n", asa: 3 },
  { m: "estomago", ini: "H.C.", idade: 66, sexo: "M", mun: "Camaquã", ca: "B", cn: "A2", pct: 81, conf: 0.89, dor: 6, lim: "m", asa: 3 },
  { m: "pulmao", ini: "V.K.", idade: 71, sexo: "M", mun: "Santa Cruz do Sul", ca: "B", cn: "A2", pct: 67, conf: 0.91, dor: 4, lim: "m", asa: 4 },
  { m: "tireoide", ini: "N.A.", idade: 44, sexo: "F", mun: "Guaíba", ca: "D", cn: "A2", pct: 29, conf: 0.55, dor: 1, lim: "n", asa: 2, ouro: true },
  { m: "colon", ini: "D.T.", idade: 62, sexo: "M", mun: "Lajeado", ca: "B", cn: "A2", pct: 58, conf: 0.9, dor: 4, lim: "l", asa: 3 },
  { m: "revasc", ini: "C.V.", idade: 64, sexo: "M", mun: "Pelotas", ca: "B", cn: "A2", pct: 52, conf: 0.87, dor: 5, lim: "m", asa: 3 },
  { m: "aneurisma", ini: "B.Z.", idade: 70, sexo: "M", mun: "Montenegro", ca: "B", cn: "A2", pct: 77, conf: 0.85, dor: 3, lim: "l", asa: 3 },
  { m: "estomago", ini: "I.O.", idade: 74, sexo: "F", mun: "Porto Alegre", ca: "A2", cn: "A2", pct: 93, conf: 0.95, dor: 5, lim: "m", asa: 3, via: "B" },
  { m: "pulmao", ini: "K.E.", idade: 59, sexo: "M", mun: "Pelotas", ca: "A2", cn: "A2", pct: 85, conf: 0.94, dor: 3, lim: "l", asa: 3 },
  { m: "pele", ini: "G.P.", idade: 73, sexo: "M", mun: "Taquara", ca: "C", cn: "B", pct: 71, conf: 0.93, dor: 2, lim: "l", asa: 3, ouro: true },
  { m: "pele", ini: "F.D.", idade: 68, sexo: "F", mun: "Alvorada", ca: "D", cn: "B", pct: 115, conf: 0.8, dor: 1, lim: "n", asa: 2, ouro: true },
  { m: "coxartrose", ini: "A.M.", idade: 76, sexo: "F", mun: "Porto Alegre", ca: "B", cn: "B", pct: 124, conf: 0.9, dor: 8, lim: "g", asa: 3, via: "C" },
  { m: "coxartrose", ini: "J.S.", idade: 65, sexo: "F", mun: "Canoas", ca: "C", cn: "B", pct: 88, conf: 0.86, dor: 7, lim: "m", asa: 2 },
  { m: "coxartrose", ini: "P.T.", idade: 70, sexo: "M", mun: "São Leopoldo", ca: "B", cn: "B", pct: 40, conf: 0.93, dor: 8, lim: "g", asa: 3 },
  { m: "colelitiase", ini: "K.L.", idade: 45, sexo: "F", mun: "Viamão", ca: "C", cn: "B", pct: 66, conf: 0.84, dor: 7, lim: "m", asa: 2 },
  { m: "colelitiase", ini: "W.R.", idade: 52, sexo: "F", mun: "Novo Hamburgo", ca: "B", cn: "B", pct: 32, conf: 0.92, dor: 7, lim: "m", asa: 2 },
  { m: "hpb", ini: "U.E.", idade: 79, sexo: "M", mun: "Porto Alegre", ca: "C", cn: "B", pct: 52, conf: 0.88, dor: 3, lim: "m", asa: 3 },
  { m: "hpb", ini: "Q.J.", idade: 74, sexo: "M", mun: "Gravataí", ca: "C", cn: "B", pct: 79, conf: 0.86, dor: 4, lim: "m", asa: 4 },
  { m: "litiase", ini: "Y.C.", idade: 55, sexo: "F", mun: "Cachoeirinha", ca: "C", cn: "B", pct: 61, conf: 0.83, dor: 6, lim: "m", asa: 2 },
  { m: "gonartrose", ini: "Z.H.", idade: 68, sexo: "F", mun: "Alvorada", ca: "C", cn: "B", pct: 85, conf: 0.81, dor: 7, lim: "m", asa: 3 },
  { m: "glaucoma", ini: "X.I.", idade: 72, sexo: "M", mun: "Pelotas", ca: "C", cn: "B", pct: 48, conf: 0.87, dor: 1, lim: "m", asa: 2 },
  { m: "mioma", ini: "B.U.", idade: 43, sexo: "F", mun: "Canoas", ca: "C", cn: "B", pct: 57, conf: 0.85, dor: 5, lim: "l", asa: 2 },
  { m: "herniaIng", ini: "O.F.", idade: 60, sexo: "M", mun: "Guaíba", ca: "C", cn: "B", pct: 74, conf: 0.8, dor: 6, lim: "m", asa: 3, extra: { sinais: ["PS x1"], ev: [ps(0.85, "PS por dor intensa e abaulamento endurecido, hérnia reduzida")] } },
  { m: "colelitiase", ini: "S.A.", idade: 49, sexo: "F", mun: "Porto Alegre", ca: "C", cn: "B", pct: 91, conf: 0.89, dor: 7, lim: "m", asa: 3 },
  { m: "gonartrose", ini: "R.O.", idade: 75, sexo: "M", mun: "Viamão", ca: "B", cn: "B", pct: 63, conf: 0.9, dor: 7, lim: "m", asa: 3 },
  { m: "herniaIng", ini: "L.G.", idade: 55, sexo: "M", mun: "Canoas", ca: "C", cn: "C", pct: 112, conf: 0.91, dor: 4, lim: "l", asa: 2, via: "D" },
  { m: "herniaIng", ini: "T.M.", idade: 48, sexo: "M", mun: "Gravataí", ca: "C", cn: "C", pct: 35, conf: 0.9, dor: 3, lim: "l", asa: 2 },
  { m: "colelitiase", ini: "E.N.", idade: 41, sexo: "F", mun: "Alvorada", ca: "C", cn: "C", pct: 108, conf: 0.88, dor: 5, lim: "l", asa: 2 },
  { m: "gonartrose", ini: "M.A.", idade: 66, sexo: "F", mun: "Porto Alegre", ca: "C", cn: "C", pct: 60, conf: 0.87, dor: 5, lim: "m", asa: 2 },
  { m: "gonartrose", ini: "C.P.", idade: 71, sexo: "F", mun: "São Leopoldo", ca: "B", cn: "C", pct: 44, conf: 0.58, dor: 4, lim: "l", asa: 3, div: true },
  { m: "gonartrose", ini: "D.R.", idade: 62, sexo: "M", mun: "Novo Hamburgo", ca: "C", cn: "C", pct: 77, conf: 0.86, dor: 5, lim: "m", asa: 2, via: "D" },
  { m: "varizes", ini: "N.Q.", idade: 51, sexo: "F", mun: "Viamão", ca: "C", cn: "C", pct: 52, conf: 0.88, dor: 3, lim: "l", asa: 2 },
  { m: "varizes", ini: "I.W.", idade: 46, sexo: "F", mun: "Porto Alegre", ca: "D", cn: "C", pct: 38, conf: 0.8, dor: 4, lim: "l", asa: 1 },
  { m: "hpb", ini: "G.V.", idade: 68, sexo: "M", mun: "Cachoeirinha", ca: "C", cn: "C", pct: 30, conf: 0.85, dor: 2, lim: "l", asa: 2 },
  { m: "litiase", ini: "H.D.", idade: 44, sexo: "M", mun: "Canoas", ca: "C", cn: "C", pct: 69, conf: 0.84, dor: 4, lim: "l", asa: 2 },
  { m: "glaucoma", ini: "A.X.", idade: 67, sexo: "F", mun: "Guaíba", ca: "C", cn: "C", pct: 83, conf: 0.82, dor: 1, lim: "m", asa: 2 },
  { m: "mioma", ini: "K.Y.", idade: 47, sexo: "F", mun: "Taquara", ca: "C", cn: "C", pct: 41, conf: 0.86, dor: 3, lim: "l", asa: 2 },
  { m: "catarata", ini: "P.C.", idade: 74, sexo: "F", mun: "Porto Alegre", ca: "D", cn: "C", pct: 55, conf: 0.83, dor: 0, lim: "m", asa: 2 },
  { m: "tunel", ini: "B.L.", idade: 54, sexo: "F", mun: "Montenegro", ca: "D", cn: "C", pct: 46, conf: 0.8, dor: 4, lim: "l", asa: 2 },
  { m: "hemorroida", ini: "F.S.", idade: 49, sexo: "M", mun: "Gravataí", ca: "D", cn: "C", pct: 36, conf: 0.79, dor: 5, lim: "l", asa: 2 },
  { m: "catarata", ini: "O.A.", idade: 81, sexo: "F", mun: "Santa Cruz do Sul", ca: "D", cn: "D", pct: 103, conf: 0.86, dor: 0, lim: "l", asa: 3 },
  { m: "catarata", ini: "L.B.", idade: 69, sexo: "M", mun: "Lajeado", ca: "D", cn: "D", pct: 40, conf: 0.88, dor: 0, lim: "l", asa: 2 },
  { m: "catarata", ini: "T.Z.", idade: 77, sexo: "F", mun: "Porto Alegre", ca: "C", cn: "D", pct: 25, conf: 0.51, dor: 0, lim: "n", asa: 3, div: true },
  { m: "herniaUmb", ini: "V.N.", idade: 57, sexo: "M", mun: "Canoas", ca: "D", cn: "D", pct: 30, conf: 0.9, dor: 0, lim: "n", asa: 2 },
  { m: "herniaUmb", ini: "E.J.", idade: 42, sexo: "F", mun: "Alvorada", ca: "C", cn: "D", pct: 61, conf: 0.47, dor: 1, lim: "n", asa: 2, div: true },
  { m: "septo", ini: "R.C.", idade: 29, sexo: "M", mun: "Porto Alegre", ca: "D", cn: "D", pct: 18, conf: 0.85, dor: 1, lim: "l", asa: 1 },
  { m: "septo", ini: "M.K.", idade: 35, sexo: "F", mun: "Novo Hamburgo", ca: "C", cn: "D", pct: 49, conf: 0.42, dor: 1, lim: "n", asa: 1, div: true },
  { m: "tunel", ini: "S.B.", idade: 58, sexo: "F", mun: "Viamão", ca: "D", cn: "D", pct: 33, conf: 0.86, dor: 3, lim: "l", asa: 2 },
  { m: "varizes", ini: "J.G.", idade: 63, sexo: "F", mun: "Cachoeirinha", ca: "D", cn: "D", pct: 27, conf: 0.87, dor: 2, lim: "l", asa: 2 },
  { m: "hemorroida", ini: "H.T.", idade: 39, sexo: "M", mun: "Porto Alegre", ca: "D", cn: "D", pct: 45, conf: 0.84, dor: 2, lim: "l", asa: 1 },
  { m: "hemorroida", ini: "A.P.", idade: 53, sexo: "F", mun: "Guaíba", ca: "D", cn: "D", pct: 21, conf: 0.82, dor: 1, lim: "n", asa: 2 },
]
