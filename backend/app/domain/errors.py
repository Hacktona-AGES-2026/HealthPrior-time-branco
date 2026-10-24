"""Erros de domínio. A camada de API converte em {"erro": codigo, "mensagem": ...}."""


class DomainError(Exception):
    codigo = "ERRO_DE_DOMINIO"
    status_http = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoEncontradoError(DomainError):
    codigo = "SOLICITACAO_NAO_ENCONTRADA"
    status_http = 404


class OncologicoRebaixadoError(DomainError):
    """Invariante I-01: oncológico nunca abaixo de paciente sem urgência."""

    codigo = "ONCOLOGICO_REBAIXADO"
    status_http = 422

    def __init__(self, mensagem: str = "Oncológico não pode ficar abaixo de paciente sem urgência."):
        super().__init__(mensagem)


class JustificativaObrigatoriaError(DomainError):
    codigo = "JUSTIFICATIVA_OBRIGATORIA"
    status_http = 422


class DecisaoInvalidaError(DomainError):
    codigo = "DECISAO_INVALIDA"
    status_http = 422


class SemPropostaError(DomainError):
    """Não há classe sugerida esperando decisão (já confirmada, sem divergência ou fora da fila)."""

    codigo = "SEM_PROPOSTA"
    status_http = 409


class EventoInvalidoError(DomainError):
    codigo = "EVENTO_INVALIDO"
    status_http = 422


class PendenciaNaoEncontradaError(DomainError):
    codigo = "PENDENCIA_NAO_ENCONTRADA"
    status_http = 404


class PendenciaJaResolvidaError(DomainError):
    """Resolver duas vezes seria sobrescrever quem resolveu primeiro (I-03)."""

    codigo = "PENDENCIA_JA_RESOLVIDA"
    status_http = 409


class ResolucaoInvalidaError(DomainError):
    """Resolução que não se aplica àquela regra, ou `fundir_com` que não é uma das duplicatas."""

    codigo = "RESOLUCAO_INVALIDA"
    status_http = 422


class ObservacaoObrigatoriaError(DomainError):
    """Tirar o paciente da fila exige motivo em texto (I-03: motivo, autor e data)."""

    codigo = "OBSERVACAO_OBRIGATORIA"
    status_http = 422


class CargaInvalidaError(DomainError):
    """Arquivo do dataset ausente, com colunas inesperadas ou valor que não converte (US-01)."""

    codigo = "CARGA_INVALIDA"
    status_http = 422


class FilaNaoPublicadaError(DomainError):
    """Ainda não existe fila publicada (I-07: só se publica o que passou no verificador)."""

    codigo = "FILA_NAO_PUBLICADA"
    status_http = 409

    def __init__(self, mensagem: str = "Nenhuma fila publicada ainda. Rode a publicação."):
        super().__init__(mensagem)


class DataReferenciaInvalidaError(DomainError):
    """US-16: a data simulada não pode voltar para antes da data oficial do dataset."""

    codigo = "DATA_REFERENCIA_INVALIDA"
    status_http = 422
