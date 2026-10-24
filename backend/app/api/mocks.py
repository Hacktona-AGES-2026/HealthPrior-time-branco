"""Respostas fixas com o contrato final, para o front trabalhar em paralelo (docs/user-stories.md §6).

Usa pacientes reais do dataset. Valores de score são ilustrativos.
Desligue com HP_USE_MOCKS=false quando os casos de uso existirem.
"""
from datetime import date, datetime

from app.api import schemas as s

AGORA = datetime(2026, 10, 24, 10, 0, 0)

FILA = s.FilaOut(
    versao_regras="stub-0",
    gerada_em=AGORA,
    publicada=True,
    total=3,
    itens=[
        s.ItemFilaOut(
            posicao=1, solicitacao_id="SOL-2023-00010", camada=1, classe="A2",
            classe_status="sugerida_nao_confirmada", pct_prazo_consumido=6276.2, dias_em_fila=1318,
            procedimento="Colectomia", especialidade="Cirurgia Oncologica", cid="C18.7",
            oncologico=True, editado_manualmente=False, alertas=["contato_perdido"],
            resumo_justificativa="Camada 1 (oncológico C18.7). Biópsia positiva em 30/01/2023.",
        ),
        s.ItemFilaOut(
            posicao=2, solicitacao_id="SOL-2025-00149", camada=1, classe="A2",
            classe_status="sugerida_nao_confirmada", pct_prazo_consumido=2428.6, dias_em_fila=510,
            procedimento="Prostatectomia radical", especialidade="Urologia", cid="C61",
            oncologico=True, editado_manualmente=False, alertas=[],
            resumo_justificativa="Camada 1 (oncológico C61). Flag oncológica corrigida pelo CID.",
        ),
        s.ItemFilaOut(
            posicao=3, solicitacao_id="SOL-2023-00060", camada=2, classe="B",
            classe_status="confirmada", pct_prazo_consumido=1848.3, dias_em_fila=1109,
            procedimento="Colecistectomia videolaparoscopica", especialidade="Cirurgia Geral",
            cid="K80.2", oncologico=False, editado_manualmente=True, alertas=[],
            resumo_justificativa="Camada 2 (2 idas ao PS em 3 meses). Classe B editada por reg-01.",
        ),
    ],
)

DETALHE = s.SolicitacaoDetalheOut(
    solicitacao_id="SOL-2023-00010", paciente_id="PAC-00467", nome_paciente="(sintético)",
    idade=62, sexo="M", municipio="Pelotas", procedimento="Colectomia", cid="C18.7",
    cid_descricao="Neoplasia maligna do colon sigmoide", status_fila="ativa", posicao=1, camada=1,
    camada_motivo="Oncológico pelo CID (C18.7)",
    score=s.ScoreOut(
        classe_sistema="A2", score_sistema=6276.2, score_efetivo=6276.2, prazo_dias=21,
        pct_prazo_consumido=6276.2, classe_status="sugerida_nao_confirmada", versao_regras="stub-0",
        motivos=[s.MotivoOut(sinal="biopsia_positiva", evidencia="Biópsia positiva", fonte="evento",
                             ref="EVT-000013", data=date(2023, 1, 30))],
    ),
    explicacao="Posição 1: oncológico (camada 1) com 1.318 dias de espera, muito acima do prazo da classe A2.",
    eventos=[
        s.EventoOut(evento_id="EVT-000013", data_evento=date(2023, 1, 30), tipo_evento="biopsia",
                    resultado="positivo", historico=True),
        s.EventoOut(evento_id="EVT-000087", data_evento=date(2024, 9, 17), tipo_evento="exame_imagem",
                    resultado="estavel"),
        s.EventoOut(evento_id="EVT-000291", data_evento=date(2025, 11, 27),
                    tipo_evento="contato_telefonico", resultado="nao_atendeu"),
    ],
    alertas=["contato_perdido"],
    correcoes=[s.CorrecaoOut(campo="flag_oncologico", original="nao", novo="sim", regra="PRE-05")],
)

