"""PRE-10..PRE-25 (US-04, US-05): detecção de inconsistências.

Cada regra devolve uma lista de Achado. Nada é apagado (I-03).
Oncológico nunca é suspenso sem confirmação humana (I-02): quem decide suspender é o caso de uso.
"""
from __future__ import annotations

import re

from app.domain.cid import is_oncologico
from app.domain.models import Achado, Evento, Motivo, Solicitacao
from app.domain.preprocessing.normalizacao import remover_acentos

PRE_CONTATO_PERDIDO = "PRE-10"
PRE_SEM_TELEFONE = "PRE-11"
PRE_CANCER_ESCONDIDO = "PRE-12"
PRE_DIABETES_FORA_DO_CADASTRO = "PRE-13"
PRE_JUSTIFICATIVA_VAZIA = "PRE-14"
PRE_CAMPO_VAZIO = "PRE-15"

PRE_DUPLICATA = "PRE-20"
PRE_OPEROU_FORA = "PRE-21"
PRE_OPEROU_CONVENIO = "PRE-22"
PRE_DESISTENCIA = "PRE-23"
PRE_EVENTO_ORFAO = "PRE-24"
PRE_FONTES_CONTRADITORIAS = "PRE-25"

# Bloqueantes (US-04): suspendem a solicitação, exceto oncológico (I-02). PRE-24 é de evento.
REGRAS_BLOQUEANTES = (PRE_DUPLICATA, PRE_OPEROU_FORA, PRE_OPEROU_CONVENIO, PRE_DESISTENCIA,
                      PRE_EVENTO_ORFAO, PRE_FONTES_CONTRADITORIAS)
REGRAS_DE_SOLICITACAO = tuple(r for r in REGRAS_BLOQUEANTES if r != PRE_EVENTO_ORFAO)
# Oncológico não é suspenso (I-02): fica ativo com este alerta até alguém confirmar.
ALERTA_SAIDA_A_CONFIRMAR = "saida_a_confirmar"

REGRAS_NAO_BLOQUEANTES = (PRE_CONTATO_PERDIDO, PRE_SEM_TELEFONE, PRE_CANCER_ESCONDIDO,
                          PRE_DIABETES_FORA_DO_CADASTRO, PRE_JUSTIFICATIVA_VAZIA, PRE_CAMPO_VAZIO)
# D-39: PRE-14 e PRE-15 só alertam; PRE-10..13 também abrem pendência (não bloqueante).
REGRAS_COM_PENDENCIA = REGRAS_NAO_BLOQUEANTES[:4]

# Alerta que cada regra põe em `Solicitacao.alertas` (aparece na fila, GET /fila).
ALERTA_POR_REGRA = {
    PRE_CONTATO_PERDIDO: "contato_perdido",
    PRE_SEM_TELEFONE: "contato_via_acs",
    PRE_CANCER_ESCONDIDO: "revisar_cid",
    PRE_DIABETES_FORA_DO_CADASTRO: "diabetes_fora_do_cadastro",
    PRE_JUSTIFICATIVA_VAZIA: "informacao_insuficiente",
    PRE_CAMPO_VAZIO: "cadastro_incompleto",
}
ALERTAS_NAO_BLOQUEANTES = frozenset(ALERTA_POR_REGRA.values())

MIN_TENTATIVAS_SEM_RESPOSTA = 2   # PRE-10 (D-37)
HBA1C_DIABETES = 6.5              # PRE-13 (D-38): critério diagnóstico de diabetes, em %
MAX_CARACTERES_GENERICA = 60      # PRE-14 (D-39)

