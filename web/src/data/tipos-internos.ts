import type { Classe } from "./tipos"
import type { EventoPlano } from "./modelos"

export type { Classe }

export type EventoPlanoExtra = {
  sinais?: string[]
  ev?: EventoPlano[]
  obs?: string
}
