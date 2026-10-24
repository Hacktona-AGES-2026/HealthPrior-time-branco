"""US-18 · Seed do ciclo de aprendizado (D-98).

Grava ~33 decisões sintéticas (DEC-SEED-001..) no log real, sobre pacientes reais ativos e não
oncológicos, para a demo ter propostas de regra a revisar. Cinco padrões cobrem os caminhos do
agrupamento: passa, passa com `outro`, descartado por I-01, falha por volume e falha por janela.
Idempotente: se já existe alguma DEC-SEED, não grava de novo. Não altera solicitações.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from app.domain.cid import is_oncologico
from app.domain.enums import AcaoDecisao, Classe, MotivoCodificado
from app.domain.models import Decisao
from app.domain.ports import DecisaoRepository, SolicitacaoRepository, UnidadeDeTrabalho

PREFIXO = "DEC-SEED-"
VERSAO = "seed-aprendizado"


@dataclass(frozen=True)
class _Padrao:
    procedimento_id: str
    motivo: MotivoCodificado
    de: Classe
    para: Classe
    reguladores: tuple[str, ...]
    n_editar: int
    justificativas: tuple[str, ...]
    n_manter: int = 0
    regulador_manter: str = "reg-02"
    n_outro: int = 0
    justificativas_outro: tuple[str, ...] = ()
    dias: tuple[int, int] = (3, 58)  # intervalo (mais recente, mais antigo) antes da referência


PADROES = (
    _Padrao("PROC004", MotivoCodificado.PS_RECORRENTE, Classe.C, Classe.B,
            ("reg-01", "reg-02", "reg-03", "reg-04"), 8,
            ("Duas idas ao PS nos últimos meses por cólica biliar.",
             "Paciente voltou ao pronto-socorro com crise de vesícula, sobe para B.",
             "Três atendimentos de urgência por dor biliar no trimestre.",
             "PS recorrente por colecistite leve; não deve esperar como C."),
            n_manter=1),
    _Padrao("PROC002", MotivoCodificado.PIORA_FUNCIONAL, Classe.D, Classe.C,
            ("reg-01", "reg-02", "reg-03"), 7,
            ("Piora funcional: já não consegue trabalhar por causa da hérnia.",
             "Relata limitação crescente para carregar peso e caminhar.",
             "Perdeu autonomia nas atividades diárias, aumento de dor ao esforço.",
             "Hérnia aumentou e limita o trabalho, sobe de D para C."),
            n_outro=2,
            justificativas_outro=("Paciente está bem pior, quase não consegue mais fazer as tarefas de casa.",
                                  "Quadro vem piorando e ele já depende da família para o dia a dia.")),
    _Padrao("PROC018", MotivoCodificado.SUGESTAO_EXAGERADA, Classe.B, Classe.C,
            ("reg-01", "reg-02", "reg-03"), 6,
            ("Sugestão exagerada: quadro estável, sem sangramento importante.",
             "Classe B acima do necessário para o caso, sintomas controlados.",
             "Paciente assintomática no momento, rebaixo para C.")),
    _Padrao("PROC006", MotivoCodificado.DOR_INTENSA, Classe.C, Classe.B,
            ("reg-01", "reg-02"), 4,
            ("Dor intensa em repouso, relatada na última consulta.",
             "Dor forte que impede de ficar em pé por muito tempo.")),
    _Padrao("PROC001", MotivoCodificado.DADO_DESATUALIZADO, Classe.D, Classe.C,
            ("reg-01", "reg-02", "reg-03"), 5,
            ("Acuidade visual no cadastro está desatualizada; exame novo mostra queda.",
             "Dado de visão antigo, paciente piorou desde a última avaliação."),
            dias=(120, 150)),
)


class SemearAprendizado:
    def __init__(self, decisoes: DecisaoRepository, solicitacoes: SolicitacaoRepository,
                 uow: UnidadeDeTrabalho, referencia: date):
        self._decisoes = decisoes
        self._solicitacoes = solicitacoes
        self._uow = uow
        self._referencia = referencia

    def executar(self) -> int:
        """Quantidade de decisões gravadas (0 se já estava semeado)."""
        if any(d.decisao_id.startswith(PREFIXO) for d in self._decisoes.listar_todas()):
            return 0
        ativas = sorted(self._solicitacoes.listar(apenas_ativas=True), key=lambda s: s.solicitacao_id)
        base = datetime(self._referencia.year, self._referencia.month, self._referencia.day,
                        tzinfo=timezone.utc)
        gravadas = 0
        for padrao in PADROES:
            for decisao in self._montar(padrao, ativas, base, gravadas):
                self._decisoes.adicionar(decisao)
                gravadas += 1
        self._uow.confirmar()
        return gravadas

    def _montar(self, p: _Padrao, ativas, base: datetime, inicio: int) -> list[Decisao]:
        vistos: set[str] = set()
        elegiveis = []
        for s in ativas:
            if (s.procedimento_id == p.procedimento_id and s.paciente_id not in vistos
                    and not s.oncologico and not is_oncologico(s.cid_norm or s.cid_principal)):
                vistos.add(s.paciente_id)
                elegiveis.append(s)
        total = p.n_editar + p.n_manter + p.n_outro
        escolhidas = elegiveis[:total]
        recente, antigo = p.dias
        decisoes = []
        for i, s in enumerate(escolhidas):
            if i < p.n_editar:
                acao, motivo, para = AcaoDecisao.EDITAR, p.motivo, p.para
                reg, texto = p.reguladores[i % len(p.reguladores)], p.justificativas[i % len(p.justificativas)]
            elif i < p.n_editar + p.n_manter:
                acao, motivo, para = AcaoDecisao.MANTER, p.motivo, p.de
                reg, texto = p.regulador_manter, "Mantida a classe: o quadro não justifica subir."
            else:
                k = i - p.n_editar - p.n_manter
                acao, motivo, para = AcaoDecisao.EDITAR, MotivoCodificado.OUTRO, p.para
                reg = p.reguladores[k % len(p.reguladores)]
                texto = p.justificativas_outro[k % len(p.justificativas_outro)]
            dias = recente + (i * (antigo - recente)) // max(total - 1, 1)
            data = base - timedelta(days=dias, hours=i % 5)
            decisoes.append(Decisao(
                decisao_id=f"{PREFIXO}{inicio + i + 1:03d}", solicitacao_id=s.solicitacao_id,
                regulador_id=reg, acao=acao, data=data, classe_sugerida=p.de, classe_decidida=para,
                motivo_codificado=motivo, justificativa=texto, versao_regras=VERSAO,
                procedimento_id=p.procedimento_id))
        return decisoes
