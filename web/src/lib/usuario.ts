/**
 * Autor gravado no log. Não há login nem seletor de persona/usuário (D-12, D-107: US-23 cortada).
 * Autor fixo por papel: decisões do regulador saem como `reg-01`; resoluções de pendência como `adm-01`.
 * Para testar autores diferentes, defina `localStorage["hp.usuario"]` (vale para os dois).
 */
const CHAVE = "hp.usuario"
export const USUARIO_PADRAO = "adm-01"
export const REGULADOR_PADRAO = "reg-01"

function doStorage(): string | undefined {
  try {
    return localStorage.getItem(CHAVE)?.trim() || undefined
  } catch {
    return undefined // localStorage indisponível (modo privado, bloqueio)
  }
}

/** Quem resolve as pendências (equipe administrativa). */
export function usuarioAtual(): string {
  return doStorage() ?? USUARIO_PADRAO
}

/** Quem decide no inbox e na fila (regulador). */
export function reguladorAtual(): string {
  return doStorage() ?? REGULADOR_PADRAO
}