_RE_NUMERO_INEXISTENTE = re.compile(r"numero nao existe")
_RE_SEM_TELEFONE = re.compile(r"\bacs\b|nao possui telefone|sem telefone")
_RE_DIABETES_NO_CADASTRO = re.compile(r"\bdm\d?\b|diabet")
_RE_DIABETES_NO_TEXTO = re.compile(r"nao consta no cadastro|sem registro no cadastro|investigar dm")
_RE_JUSTIFICATIVA_GENERICA = re.compile(
    r"^(solicito cirurgia|indicacao cirurgica|conforme laudo anexo|paciente com indicacao de [a-z ]+)\."
)
_CAMPOS_DE_COMPLETUDE = ("prioridade_regulacao", "intensidade_dor_eva", "asa", "distancia_hospital_km")

# PRE-21/22/23: o que cada fonte diz sobre a saída do paciente (D-43).
_SAIDA_NA_OBSERVACAO = (
    ("operou_fora", PRE_OPEROU_FORA, re.compile(r"outro servico|operou em outro|operou fora")),
    ("operou_convenio", PRE_OPEROU_CONVENIO, re.compile(r"operou pelo convenio|cirurgia pelo convenio")),
    ("desistencia", PRE_DESISTENCIA, re.compile(r"desistiu|nao deseja mais|solicita retirada da fila")),
)
_SAIDA_NO_EVENTO = {  # contato_telefonico / resultado
    "informou_cirurgia_outro_servico": ("operou_fora", PRE_OPEROU_FORA),
    "desistiu": ("desistencia", PRE_DESISTENCIA),
}
_TEXTO_DA_SAIDA = {
    PRE_OPEROU_FORA: ("Operou em outro serviço", "Ligar para confirmar a cirurgia em outro serviço"),
    PRE_OPEROU_CONVENIO: ("Operou pelo convênio", "Confirmar com a família se o paciente operou pelo convênio"),
    PRE_DESISTENCIA: ("Desistência", "Ligar para confirmar a desistência"),
    PRE_FONTES_CONTRADITORIAS: ("Fontes contraditórias", "Ligar para confirmar o motivo da saída"),
}


def detectar_bloqueantes(
    solicitacao: Solicitacao,
    eventos: list[Evento],
    outras_do_paciente: list[Solicitacao],
) -> list[Achado]:
    """PRE-20 duplicata, PRE-21/22/23 saída da fila e PRE-25 fontes contraditórias.

    `eventos` são os desta solicitação, já marcados por `marcar_eventos` (US-03);
    `outras_do_paciente`, as outras solicitações do mesmo paciente. PRE-24 é por evento
    (`detectar_eventos_orfaos`). Só detecta: suspender ou não (I-02) é do caso de uso.
    """
    achados = (_duplicata(solicitacao, outras_do_paciente), _saida_da_fila(solicitacao, eventos))
    return [a for a in achados if a is not None]


def detectar_eventos_orfaos(eventos: list[Evento], solicitacoes_existentes: set[str]) -> dict[str, Achado]:
    """PRE-24: evento cuja solicitação não existe. Não é aplicado. Um achado por ID referenciado."""
    por_id: dict[str, list[Evento]] = {}
    for e in eventos:
        if e.solicitacao_id not in solicitacoes_existentes:
            por_id.setdefault(e.solicitacao_id, []).append(e)
    return {
        sid: Achado(PRE_EVENTO_ORFAO, True, "Evento de solicitação fora da fila",
                    [Motivo("evento_orfao", e.descricao, "evento", e.evento_id, e.data_evento) for e in evs],
                    f"Verificar o ID {sid}: a solicitação não existe na fila")
        for sid, evs in por_id.items()
    }


