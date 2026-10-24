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


class EventoInvalidoError(DomainError):
    codigo = "EVENTO_INVALIDO"
    status_http = 422


class CargaInvalidaError(DomainError):
    """Arquivo do dataset ausente, com colunas inesperadas ou valor que não converte (US-01)."""

    codigo = "CARGA_INVALIDA"
    status_http = 422
