"""Comandos de linha (rode dentro de backend/):

    python -m app.cli init-db     cria as tabelas
    python -m app.cli carga       US-01/02/03/05: carga + normalização + flags + alertas (mesma transação)
    python -m app.cli normalizar  US-02: recalcula as colunas *_norm e o correcoes_log
    python -m app.cli bloqueantes  US-04: recalcula achados bloqueantes e suspensões (sem recarregar)
    python -m app.cli inconsistencias  US-05: recalcula alertas e pendências não bloqueantes (sem recarregar)
    python -m app.cli flags       US-03: recalcula oncologico/piora e marca eventos (sem recarregar)
    python -m app.cli gerar-fila  US-09/10: gera a fila do banco, verifica e publica (I-07)
    python -m app.cli gerar-fila-csv  US-08 provisório (D-26): gera a fila direto do dataset, sem banco
    python -m app.cli extrair-sinais  SW-01..04: pré-aquece o cache do LLM e mostra as classes SWALIS
    python -m app.cli seed-aprendizado  US-18: grava ~33 decisões de exemplo (DEC-SEED-*); idempotente
    python -m app.cli gerar-propostas  US-18: agrupa as decisões em propostas de regra e as grava
    python -m app.cli recontato   US-17: abre pendências de recontato (sem evento há N dias, HP_RECONTATO_DIAS)
    python -m app.cli sugerir-cid  PRE-12 (D-125): LLM sugere o CID nas pendências de câncer escondido abertas
    python -m app.cli bootstrap   deploy: se o banco está vazio, carga + primeira fila (+ propostas da demo com HP_DEMO_SEED=true)
    python -m app.cli decisoes    US-11: lista exclusões para o DECISOES.md
"""
import argparse
import os
import sys
from collections import Counter
from datetime import datetime, timezone

from sqlmodel import Session

from app.application.carga_inicial import CargaInicial
from app.application.gerar_fila import GerarFila
from app.application.montar_fila import linhas_para_dicts, montar_fila
from app.application.detectar_bloqueantes import DetectarBloqueantes, ResumoBloqueantes
from app.application.detectar_inconsistencias import DetectarInconsistencias, ResumoInconsistencias
from app.application.gerar_propostas import GerarPropostas
from app.application.publicar_fila import PublicarFila
from app.application.semear_aprendizado import SemearAprendizado
from app.application.normalizar import Normalizar, ResumoNormalizacao
from app.application.recalcular_flags import RecalcularFlags, ResumoFlags
from app.config import settings
from app.domain.errors import CargaInvalidaError
from app.infrastructure.csv_loader import LeitorDataset
from app.infrastructure.csv_source import carregar_do_csv
from app.infrastructure.db import criar_tabelas, engine
from app.infrastructure.exportador import ExportadorCsv
from app.infrastructure.repositories import (
    SqlCargaRepository,
    SqlCorrecaoRepository,
    SqlDecisaoRepository,
    SqlEventoRepository,
    SqlFilaRepository,
    SqlPendenciaRepository,
    SqlPropostaRepository,
    SqlSolicitacaoRepository,
    SqlUnidadeDeTrabalho,
)
from app.infrastructure.swalis_aprendido import com_regras
from app.infrastructure.swalis_regras import criar_swalis
from app.infrastructure.verificador import VerificadorOficial


def cmd_init_db() -> None:
    criar_tabelas()
    print(f"Tabelas criadas em {settings.db_url}")


def _imprimir_normalizacao(r: ResumoNormalizacao) -> None:
    regras = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.por_regra.items())) or "nenhuma"
    print(f"normalização: {r.solicitacoes} solicitações, {r.correcoes} correções ({regras})")


def _imprimir_flags(r: ResumoFlags) -> None:
    regras = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.correcoes.items())) or "nenhuma"
    print(f"flags: {r.solicitacoes} solicitações, correções ({regras})")
    print(f"eventos: {r.eventos_duplicados} duplicados, {r.eventos_historicos} históricos")


def _recalcular_flags(session: Session) -> RecalcularFlags:
    return RecalcularFlags(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                           SqlCorrecaoRepository(session))