def _duplicata(s: Solicitacao, outras: list[Solicitacao]) -> Achado | None:
    """PRE-20 (D-10, D-44): mesmo paciente e procedimento. Só a mais recente é o achado; a mais antiga fica
    com a data de entrada que já tem (a fusão dos eventos é da resolução, US-07)."""
    anteriores = [o for o in outras
                  if o.solicitacao_id != s.solicitacao_id and o.paciente_id == s.paciente_id
                  and o.procedimento_id == s.procedimento_id
                  and (o.data_entrada_fila, o.solicitacao_id) < (s.data_entrada_fila, s.solicitacao_id)]
    if not anteriores:
        return None
    mantida = min(anteriores, key=lambda o: (o.data_entrada_fila, o.solicitacao_id))
    evidencias = [
        Motivo("duplicata", f"{x.solicitacao_id}: entrada em {x.data_entrada_fila.isoformat()}, CID {x.cid_principal}",
               "solicitacao", x.solicitacao_id, x.data_entrada_fila)
        for x in (mantida, s)
    ]
    return Achado(PRE_DUPLICATA, True, "Solicitação duplicada", evidencias,
                  f"Fundir com {mantida.solicitacao_id}, mantendo a data de entrada mais antiga "
                  f"({mantida.data_entrada_fila.isoformat()})")


