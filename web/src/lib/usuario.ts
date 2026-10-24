/**
 * Quem está resolvendo as pendências. Não há login (D-12): até a US-23 trazer o seletor de usuário,
 * vale `adm-01`, ou o que estiver em `localStorage["hp.usuario"]` (útil para testar autores diferentes).
 */
const CHAVE = "hp.usuario"
export const USUARIO_PADRAO = "adm-01"

export function usuarioAtual(): string {
  try {
    return localStorage.getItem(CHAVE)?.trim() || USUARIO_PADRAO
  } catch {
    return USUARIO_PADRAO // localStorage indisponível (modo privado, bloqueio)
  }
}