def _imprimir_inconsistencias(r: ResumoInconsistencias) -> None:
    alertas = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.alertas.items())) or "nenhum"
    p = r.pendencias
    print(f"inconsistências: {r.solicitacoes} solicitações, alertas ({alertas})")
    print(f"pendências: {p.abertas} abertas, {p.atualizadas} atualizadas, {p.encerradas} encerradas")


def _imprimir_bloqueantes(r: ResumoBloqueantes) -> None:
    achados = ", ".join(f"{regra}: {n}" for regra, n in sorted(r.achados.items())) or "nenhum"
    p = r.pendencias
    print(f"bloqueantes: {r.solicitacoes} solicitações, achados ({achados})")
    print(f"suspensas: {r.suspensas} ({r.reativadas} reativadas); oncológicas a confirmar: "
          f"{r.oncologicas_a_confirmar}; eventos órfãos: {r.eventos_orfaos}")
    print(f"pendências bloqueantes: {p.abertas} abertas, {p.atualizadas} atualizadas, {p.encerradas} encerradas")


def _detectar_bloqueantes(session: Session) -> DetectarBloqueantes:
    return DetectarBloqueantes(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                               SqlPendenciaRepository(session), settings.ref_date)


def _detectar_inconsistencias(session: Session) -> DetectarInconsistencias:
    return DetectarInconsistencias(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                                   SqlPendenciaRepository(session), settings.ref_date)


def cmd_carga() -> None:
    criar_tabelas()
    with Session(engine) as session:
        normalizar = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session))
        try:
            resumo = CargaInicial(LeitorDataset(), SqlCargaRepository(session), normalizar,
                                  SqlUnidadeDeTrabalho(session),
                                  _recalcular_flags(session),
                                  _detectar_inconsistencias(session),
                                  _detectar_bloqueantes(session)).executar()
        except CargaInvalidaError as e:
            sys.exit(f"Erro na carga: {e.mensagem}")
    for tabela in ("procedimentos", "solicitacoes", "eventos"):
        r = getattr(resumo, tabela)
        print(f"{tabela}: {r.lido} lidos, {r.inseridos} inseridos, {r.atualizados} atualizados")
    _imprimir_normalizacao(resumo.normalizacao)
    _imprimir_flags(resumo.flags)
    _imprimir_inconsistencias(resumo.inconsistencias)
    _imprimir_bloqueantes(resumo.bloqueantes)


def cmd_normalizar() -> None:
    with Session(engine) as session:
        resumo = Normalizar(SqlSolicitacaoRepository(session), SqlCorrecaoRepository(session)).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    _imprimir_normalizacao(resumo)


def cmd_flags() -> None:
    with Session(engine) as session:
        resumo = _recalcular_flags(session).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    _imprimir_flags(resumo)


def cmd_bloqueantes() -> None:
    with Session(engine) as session:
        resumo = _detectar_bloqueantes(session).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    _imprimir_bloqueantes(resumo)


def cmd_sugerir_cid() -> None:
    """PRE-12 (D-125): sugere o CID de cada pendência "câncer escondido" aberta e aquece o cache."""
    from app.api.deps import montar_sugerir_cid

    with Session(engine) as session:
        r = montar_sugerir_cid(session).executar_abertas()
    print(f"PRE-12: {r.pendencias} pendências abertas, {r.sugeridas} com sugestão de CID, "
          f"{r.sem_sugestao} sem sugestão ({settings.cid_llm_model}, esforço {settings.cid_llm_esforco})")
    print(f"Cache: {settings.cid_llm_cache_path}")


def cmd_inconsistencias() -> None:
    with Session(engine) as session:
        resumo = _detectar_inconsistencias(session).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    _imprimir_inconsistencias(resumo)