INBOX = s.InboxOut(
    total=1,
    itens=[
        s.ItemInboxOut(
            solicitacao_id="SOL-2023-00060", procedimento="Colecistectomia videolaparoscopica",
            camada=2, dias_em_fila=1109, classe_atual="C", classe_sugerida="B",
            motivos=[s.MotivoOut(sinal="ps_recorrente", evidencia="2 idas ao PS em 3 meses",
                                 fonte="justificativa_clinica")],
            criado_em=AGORA,
        )
    ],
)

PENDENCIAS = s.PendenciasOut(
    total=1,
    itens=[
        s.PendenciaOut(
            pendencia_id="PEN-0001", solicitacao_id="SOL-2026-00305", regra="PRE-25",
            titulo="Fontes contraditórias", bloqueante=True,
            evidencias=[
                s.EvidenciaOut(fonte="evento", ref="EVT-000566",
                               texto="Pct informa que nao deseja mais realizar a cirurgia."),
                s.EvidenciaOut(fonte="observacoes",
                               texto="Familiar informa que paciente operou pelo convenio."),
            ],
            acao_sugerida="Ligar para confirmar o motivo da saída", status="aberta",
            aberta_em=date(2026, 10, 24),
        )
    ],
)


GERAR_PROPOSTAS = s.GerarPropostasOut(
    analisadas=33, consideradas=33, outros_reclassificados=2, outros_sem_grupo=0,
    propostas=[
        s.PropostaRegraOut(
            proposta_id="PROP-PROC004-ps_recorrente-C-B", procedimento_id="PROC004",
            procedimento="Colecistectomia videolaparoscopica", motivo="ps_recorrente",
            classe_de="C", classe_para="B", direcao="subir", n_casos=8, n_reguladores=4,
            consistencia=0.89, casos=[f"DEC-SEED-{i:03d}" for i in range(1, 9)], status="pendente"),
    ],
    descartadas=[
        s.PropostaRegraOut(
            proposta_id="PROP-PROC018-sugestao_exagerada-B-C", procedimento_id="PROC018",
            procedimento="Histerectomia", motivo="sugestao_exagerada", classe_de="B", classe_para="C",
            direcao="rebaixar", n_casos=6, n_reguladores=3, consistencia=1.0,
            casos=[f"DEC-SEED-{i:03d}" for i in range(19, 25)], status="descartada",
            motivo_descarte="Rebaixa classe de procedimento com paciente oncológico ativo (I-01)."),
    ],
)


_PROPOSTA_MOCK = dict(
    proposta_id="PROP-PROC004-ps_recorrente-C-B", procedimento_id="PROC004",
    procedimento="Colecistectomia videolaparoscopica", motivo="ps_recorrente", classe_de="C",
    classe_para="B", direcao="subir", n_casos=8, n_reguladores=4, consistencia=0.89,
    casos=[f"DEC-SEED-{i:03d}" for i in range(1, 9)], status="pendente")

PROPOSTAS = s.PropostasOut(total=1, itens=[s.PropostaDetalheOut(
    **_PROPOSTA_MOCK,
    casos_origem=[s.CasoOrigemOut(
        decisao_id="DEC-SEED-001", solicitacao_id="SOL-2023-00060", regulador_id="reg-01",
        data=datetime(2026, 9, 1, 12, 0), acao="editar", classe_de="C", classe_para="B",
        motivo="ps_recorrente", justificativa="Dois PS por colecistite em 60 dias.")],
    impacto=s.ImpactoOut(afetados=12, oncologicos_afetados=0, oncologicos_rebaixados=0,
                         exemplos=["SOL-2023-00060"]))])

DECIDIR_PROPOSTA = s.DecidirPropostaOut(
    proposta_id="PROP-PROC004-ps_recorrente-C-B", status="aprovada", versao=1,
    versao_regras="swalis-regras-2+aprendizado-v1", enviados_ao_inbox=12)


REVERTER_REGRA = s.ReverterRegraOut(
    regra_id="PROP-PROC004-ps_recorrente-C-B", status="revertida",
    versao_regras="swalis-regras-2", devolvidos_ao_inbox=12)
