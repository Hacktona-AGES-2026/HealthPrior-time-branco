"""Vocabulário do domínio. Valores em string são os mesmos usados na API (docs/user-stories.md §5)."""
from enum import Enum, IntEnum


class Camada(IntEnum):
    """Camadas impostas pela trava da regra de ouro (C-11)."""

    ONCOLOGICO = 1
    URGENTE = 2
    DEMAIS = 3


class Classe(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B = "B"
    C = "C"
    D = "D"


PRAZO_MAXIMO_DIAS: dict[Classe, int] = {
    Classe.A1: 15,
    Classe.A2: 21,
    Classe.B: 60,
    Classe.C: 180,
    Classe.D: 360,
}


class ClasseStatus(str, Enum):
    SUGERIDA_NAO_CONFIRMADA = "sugerida_nao_confirmada"
    CONFIRMADA = "confirmada"


class StatusFila(str, Enum):
    ATIVA = "ativa"
    SUSPENSA = "suspensa"
    REMOVIDA = "removida"


class Prioridade(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAIXA = "baixa"


class MotivoCodificado(str, Enum):
    PS_RECORRENTE = "ps_recorrente"
    INTERNACAO_RELACIONADA = "internacao_relacionada"
    PROGRESSAO_IMAGEM = "progressao_imagem"
    PIORA_FUNCIONAL = "piora_funcional"
    DOR_INTENSA = "dor_intensa"
    BIOPSIA_POSITIVA = "biopsia_positiva"
    SINAL_ALARME_TEXTO = "sinal_alarme_texto"
    SUGESTAO_EXAGERADA = "sugestao_exagerada"
    DADO_DESATUALIZADO = "dado_desatualizado"
    OUTRO = "outro"


class AcaoDecisao(str, Enum):
    APROVAR = "aprovar"
    EDITAR = "editar"
    MANTER = "manter"


class DesfechoEvento(str, Enum):
    REGISTRADO = "registrado"
    ENVIADO_INBOX = "enviado_inbox"
    PENDENCIA = "pendencia"


class ResolucaoPendencia(str, Enum):
    CONFIRMAR_SAIDA = "confirmar_saida"
    FUNDIR = "fundir"
    REATIVAR = "reativar"
    DESCARTAR = "descartar"


class StatusPendencia(str, Enum):
    ABERTA = "aberta"
    RESOLVIDA = "resolvida"
    DESCARTADA = "descartada"


class TipoEvento(str, Enum):
    BIOPSIA = "biopsia"
    HBA1C = "hba1c"
    PRONTO_SOCORRO = "pronto_socorro"
    INTERNACAO = "internacao"
    EXAME_IMAGEM = "exame_imagem"
    CONSULTA_REAVALIACAO = "consulta_reavaliacao"
    CONTATO_TELEFONICO = "contato_telefonico"
    FALTA = "falta"