def cmd_gerar_fila() -> None:
    """US-09/10: gera a fila do banco, roda o verificador e só publica se passar (I-07)."""
    with Session(engine) as session:
        gerar = GerarFila(
            SqlSolicitacaoRepository(session), SqlEventoRepository(session),
            com_regras(criar_swalis(), session),
            ExportadorCsv(), settings.ref_date,
        )
        resultado = PublicarFila(
            gerar, VerificadorOficial(session=session), SqlFilaRepository(session), SqlUnidadeDeTrabalho(session),
            lambda: datetime.now(timezone.utc), settings.output_dir,
        ).executar()
    print(resultado.saida_verificador, end="")
    print(f"Arquivo: {resultado.caminho_csv}")
    print(f"Total: {resultado.total} | " + " | ".join(
        f"camada {c}: {resultado.por_camada.get(c, 0)}" for c in (1, 2, 3)))
    if not resultado.publicada:
        print("FILA NÃO PUBLICADA: o verificador falhou (I-07). A fila anterior continua valendo.",
              file=sys.stderr)
        sys.exit(1)


def cmd_gerar_fila_csv() -> None:
    """Gera output/fila_priorizada.csv direto do dataset (sem banco) e roda o verificador (I-07).

    Provisório (D-26): substituído por `gerar-fila` quando a US-01 (carga no banco) existir.
    """
    solicitacoes, eventos = carregar_do_csv(settings.data_dir)
    linhas = montar_fila(solicitacoes, eventos, criar_swalis(), settings.ref_date)
    csv_path = ExportadorCsv().exportar(linhas_para_dicts(linhas),
                                        settings.output_dir / "fila_priorizada.csv")
    passou, saida = VerificadorOficial().verificar(csv_path)
    print(saida, end="")
    por_camada = Counter(linha.camada for linha in linhas)
    print(f"Arquivo: {csv_path}")
    print(f"Total: {len(linhas)} | " + " | ".join(
        f"camada {c}: {por_camada.get(c, 0)}" for c in (1, 2, 3)))
    if not passou:
        print("FILA NÃO PUBLICADA: o verificador falhou (I-07).", file=sys.stderr)
        sys.exit(1)


def cmd_extrair_sinais() -> None:
    """Chama o LLM para os textos que faltam no cache (congela o cache) e resume classes e alertas."""
    from concurrent.futures import ThreadPoolExecutor

    solicitacoes, eventos = carregar_do_csv(settings.data_dir)
    swalis = criar_swalis(apenas_cache=False)
    extrator = swalis.extrator
    if extrator is None:
        sys.exit("LLM desligado: defina OPENROUTER_API_KEY no .env da raiz (ou HP_LLM_ENABLED=true).")
    textos = {t for s in solicitacoes for t in (s.justificativa_clinica, s.observacoes) if t.strip()}
    faltando = [t for t in textos if not extrator.em_cache(t)]
    print(f"{len(textos)} textos distintos, {len(faltando)} fora do cache ({extrator.modelo})")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for i, _ in enumerate(pool.map(lambda t: extrator.extrair(t, ""), faltando), 1):
                if i % 50 == 0:
                    print(f"  {i}/{len(faltando)}")
                    extrator.salvar_cache()
    finally:
        extrator.salvar_cache()
    classes = Counter()
    por_llm = 0
    for sol in solicitacoes:
        c = swalis.classificar(sol, eventos.get(sol.solicitacao_id, []))
        classes[c.classe.value] += 1
        por_llm += bool(swalis.pontos_llm(sol))
    print("Classes: " + " | ".join(f"{k}: {classes[k]}" for k in ("A1", "A2", "B", "C", "D")))
    print(f"Solicitações com ponto apontado pelo Jev: {por_llm}")
    print(f"Cache: {settings.llm_cache_path}")


def cmd_recontato() -> None:
    """US-17 (C-04): pendência de recontato para quem está sem evento há N dias; não altera a fila."""
    from app.application.detectar_recontato import DetectarRecontato

    criar_tabelas()
    with Session(engine) as session:
        data = _data_referencia(session)
        r = DetectarRecontato(SqlSolicitacaoRepository(session), SqlEventoRepository(session),
                              SqlPendenciaRepository(session), data, settings.recontato_dias).executar()
        SqlUnidadeDeTrabalho(session).confirmar()
    p = r.pendencias
    print(f"recontato em {data:%d/%m/%Y}: {r.sem_evento} de {r.avaliadas} ativas sem evento há "
          f"{r.n_dias}+ dias; pendências: {p.abertas} abertas, {p.atualizadas} atualizadas, "
          f"{p.encerradas} encerradas")