def _saida_da_fila(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-21/22/23 (D-43): a observação ou o call center diz que o paciente saiu. Se as fontes dizem
    coisas diferentes (ou uma só diz duas), é PRE-25, com as duas evidências lado a lado."""
    sinais: list[tuple[str, Motivo]] = []
    observacao = _chave(s.observacoes)
    for tipo, regra, padrao in _SAIDA_NA_OBSERVACAO:
        if padrao.search(observacao):
            sinais.append((regra, Motivo(tipo, s.observacoes, "observacoes")))
    for e in _validos(eventos):
        saida = _SAIDA_NO_EVENTO.get(e.resultado or "") if e.tipo_evento == "contato_telefonico" else None
        if saida:
            sinais.append((saida[1], Motivo(saida[0], e.descricao, "evento", e.evento_id, e.data_evento)))
    regras = {regra for regra, _ in sinais}
    if not regras:
        return None
    regra = next(iter(regras)) if len(regras) == 1 else PRE_FONTES_CONTRADITORIAS
    titulo, acao = _TEXTO_DA_SAIDA[regra]
    return Achado(regra, True, titulo, [m for _, m in sinais], acao)


def _chave(texto: str | None) -> str:
    """Minúsculo e sem acento, para casar texto livre."""
    return remover_acentos(texto or "").lower()


def _validos(eventos: list[Evento]) -> list[Evento]:
    """Eventos que contam: durante a espera e que não são cópia de outro (PRE-07/08)."""
    return [e for e in eventos if not e.historico and e.duplicado_de is None]


def detectar_nao_bloqueantes(solicitacao: Solicitacao, eventos: list[Evento]) -> list[Achado]:
    """PRE-10..PRE-15: o paciente segue na fila; o achado vira alerta (e pendência em PRE-10..13).

    `eventos` são os desta solicitação, já marcados por `marcar_eventos` (US-03).
    """
    regras = (_contato_perdido, _sem_telefone, _cancer_escondido, _diabetes_fora_do_cadastro,
              _justificativa_sem_conteudo, _campos_vazios)
    achados = (regra(solicitacao, eventos) for regra in regras)
    return [a for a in achados if a is not None]


def _contato_perdido(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-10 (D-37): 2 ou mais tentativas sem resposta, ou o número não existe. Não pune."""
    tentativas = [e for e in _validos(eventos)
                  if e.tipo_evento == "contato_telefonico" and e.resultado == "nao_atendeu"]
    numero_inexistente = bool(_RE_NUMERO_INEXISTENTE.search(_chave(s.observacoes)))
    if len(tentativas) < MIN_TENTATIVAS_SEM_RESPOSTA and not numero_inexistente:
        return None
    evidencias = [Motivo("sem_resposta", e.descricao or e.resultado or "", "evento", e.evento_id,
                         e.data_evento) for e in tentativas]
    if numero_inexistente:
        evidencias.append(Motivo("numero_inexistente", s.observacoes, "observacoes"))
    return Achado(PRE_CONTATO_PERDIDO, False, "Contato perdido", evidencias,
                  "Atualizar o contato (pode ser barreira de acesso; não altera a prioridade)")


def _sem_telefone(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-11 (D-37): sem telefone ou contato só via ACS, dito nas observações."""
    if not _RE_SEM_TELEFONE.search(_chave(s.observacoes)):
        return None
    return Achado(PRE_SEM_TELEFONE, False, "Contato via ACS",
                  [Motivo("sem_telefone", s.observacoes, "observacoes")],
                  "Acionar o ACS para contatar o paciente")


def _cancer_escondido(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-12 (D-37): biópsia positiva e CID não oncológico. A classe segue o fluxo de eventos."""
    if is_oncologico(s.cid_principal):
        return None
    biopsias = [e for e in eventos
                if e.duplicado_de is None and e.tipo_evento == "biopsia" and e.resultado == "positivo"]
    if not biopsias:
        return None
    evidencias = [Motivo("biopsia_positiva", e.descricao, "evento", e.evento_id, e.data_evento)
                  for e in biopsias]
    evidencias.append(Motivo("cid", f"{s.cid_principal} {s.cid_descricao or ''}".strip(), "cid"))
    return Achado(PRE_CANCER_ESCONDIDO, False, "Biópsia positiva com CID não oncológico", evidencias,
                  "Corrigir o CID com o médico solicitante")


def _diabetes_fora_do_cadastro(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-13 (D-38): sinal de diabetes (texto explícito ou HbA1c >= 6,5%) sem o cadastro. Sem efeito na prioridade."""
    if s.flag_diabetico == "sim" or _RE_DIABETES_NO_CADASTRO.search(_chave(s.comorbidades)):
        return None
    evidencias: list[Motivo] = []
    if _RE_DIABETES_NO_TEXTO.search(_chave(s.observacoes)):
        evidencias.append(Motivo("diabetes_no_texto", s.observacoes, "observacoes"))
    evidencias += [Motivo("hba1c_alta", f"HbA1c {e.valor_numerico:g}%", "evento", e.evento_id, e.data_evento)
                   for e in eventos if e.duplicado_de is None and e.tipo_evento == "hba1c"
                   and e.valor_numerico is not None and e.valor_numerico >= HBA1C_DIABETES]
    if not evidencias and s.hba1c_ultima is not None and s.hba1c_ultima >= HBA1C_DIABETES:
        evidencias.append(Motivo("hba1c_alta", f"HbA1c {s.hba1c_ultima:g}% no cadastro", "cadastro"))
    if not evidencias:
        return None
    return Achado(PRE_DIABETES_FORA_DO_CADASTRO, False, "Diabetes fora do cadastro", evidencias,
                  "Atualizar o cadastro (não altera a prioridade)")


def _justificativa_sem_conteudo(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-14 (D-39): frase genérica e curta, sem dado clínico para classificar."""
    texto = (s.justificativa_clinica or "").strip()
    vazia = not texto
    generica = bool(_RE_JUSTIFICATIVA_GENERICA.match(_chave(texto))) and len(texto) < MAX_CARACTERES_GENERICA
    if not (vazia or generica):
        return None
    return Achado(PRE_JUSTIFICATIVA_VAZIA, False, "Informação insuficiente para classificar",
                  [Motivo("justificativa_generica", texto or "(vazia)", "justificativa_clinica")],
                  "Pedir ao médico solicitante a indicação clínica")


def _campos_vazios(s: Solicitacao, eventos: list[Evento]) -> Achado | None:
    """PRE-15 (D-39): campo que o SWALIS usa e veio vazio. O SWALIS segue com o que existe."""
    vazios = [c for c in _CAMPOS_DE_COMPLETUDE
              if getattr(s, c) is None or (isinstance(getattr(s, c), str) and not getattr(s, c).strip())]
    if not vazios:
        return None
    return Achado(PRE_CAMPO_VAZIO, False, "Cadastro incompleto",
                  [Motivo("campo_vazio", f"{c} sem valor", "cadastro") for c in vazios],
                  "Completar o cadastro")
