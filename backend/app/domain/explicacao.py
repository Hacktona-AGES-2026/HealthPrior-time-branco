"""US-21 · Textos de explicação do paciente. Funções puras: sem I/O, sem relógio (datas vêm de fora)."""
from __future__ import annotations

NOME_CAMADA = {1: "oncológico", 2: "urgente", 3: "demais casos"}
MAX_MOTIVOS = 3
STATUS_NAO_ATIVO = ("suspensa", "removida")


def camada_motivo(camada: int | None, cid: str, justificativa: str | None) -> str | None:
    """Texto curto do motivo da camada: pelo CID na camada 1; na 2 e 3, a 1a frase da justificativa."""
    if camada is None:
        return None
    if camada == 1:
        return f"Oncológico pelo CID {cid}"
    if not justificativa:
        return None
    return justificativa.split(".", 1)[0].strip() or None


def montar_explicacao(*, posicao: int | None, camada: int | None, cid: str, classe: str | None,
                      prazo_dias: int | None, pct_prazo: float | None, dias_em_fila: int,
                      motivos: list[str], editado_manualmente: bool, editado_por: str | None,
                      status_fila: str, motivo_status: str | None) -> str:
    """Explicação de 2 a 4 frases em português para o regulador."""
    frases = []

    if posicao is None or camada is None:
        frases.append("Ainda não está na fila publicada.")
    elif camada == 1:
        frases.append(f"Posição {posicao}: oncológico pelo CID {cid} (camada 1).")
    else:
        frases.append(f"Posição {posicao}: {NOME_CAMADA[camada]} (camada {camada}).")

    classe_txt = f"Classe {classe}" if classe else "Classe não definida"
    if editado_manualmente:
        quem = f"por {editado_por}" if editado_por else "pelo regulador"
        classe_txt += f" (editada manualmente {quem})"
    partes = []
    if prazo_dias is not None:
        partes.append(f"prazo de {prazo_dias} dias")
    trecho_espera = f"{dias_em_fila} dias em fila"
    if pct_prazo is not None:
        trecho_espera += f" ({pct_prazo:g}% do prazo)"
    partes.append(trecho_espera)
    frases.append(f"{classe_txt}; " + ", ".join(partes) + ".")

    if motivos:
        frases.append("Principais sinais: " + "; ".join(motivos[:MAX_MOTIVOS]) + ".")

    if status_fila in STATUS_NAO_ATIVO:
        frase = f"Solicitação {status_fila}"
        frases.append(frase + (f": {motivo_status}." if motivo_status else "."))

    return " ".join(frases)