def _data_referencia(session: Session):
    return SqlFilaRepository(session).data_referencia() or settings.ref_date


def cmd_seed_aprendizado() -> None:
    """US-18 (D-98): grava as decisões de exemplo no log real. Não altera solicitações."""
    criar_tabelas()
    with Session(engine) as session:
        gravadas = SemearAprendizado(
            SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
            SqlUnidadeDeTrabalho(session), _data_referencia(session)).executar()
    print(f"seed-aprendizado: {gravadas} decisões gravadas" if gravadas
          else "seed-aprendizado: já semeado (DEC-SEED-*), nada a gravar")


def _linha_proposta(p) -> str:
    extra = f" | {p.motivo_descarte}" if p.motivo_descarte else ""
    return (f"  {p.proposta_id} | {p.direcao} {p.classe_de.value}->{p.classe_para.value} | "
            f"{p.n_casos} casos, {p.n_reguladores} reguladores, consistência {p.consistencia:.2f} | "
            f"{p.status}{extra}")


def cmd_gerar_propostas() -> None:
    """US-18: agrupa as decisões em propostas de regra (C-14) e substitui as pendentes/descartadas."""
    from app.api.deps import criar_classificador_motivo

    criar_tabelas()
    with Session(engine) as session:
        data = _data_referencia(session)
        classificador = criar_classificador_motivo()
        try:
            r = GerarPropostas(
                SqlDecisaoRepository(session), SqlSolicitacaoRepository(session),
                SqlPropostaRepository(session), SqlUnidadeDeTrabalho(session),
                datetime(data.year, data.month, data.day, tzinfo=timezone.utc),
                classificador).executar()
        finally:
            if classificador is not None:
                classificador.salvar_cache()
    print(f"decisões: {r.analisadas} analisadas, {r.consideradas} consideradas; `outro`: "
          f"{r.outros_reclassificados} reclassificados, {r.outros_sem_grupo} sem grupo")
    print(f"propostas: {len(r.propostas)} pendentes, {len(r.descartadas)} descartadas")
    for p in (*r.propostas, *r.descartadas):
        print(_linha_proposta(p))


def cmd_bootstrap() -> None:
    """Primeira subida (deploy): banco sem solicitações -> carga, fila publicada e, na demo, as propostas de regra.

    Idempotente: com dados no banco não faz nada, então reiniciar o serviço não refaz a carga nem mexe em decisões.
    """
    from sqlalchemy import func, select

    from app.infrastructure.tables import SolicitacaoTable

    criar_tabelas()
    with Session(engine) as session:
        existentes = session.execute(select(func.count()).select_from(SolicitacaoTable)).scalar() or 0
    if existentes:
        print(f"bootstrap: o banco já tem {existentes} solicitações; nada a fazer")
        return
    print("bootstrap: banco vazio; carregando o dataset")
    cmd_carga()
    cmd_gerar_fila()
    if os.getenv("HP_DEMO_SEED", "true").lower() == "true":
        cmd_seed_aprendizado()
        cmd_gerar_propostas()
    print("bootstrap: pronto")


def cmd_decisoes() -> None:
    raise NotImplementedError("US-11: gerar tabela de exclusões")


COMANDOS = {"init-db": cmd_init_db, "carga": cmd_carga, "normalizar": cmd_normalizar,
            "flags": cmd_flags, "inconsistencias": cmd_inconsistencias, "bloqueantes": cmd_bloqueantes,
            "gerar-fila": cmd_gerar_fila, "gerar-fila-csv": cmd_gerar_fila_csv,
            "extrair-sinais": cmd_extrair_sinais,
            "recontato": cmd_recontato, "sugerir-cid": cmd_sugerir_cid, "seed-aprendizado": cmd_seed_aprendizado, "gerar-propostas": cmd_gerar_propostas,
            "bootstrap": cmd_bootstrap, "decisoes": cmd_decisoes}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("comando", choices=COMANDOS)
    COMANDOS[parser.parse_args().comando]()


if __name__ == "__main__":
    main()
